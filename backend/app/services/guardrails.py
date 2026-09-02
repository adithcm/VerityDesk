from app.schemas.agent import GuardrailCheck


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
