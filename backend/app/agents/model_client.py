from __future__ import annotations

import json
import logging
import ssl
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class ResearchSummarizer(Protocol):
    def summarize(self, *, agent_name: str, instructions: str, evidence: str) -> str:
        """Summarize evidence for a domain agent."""


class TemplateResearchSummarizer:
    def summarize(self, *, agent_name: str, instructions: str, evidence: str) -> str:
        if not evidence.strip():
            return f"{agent_name} did not find enough evidence to produce a source-backed summary."

        lines = [line for line in evidence.splitlines() if line.strip()]
        if agent_name == "SynthesisAgent":
            return build_template_synthesis_summary(lines)

        preview = "\n".join(lines[:6])
        return f"{agent_name} reviewed the available evidence:\n{preview}"


class OpenAIResearchSummarizer:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def summarize(self, *, agent_name: str, instructions: str, evidence: str) -> str:
        if not self.settings.openai_api_key:
            logger.info("OpenAI API key not configured; using template summarizer for %s", agent_name)
            return TemplateResearchSummarizer().summarize(
                agent_name=agent_name,
                instructions=instructions,
                evidence=evidence,
            )

        payload = {
            "model": self.settings.openai_model,
            "store": False,
            "max_output_tokens": 1200,
            "reasoning": {"effort": "minimal"},
            "input": build_prompt(agent_name, instructions, evidence),
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            logger.info("Calling OpenAI model %s for %s", self.settings.openai_model, agent_name)
            context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(request, timeout=30, context=context) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            logger.warning("OpenAI request failed for %s with status %s; using template fallback", agent_name, error.code)
            return TemplateResearchSummarizer().summarize(
                agent_name=agent_name,
                instructions=instructions,
                evidence=evidence,
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            logger.warning("OpenAI request failed for %s: %s; using template fallback", agent_name, error)
            return TemplateResearchSummarizer().summarize(
                agent_name=agent_name,
                instructions=instructions,
                evidence=evidence,
            )

        text = extract_response_text(body)
        if text:
            logger.info("OpenAI response received for %s", agent_name)
            return text

        logger.warning(
            "OpenAI response for %s did not contain text; status=%s incomplete_details=%s output_types=%s usage=%s; "
            "using template fallback",
            agent_name,
            body.get("status"),
            body.get("incomplete_details"),
            output_item_types(body),
            body.get("usage"),
        )
        return TemplateResearchSummarizer().summarize(agent_name=agent_name, instructions=instructions, evidence=evidence)


def build_default_summarizer(settings: Settings | None = None) -> ResearchSummarizer:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return OpenAIResearchSummarizer(settings)
    return TemplateResearchSummarizer()


def build_template_synthesis_summary(lines: list[str]) -> str:
    evidence_lines = [
        clean_evidence_line(line)
        for line in lines
        if line.startswith("- ") and "|" in line and not line.startswith("- live_web:")
    ]
    evidence_lines = [line for line in evidence_lines if line]
    if not evidence_lines:
        return "I do not have enough current source-backed evidence to answer this with confidence yet."

    opening = "Here is the clearest source-backed read from the available evidence."
    details = " ".join(evidence_lines[:3])
    return f"{opening}\n\n{details}"


def clean_evidence_line(line: str) -> str:
    text = line[2:].strip()
    if " - " not in text:
        return ""
    _source, detail = text.split(" - ", 1)
    return detail.strip()


def build_prompt(agent_name: str, instructions: str, evidence: str) -> str:
    return (
        f"You are {agent_name}, a careful research agent for a local market intelligence app.\n"
        "Use only the provided evidence. Do not invent facts. Do not give direct buy, sell, or hold instructions. "
        "Keep the answer concise and include uncertainty when evidence is thin.\n\n"
        f"Agent instructions:\n{instructions}\n\n"
        f"Evidence:\n{evidence}"
    )


def output_item_types(body: dict) -> list[str]:
    return [item.get("type", "unknown") for item in body.get("output", []) if isinstance(item, dict)]


def extract_response_text(body: dict) -> str | None:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []
    for item in body.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                text_parts.append(content["text"])

    text = "\n".join(text_parts).strip()
    return text or None
