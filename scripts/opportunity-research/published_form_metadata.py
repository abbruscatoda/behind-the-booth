"""Conservatively read authored Google Forms metadata exposed on a public page.

FB_PUBLIC_LOAD_DATA_ is a published form schema, not respondent submissions.
Only already-delivered HTML is inspected; no formResponse requests, credentials,
answer entry, browser automation, or guessed question choices. Schema evidence
does NOT make a multipage form complete or prove that it accepts responses.
"""
from __future__ import annotations

import json
import re

from verifier import clean

_ASSIGN = re.compile(r"(?<![A-Za-z0-9_])(?:var\s+)?FB_PUBLIC_LOAD_DATA_\s*=", re.I)
_FEE_TERMS = re.compile(
    r"(?i)(?:\$\s*\d{1,5}|(?:booth|table|tent|space|stall|application|"
    r"registration|vendor|co[- ]?op|deposit)\s+(?:fees?|prices?|costs?)|"
    r"per[- ]event|non[- ]?refundable|waived?\s+for|table of fees)"
)
_DATE_TERMS = re.compile(r"(?i)(?:applications?\s+(?:due|close|deadline)|registration\s+(?:due|close|deadline))")
_REQUIREMENT_TERMS = re.compile(
    r"(?i)\b(?:must|required|requirement|eligible|ineligible|prohibited|"
    r"insurance|permit|license|sales tax|tax id|electricity|power|"
    r"food vendors?|craft vendors?|artisans?|tent weights?|selection|"
    r"payment|nonrefundable|non-refundable|set[- ]?up|load[- ]?in|"
    r"category|categories|restrictions?)\b"
)
_MAX_SCRIPT = 500_000
_MAX_STRINGS = 180
_MAX_DEPTH = 18
# Organizer introductions can contain several pages of published fee terms.
# Keep them available to the bounded field extractor rather than dropping the
# entire price section because the surrounding introduction is long.
_MAX_TEXT = 16_000


def _authored_strings(value, depth=0):
    if depth >= _MAX_DEPTH:
        return
    if isinstance(value, str):
        if 8 <= len(value) <= _MAX_TEXT:
            cleaned = clean(value)
            if (_FEE_TERMS.search(cleaned) or _DATE_TERMS.search(cleaned)
                or _REQUIREMENT_TERMS.search(cleaned)):
                yield cleaned
    elif isinstance(value, list):
        for child in value[:500]:
            yield from _authored_strings(child, depth + 1)


def public_form_sections(doc):
    """Return bounded, fee/date-related authored strings from a public form.

    Google may change or omit its schema. In that case return [] and let
    normal visible-text and document-link research handle the page instead.
    """
    all_sections = []
    seen = set()
    for node in doc.root.walk():
        if node.tag != "script":
            continue
        raw = "".join(child for child in node.children if isinstance(child, str))
        if not raw or len(raw) > _MAX_SCRIPT:
            continue
        match = _ASSIGN.search(raw)
        if not match:
            continue
        try:
            data, _ = json.JSONDecoder().raw_decode(raw[match.end():].lstrip())
        except (ValueError, TypeError, RecursionError):
            continue
        # Schema payload shape: [form config, [published form details], ...].
        # Do not parse arbitrary top-level keys, URLs, respondent data, IDs.
        if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
            continue
        for section in _authored_strings(data[1]):
            if section not in seen:
                seen.add(section)
                all_sections.append(section)
                if len(all_sections) >= _MAX_STRINGS:
                    return all_sections
    return all_sections
