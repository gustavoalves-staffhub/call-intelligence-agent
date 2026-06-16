"""Step 6: CRM workspace routing."""

from app.models.call_event import CallEvent
from app.models.match_result import MatchMethod, MatchResult


def route(match: MatchResult, event: CallEvent) -> str:
    """Return the owning workspace name for a matched lead."""

    if match.method is MatchMethod.UNMATCHED or not match.workspace:
        raise ValueError("Cannot route an unmatched call to a CRM workspace.")

    if match.workspace != event.workspace:
        return match.workspace

    return event.workspace
