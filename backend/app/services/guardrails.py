import re

from app.schemas.agent import AgentCitation, AgentQueryRequest, ConfidenceLevel, GuardrailCheck


FINANCIAL_DISCLAIMER = (
    "This is not financial advice. The information shown is for research and "
    "educational purposes only. Investing involves risk. Do your own research "
    "and consider consulting a licensed financial advisor before making "
    "investment decisions."
)

BANNED_DIRECT_ADVICE_PHRASES = (
    "buy this stock",
    "sell this stock",
    "hold this stock",
    "you should buy",
    "you should sell",
    "you should invest",
    "guaranteed return",
    "risk-free",
)

PRICE_TARGET_PATTERNS = (
    re.compile(r"\b(price target|target price|pt)\b", re.IGNORECASE),
    re.compile(r"\b(to|at|toward)\s+\$?\d+(?:\.\d+)?\b", re.IGNORECASE),
)

REQUIRED_INVESTMENT_RESEARCH_SECTIONS = (
    "bullish factors",
    "bearish factors",
    "key risks",
    "sources",
    "not a recommendation",
)


def find_banned_direct_advice_phrases(text: str) -> list[str]:
    normalized_text = text.lower()
    return [phrase for phrase in BANNED_DIRECT_ADVICE_PHRASES if phrase in normalized_text]


def check_investment_guardrails(text: str) -> GuardrailCheck:
    banned_phrases = find_banned_direct_advice_phrases(text)
    issues: list[str] = []

    if banned_phrases:
        issues.append("Output contains direct investment advice wording.")

    if "not financial advice" not in text.lower():
        issues.append("Output is missing the required financial disclaimer.")

    status = "needs_revision" if issues else "passed"

    return GuardrailCheck(
        status=status,
        disclaimer=FINANCIAL_DISCLAIMER,
        issues=issues,
        banned_phrases_found=banned_phrases,
        required_sections=list(REQUIRED_INVESTMENT_RESEARCH_SECTIONS),
    )


def enforce_agent_guardrails(
    text: str,
    *,
    request: AgentQueryRequest,
    citations: list[AgentCitation],
    confidence: ConfidenceLevel,
) -> GuardrailCheck:
    base_check = check_investment_guardrails(text)
    issues = list(base_check.issues)

    if request.safety_level == "investment_research" and not citations:
        issues.append("Investment-oriented response has no citations.")

    if confidence == "low":
        issues.append("Response confidence is low; answer must clearly state uncertainty.")

    if has_unsupported_price_target(text, citations):
        issues.append("Output contains an unsupported price-target style statement.")

    rewritten_text = rewrite_unsafe_text(text, issues)
    status = "blocked" if has_blocking_issue(issues) else "needs_revision" if issues else "passed"

    return GuardrailCheck(
        status=status,
        disclaimer=FINANCIAL_DISCLAIMER,
        issues=issues,
        banned_phrases_found=base_check.banned_phrases_found,
        required_sections=list(REQUIRED_INVESTMENT_RESEARCH_SECTIONS),
        rewritten_text=rewritten_text if rewritten_text != text else None,
    )


def has_unsupported_price_target(text: str, citations: list[AgentCitation]) -> bool:
    normalized_support = " ".join(citation.supports_claim for citation in citations).lower()
    mentions_target = all(pattern.search(text) for pattern in PRICE_TARGET_PATTERNS)
    return mentions_target and "price target" not in normalized_support


def has_blocking_issue(issues: list[str]) -> bool:
    return any("direct investment advice" in issue.lower() for issue in issues)


def rewrite_unsafe_text(text: str, issues: list[str]) -> str:
    rewritten = text
    replacements = {
        "you should buy": "a bullish scenario may consider",
        "you should sell": "a bearish scenario may consider",
        "you should invest": "a research workflow may consider",
        "buy this stock": "review this security as a research candidate",
        "sell this stock": "review downside risk for this security",
        "hold this stock": "continue monitoring this security as a research candidate",
        "guaranteed return": "uncertain potential outcome",
        "risk-free": "lower-risk but not risk-free",
    }
    for banned, replacement in replacements.items():
        rewritten = re.sub(re.escape(banned), replacement, rewritten, flags=re.IGNORECASE)

    if "Response confidence is low" in " ".join(issues) and "I do not have enough" not in rewritten:
        rewritten = (
            f"{rewritten}\n\n"
            "I do not have enough current source-backed evidence to answer this with high confidence."
        )

    return rewritten
