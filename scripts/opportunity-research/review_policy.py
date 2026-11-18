"""Conservative review-noise policy for previously published opportunities.

A failed read is not evidence that a source has changed. Never suppress verified
identity conflicts, material changes, or confirmed closure.
"""

def defer_inconclusive_review(item, result):
    if not item or item.get("publication") != "published":
        return False
    if result.get("decision") != "review":
        return False

    # Transient failures are produced without a candidate by run.py. An
    # unexpected verification or identity error must still reach review.
    reason = result.get("reason", "")
    if not result.get("candidate") and not result.get("research_suggestions"):
        return reason == (
            "Official source could not be read reliably. "
            "The next successful run can resolve this automatically."
        )

    # The organizer-bound First Night adapter confirms the exact event
    # identity and date on its public source before collecting form details.
    # An inaccessible form alone does not invalidate a previous approval.
    suggestions = result.get("research_suggestions") or {}
    if (
        result.get("policy") == "artsplosure-google-v1"
        and suggestions.get("form_readable") is False
        and suggestions.get("application_url") == item.get("application_url")
        and suggestions.get("starts_on") == item.get("starts_on")
        and suggestions.get("ends_on") == item.get("ends_on")
        and "Application could not be read by the public worker" in reason
    ):
        return True

    return False
