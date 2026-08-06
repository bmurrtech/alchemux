"""Shared recovery guidance for rate-limit fractures."""

from typing import Optional


RATE_LIMIT_ADVICE = (
    "Rate limited (HTTP 429/402). The site is soft-blocking this IP for overuse. "
    "Open the URL in a browser, solve any CAPTCHA, then enable cookies in "
    "alchemux config (Download Reliability), or in alchemux setup after enabling "
    "video (at your own risk). If you use multiple IPs, match the CAPTCHA IP. "
    "See docs/configs.md."
)


def get_rate_limit_advice(error_text: Optional[str]) -> Optional[str]:
    """Return recovery guidance when an error represents an HTTP 429 or 402."""
    if not error_text:
        return None

    normalized = error_text.lower()
    if (
        "429" in normalized
        or "too many requests" in normalized
        or "402" in normalized
        or "payment required" in normalized
    ):
        return RATE_LIMIT_ADVICE
    return None
