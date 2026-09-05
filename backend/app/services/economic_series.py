from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomicSeriesInfo:
    series_id: str
    label: str
    description: str
    unit: str | None = None


ECONOMIC_SERIES_LABELS: dict[str, EconomicSeriesInfo] = {
    "UNRATE": EconomicSeriesInfo(
        series_id="UNRATE",
        label="Unemployment Rate",
        description="Share of the U.S. labor force that is unemployed.",
        unit="percent",
    ),
    "FEDFUNDS": EconomicSeriesInfo(
        series_id="FEDFUNDS",
        label="Federal Funds Rate",
        description="Effective federal funds rate.",
        unit="percent",
    ),
    "MORTGAGE30US": EconomicSeriesInfo(
        series_id="MORTGAGE30US",
        label="30-Year Fixed Mortgage Rate",
        description="Average U.S. 30-year fixed mortgage rate.",
        unit="percent",
    ),
}


def economic_series_info(series_id: str, fallback_name: str | None = None) -> EconomicSeriesInfo:
    normalized = series_id.strip().upper()
    if normalized in ECONOMIC_SERIES_LABELS:
        return ECONOMIC_SERIES_LABELS[normalized]

    return EconomicSeriesInfo(
        series_id=normalized,
        label=fallback_name or normalized,
        description="Economic data series.",
    )


def economic_series_label(series_id: str, fallback_name: str | None = None) -> str:
    return economic_series_info(series_id, fallback_name).label
