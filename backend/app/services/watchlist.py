from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Report, WatchAlert, WatchItem
from app.schemas.watchlist import (
    WatchAlertResponse,
    WatchEvaluationResponse,
    WatchItemCreate,
    WatchItemListResponse,
    WatchItemResponse,
    WatchItemUpdate,
)


CATEGORY_REPORT_TYPES = {
    "market": {"market_strategy", "daily_briefing"},
    "company": {"company_research", "daily_briefing"},
    "housing": {"housing", "daily_briefing"},
    "macro": {"macro", "market_strategy", "daily_briefing"},
    "world": {"daily_briefing"},
}

STOP_WORDS = {
    "about",
    "after",
    "alert",
    "below",
    "between",
    "could",
    "from",
    "give",
    "have",
    "into",
    "market",
    "news",
    "rates",
    "should",
    "that",
    "their",
    "there",
    "this",
    "today",
    "watch",
    "what",
    "when",
    "where",
    "with",
}


def list_watch_items(session: Session) -> WatchItemListResponse:
    items = (
        session.scalars(
            select(WatchItem)
            .options(joinedload(WatchItem.alerts))
            .order_by(desc(WatchItem.enabled), desc(WatchItem.updated_at), desc(WatchItem.id))
        )
        .unique()
        .all()
    )
    return WatchItemListResponse(items=[watch_item_to_response(item) for item in items], total=len(items))


def create_watch_item(session: Session, request: WatchItemCreate) -> WatchItemResponse:
    item = WatchItem(
        title=request.title.strip(),
        category=request.category,
        query=request.query.strip(),
        priority=request.priority,
        enabled=request.enabled,
        status="watching" if request.enabled else "paused",
        trigger_metadata={"matching": "recent saved reports"},
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return get_watch_item(session, item.id)


def update_watch_item(session: Session, watch_item_id: int, request: WatchItemUpdate) -> WatchItemResponse:
    item = session.get(WatchItem, watch_item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch item not found")

    if request.title is not None:
        item.title = request.title.strip()
    if request.category is not None:
        item.category = request.category
    if request.query is not None:
        item.query = request.query.strip()
    if request.priority is not None:
        item.priority = request.priority
    if request.enabled is not None:
        item.enabled = request.enabled
        if not request.enabled:
            item.status = "paused"
        elif item.status == "paused":
            item.status = "watching"

    session.commit()
    session.refresh(item)
    return get_watch_item(session, item.id)


def delete_watch_item(session: Session, watch_item_id: int) -> dict[str, bool | int]:
    item = session.get(WatchItem, watch_item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch item not found")

    session.delete(item)
    session.commit()
    return {"id": watch_item_id, "deleted": True}


def get_watch_item(session: Session, watch_item_id: int) -> WatchItemResponse:
    item = session.scalar(
        select(WatchItem).options(joinedload(WatchItem.alerts)).where(WatchItem.id == watch_item_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch item not found")
    return watch_item_to_response(item)


def evaluate_watch_items(session: Session) -> WatchEvaluationResponse:
    now = datetime.now(UTC)
    items = session.scalars(select(WatchItem).where(WatchItem.enabled.is_(True)).order_by(WatchItem.id)).all()
    reports = recent_generated_reports(session)
    alerts: list[WatchAlert] = []

    for item in items:
        match = best_report_match(item, reports)
        item.last_checked_at = now
        if match is None:
            item.status = "quiet"
            item.last_summary = "No meaningful match in the latest saved reports."
            continue

        report, matched_terms = match
        item.status = "alert"
        item.last_matched_at = now
        item.last_summary = build_watch_summary(report, matched_terms)
        item.trigger_metadata = {
            **(item.trigger_metadata or {}),
            "matched_terms": matched_terms,
            "matched_report_id": report.id,
            "matched_report_type": report.report_type,
        }

        if not existing_alert_for_report(session, item.id, report.id):
            alert = WatchAlert(
                watch_item_id=item.id,
                report_id=report.id,
                title=f"{item.title} matched new evidence",
                message=item.last_summary,
                status="new",
                triggered_at=now,
                alert_metadata={
                    "matched_terms": matched_terms,
                    "report_type": report.report_type,
                    "signal_label": (report.report_metadata or {}).get("signal_label"),
                    "change_label": (report.report_metadata or {}).get("change_label"),
                },
            )
            session.add(alert)
            alerts.append(alert)

    session.commit()
    for alert in alerts:
        session.refresh(alert)

    return WatchEvaluationResponse(
        checked=len(items),
        triggered=len(alerts),
        alerts=[watch_alert_to_response(alert) for alert in alerts],
    )


def recent_generated_reports(session: Session) -> list[Report]:
    return session.scalars(
        select(Report)
        .where(Report.status == "generated")
        .order_by(desc(Report.as_of), desc(Report.id))
        .limit(30)
    ).all()


def best_report_match(item: WatchItem, reports: list[Report]) -> tuple[Report, list[str]] | None:
    query_terms = meaningful_terms(f"{item.title} {item.query}")
    if not query_terms:
        return None

    allowed_report_types = CATEGORY_REPORT_TYPES.get(item.category)
    best: tuple[Report, list[str]] | None = None
    for report in reports:
        if allowed_report_types and report.report_type not in allowed_report_types:
            continue
        text = f"{report.title} {report.summary or ''} {report.body}".lower()
        matched_terms = sorted(term for term in query_terms if term in text)
        minimum_matches = 2 if len(query_terms) >= 4 else 1
        if len(matched_terms) < minimum_matches:
            continue
        if best is None or len(matched_terms) > len(best[1]):
            best = (report, matched_terms)
    return best


def existing_alert_for_report(session: Session, watch_item_id: int, report_id: int) -> bool:
    existing = session.scalar(
        select(WatchAlert.id)
        .where(WatchAlert.watch_item_id == watch_item_id, WatchAlert.report_id == report_id)
        .limit(1)
    )
    return existing is not None


def meaningful_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 4 and token not in STOP_WORDS
    }


def build_watch_summary(report: Report, matched_terms: list[str]) -> str:
    label = (report.report_metadata or {}).get("signal_label") or report.confidence
    change = (report.report_metadata or {}).get("change_label") or "Latest saved report"
    matched = ", ".join(matched_terms[:5])
    summary = report.summary or report.body.splitlines()[0] if report.body else "Matched latest report evidence."
    return f"{label} / {change}. Matched {matched}. {summary[:360]}"


def watch_item_to_response(item: WatchItem) -> WatchItemResponse:
    return WatchItemResponse(
        id=item.id,
        title=item.title,
        category=item.category,
        query=item.query,
        status=item.status,
        priority=item.priority,
        enabled=item.enabled,
        last_checked_at=item.last_checked_at,
        last_matched_at=item.last_matched_at,
        last_summary=item.last_summary,
        metadata=item.trigger_metadata or {},
        created_at=item.created_at,
        updated_at=item.updated_at,
        alerts=[watch_alert_to_response(alert) for alert in sorted(item.alerts, key=lambda alert: alert.id, reverse=True)],
    )


def watch_alert_to_response(alert: WatchAlert) -> WatchAlertResponse:
    return WatchAlertResponse(
        id=alert.id,
        watch_item_id=alert.watch_item_id,
        report_id=alert.report_id,
        title=alert.title,
        message=alert.message,
        status=alert.status,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        metadata=alert.alert_metadata or {},
    )
