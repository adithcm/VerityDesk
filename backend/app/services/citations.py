from app.schemas.agent import AgentCitation


def format_citation(citation: AgentCitation) -> str:
    parts = [citation.title]
    if citation.publisher:
        parts.append(citation.publisher)
    if citation.published_at:
        parts.append(f"published {citation.published_at}")
    if citation.retrieved_at:
        parts.append(f"retrieved {citation.retrieved_at}")
    if citation.url:
        parts.append(citation.url)
    return " | ".join(parts)


def format_sources_section(citations: list[AgentCitation]) -> str:
    if not citations:
        return "Sources:\n- No source citations were available for this response."

    lines = ["Sources:"]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"{index}. {format_citation(citation)}")
    return "\n".join(lines)
