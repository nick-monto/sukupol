"""LLM-authored text validation: hard-reject malformed content.

Every consumer that accepts LLM-generated text destined for the persistent
quest/lore path should use `validate_authored_text` rather than silently
coercing malformed input.
"""

from __future__ import annotations

import re

from .sanitize import sanitize_prompt_input

# Characters that MUST NOT appear in authored text (checked *before*
# sanitization — the sanitizer strips most of these, but we hard-reject
# at the validation boundary so the caller knows the input was bad):
#   C0 (0x00-0x1F) minus whitespace already converted by sanitize
#   DEL (0x7F)
#   C1 (0x80-0x9F)
#   U+202E RIGHT-TO-LEFT OVERRIDE
#   \n, \r (should be converted by sanitize; if present, reject)
_REJECT_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u202e\n\r]"
)


def validate_authored_text(s: str, *, max_len: int) -> str | None:
    """Validate and sanitise LLM-authored text; return ``None`` on rejection.

    Returns ``None`` if *s* contains any rejected control / override / newline
    character, or is empty after sanitisation, or exceeds *max_len*.
    Otherwise returns the sanitised, stripped text.
    """
    # 1. Hard-reject any character that should never appear in authored text.
    if _REJECT_RE.search(s):
        return None

    # 2. Sanitize remaining text (strip remaining control chars, collapse
    #    whitespace — this handles multi-byte whitespace and edge cases).
    s = sanitize_prompt_input(s)

    # 3. Reject if nothing remains after cleaning.
    if not s.strip():
        return None

    # 4. Enforce length cap.
    if len(s) > max_len:
        return None

    return s.strip()
