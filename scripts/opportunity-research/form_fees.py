"""Extract independently labeled fees from a readable official vendor form.

Only quote amounts adjacent to their fee type. Never infer missing fees from
an application requirement, a generic pricing page, or another fee category.
Ambiguous competing amounts for the same type remain unverified.
"""
from __future__ import annotations
import re

DOLLARS = r"\$\s*([0-9]{1,5}(?:\.[0-9]{1,2})?)"
APPLICATION = r"(?:non[- ]?refundable\s+)?(?:(?:vendor|craft)\s+)?application\s+fee"
BOOTH = r"(?<!Second )(?<!Additional )(?:(?:event|per[- ]event|standard|daily|single[- ]day)\s+)?(?:booth|stall|table|space)\s+fee"

# Absence of a published price is never evidence that the price is zero.
# Explicit free-intake wording in the *same verified application* is evidence.
FREE_APPLICATION = re.compile(
    r"\b(?:there\s*(?:is|['’]s)\s+|(?:we\s+)?charge\s+)?no\s+(?:(?:vendor|craft|registration)\s+)?application\s+fee\b"
    r"|\bapplication\s+fee\s*[:=]\s*\$\s*0(?:\.00)?\b"
    r"|\b\$\s*0(?:\.00)?\s+application\s+fee\b", re.I,
)

def explicitly_free_application(text):
    """True only for explicit zero-cost application wording, not missing prices."""
    normalized = ' '.join((text or '').split())
    return bool(FREE_APPLICATION.search(normalized))

def _patterns(label):
    # Amount before label, e.g. "$28 NON-REFUNDABLE Application Fee"
    # or "$35 Event Booth Fee".
    first = re.compile(DOLLARS + r"\s*" + label + r"\b", re.I)
    # Label before amount, e.g. "Application fee: $28". Do not traverse
    # another fee label before picking up an unrelated dollar value.
    second = re.compile(label + r"\b(?:(?!\b(?:fee|deposit|booth|stall|table)\b)[^.$]){0,45}" + DOLLARS, re.I)
    return first, second

PRIOR_PRICE_LABEL = re.compile(
    r"\b(?:application|booth|stall|table|space|ticket|deposit|admission)"
    r"\s+(?:fee|cost|price|tickets?)\s*[:=]\s*$", re.I,
)

def _amount_attached_to_previous_label(text, start):
    # "Booth fee: $125 Application fee: $0" has TWO label-first amounts.
    # The $125 must not also become an application price.
    return bool(PRIOR_PRICE_LABEL.search(text[max(0,start-60):start]))


def _amount(text, label):
    before, after = _patterns(label)
    # The "$28 application fee $35 booth fee" sequence must not attach
    # $35 to the preceding "application fee" label. Prefer amount-first
    # evidence when available, and otherwise reject a label-first match if
    # the dollar amount is immediately followed by a *different* fee label.
    matches = [m for m in before.finditer(text)
               if not _amount_attached_to_previous_label(text,m.start())]
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

# Google Forms often writes "$30 per event: 10'x10' booth fee" rather
# than "$30 booth fee". The price and the booth label must still occur in
# the same bounded clause, and no other currency amount may intervene.
EVENT_BOOTH = re.compile(
    DOLLARS
    + r"\s*(?:per|each)\s+event\s*[:\-–]?\s*"
    + r"(?:[0-9]{1,2}\s*['′]?\s*[x×]\s*[0-9]{1,2}\s*['′]?\s*)?"
    + r"(?:standard\s+)?(?:booth|stall|table|tent|space)\s*(?:fee|cost|price)\b",
    re.I,
)


def _event_booth_amount(text):
    values = {round(float(match.group(1)), 2) for match in EVENT_BOOTH.finditer(text)
              if not _amount_attached_to_previous_label(text,match.start())}
    return next(iter(values)) if len(values) == 1 else None


def extract_amount_first_fees(text):
    """Extract ONLY amounts that precede their fee labels on a public form.

    Other extractors handle exact label-first fields. This avoids taking the
    dollar amount of the NEXT question ("Application fee: $0. Deposit: $40")
    as if it were the current question's price.
    """
    normalized = " ".join((text or "").split())
    def unique(patterns):
        amounts = set()
        for pattern in patterns:
            for match in pattern.finditer(normalized):
                if _amount_attached_to_previous_label(normalized,match.start()):
                    continue
                amount = round(float(match.group(1)), 2)
                if 0 < amount <= 10000:
                    amounts.add(amount)
        return next(iter(amounts)) if len(amounts) == 1 else None
    return {
        "application_fee": unique((_patterns(APPLICATION)[0],)),
        "booth_fee": unique((_patterns(BOOTH)[0], EVENT_BOOTH)),
    }


def extract_labeled_fees(text):
    """Return unambiguous standalone vendor application and booth fees.

    Multitier, category-specific or conflicting prices are left unknown;
    None never means free. Source ownership is verified by the caller.
    """
    normalized = " ".join((text or "").split())
    standard = _amount(normalized, BOOTH)
    event_options = list(EVENT_BOOTH.finditer(normalized))
    # Multiple priced event booth sizes are separate tiers, not one universal standard.
    per_event = _event_booth_amount(normalized)
    booth = (None if len({m.group(1) for m in event_options}) > 1
             else standard if per_event is None
             else per_event if standard is None or standard == per_event else None)
    application_fee = _amount(normalized, APPLICATION)
    # Both a positive charge and an explicit free-intake statement are
    # contradictory; do not pick one arbitrarily.
    if explicitly_free_application(normalized):
        application_fee = 0.0 if application_fee is None else None
    return {
        "application_fee": application_fee,
        "booth_fee": booth,
    }


def extract_fee_conditions(text):
    """Only the clear, local conditions attached to a fee, never guesses."""
    normalized = " ".join((text or "").split())
    application = re.search(
        DOLLARS + r"\s*(?:non[- ]?refundable\s+)?(?:craft\s+|vendor\s+)?application\s+fee\b"
        + r"[^.]{0,135}", normalized, re.I,
    )
    booth = re.search(EVENT_BOOTH.pattern + r"[^.]{0,100}", normalized, re.I)
    application_context = application.group(0) if application else ""
    booth_context = booth.group(0) if booth else ""
    return {
        "application_fee_waived_for_current_vendors": bool(
            re.search(r"waived?\s+for\s+(?:current|existing)\s+vendors", application_context, re.I)
        ),
        "application_fee_nonrefundable": bool(re.search(r"non[- ]?refundable", application_context, re.I)),
        "booth_fee_due_on_acceptance": bool(
            re.search(r"payable\s+upon\s+acceptance|due\s+(?:upon|on)\s+acceptance", booth_context, re.I)
        ),
        "booth_size_10x10": bool(re.search(r"10\s*['′]?\s*[x×]\s*10\s*['′]?", booth_context, re.I)),
    }


def extract_linked_fee_options(text):
    """Extract labeled add-on fees from a separately validated official PDF.

    Does not treat regular market daily vendor tiers as craft-fair booth
    pricing. These optional fees are notes, not standard booth fees.
    """
    normalized = " ".join((text or "").split())
    labels = {
        "second_space": r"\bSecond\s+Space\s+Fee\b",
        "co_op_tent": r"\bCo[- ]?op\s+Vending\s+Arrangement\s+Fee\b",
    }
    result = {}
    for key, label in labels.items():
        matches = re.findall(label + r"(?:(?!\b(?:Fee|Vendor Tier)\b).){0,95}?" + DOLLARS, normalized, re.I)
        values = {round(float(value), 2) for value in matches if 0 < float(value) < 1000}
        if len(values) == 1:
            result[key] = next(iter(values))
    return result
