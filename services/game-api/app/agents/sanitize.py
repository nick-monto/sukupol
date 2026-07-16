"""Prompt-bound input sanitization: strip control chars, directional overrides, collapse whitespace, truncate.

This is the single source of truth for embedding untrusted strings
(player messages, NPC names, etc.) inside LLM prompts.  Every agent
builder that formats a user prompt should import and use
`sanitize_prompt_input` rather than inlining its own variant.
"""

from __future__ import annotations

import re

# Characters that are *removed* entirely (not converted to space):
#   C0 (0x00-0x1F) minus \t \r \n — those become spaces
#   DEL (0x7F)
#   C1 (0x80-0x9F)
#   U+2028 LINE SEPARATOR
#   U+2029 PARAGRAPH SEPARATOR
#   U+202E RIGHT-TO-LEFT OVERRIDE
_STRIP_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029\u202e]"
)

# Characters converted to a plain space before collapsing.
_CONVERT_RE = re.compile(r"[\r\n\t]")


def sanitize_prompt_input(s: str, *, max_len: int = 2000) -> str:
    """Strip control chars / directional overrides; collapse whitespace; truncate.

    * Removes C0 (except ``\\t``/``\\r``/``\\n``), DEL, C1,
      U+2028, U+2029, and U+202E outright.
    * Converts ``\\r``, ``\\n``, ``\\t`` to a single space.
    * Collapses runs of whitespace (including the converted ones) to one space.
    * Truncates to ``max_len`` on the last word boundary ≤ ``max_len``;
      hard-cuts if no such boundary.
    * Strips leading/trailing whitespace.
    * Idempotent: ``sanitize_prompt_input(sanitize_prompt_input(x)) == x``.
    """
    # 1. Strip dangerous control chars.
    s = _STRIP_RE.sub("", s)
    # 2. Convert newlines / tabs to spaces.
    s = _CONVERT_RE.sub(" ", s)
    # 3. Collapse runs of space characters.
    s = re.sub(r" +", " ", s)
    # 4. Truncate on a word boundary.
    if len(s) > max_len:
        boundary = s.rfind(" ", 0, max_len + 1)
        if boundary != -1:
            s = s[:boundary]
        else:
            s = s[:max_len]
    # 5. Strip leading/trailing whitespace.
    return s.strip()
