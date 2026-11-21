"""Extract independently labeled fees from a readable official vendor form.

Only quote amounts adjacent to their fee type. Never infer missing fees from
an application requirement, a generic pricing page, or another fee category.
Ambiguous competing amounts for the same type remain unverified.
"""
from __future__ import annotations
import re

DOLLARS = r"\$\s*([0-9]{1,5}(?:\.[0-9]{1,2})?)"
APPLICATION = r"(?:non[- ]?refundable\s+)?(?:vendor\s+)?application\s+fee"
BOOTH = r"(?:(?:event|per[- ]event|standard|daily|single[- ]day)\s+)?(?:booth|stall|table|space)\s+fee"

def _patterns(label):
    # Amount before label, e.g. "$28 NON-REFUNDABLE Application Fee"
    # or "$35 Event Booth Fee".
    first = re.compile(DOLLARS + r"\s*" + label + r"\b", re.I)
    # Label before amount, e.g. "Application fee: $28". Do not traverse
    # another fee label before picking up an unrelated dollar value.
    second = re.compile(label + r"\b(?:(?!\b(?:fee|deposit|booth|stall|table)\b)[^$]){0,45}" + DOLLARS, re.I)
    return first, second

def _amount(text, label):
    before, after = _patterns(label)
    # The "$28 application fee $35 booth fee" sequence must not attach
    # $35 to the preceding "application fee" label. Prefer amount-first
    # evidence when available, and otherwise reject a label-first match if
    # the dollar amount is immediately followed by a *different* fee label.
    matches = list(before.finditer(text))
    if not matches:
        other_fee = re.compile(
            r"\s*(?:(?:non[- ]?refundable|event|per[- ]event|standard|daily)\s+)?"
            r"(?:application|booth|stall|table|space)\s+fee\b", re.I)
        matches = [match for match in after.finditer(text)
                   if not other_fee.match(text[match.end():])]
    candidates = set()
    for match in matches:
        try:
            amount = round(float(match.group(1)), 2)
        except (ValueError, OverflowError):
            continue
        if 0 < amount <= 10000:
            candidates.add(amount)
    # Conflicting values may be different packages; don't call one "standard".
    return next(iter(candidates)) if len(candidates) == 1 else None

def extract_labeled_fees(text):
    """Return only verified application and per-event booth fee amounts."""
    normalized = " ".join((text or "").split())
    return {
        "application_fee": _amount(normalized, APPLICATION),
        "booth_fee": _amount(normalized, BOOTH),
    }
