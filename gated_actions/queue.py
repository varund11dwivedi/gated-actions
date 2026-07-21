"""Review queue + append-only audit log. In-memory for the reference
implementation; the interface is what matters — swap for Postgres and
nothing upstream changes."""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .schemas import (Decision, Extraction, GateResult, IntakeEvent,
                      ReviewItem, ReviewOutcome)


class ReviewQueue:
    def __init__(self) -> None:
        self._items: Dict[str, ReviewItem] = {}
        self._audit: List[dict] = []

    # -- writes ------------------------------------------------------------
    def record(self, event: IntakeEvent, extraction: Extraction,
               gate: GateResult) -> ReviewItem:
        item = ReviewItem(event=event, extraction=extraction, gate=gate)
        if gate.decision == Decision.queued_for_review:
            self._items[event.event_id] = item
        self._log("gate_decision", event.event_id,
                  decision=gate.decision.value, confidence=gate.confidence,
                  threshold=gate.threshold)
        return item

    def resolve(self, event_id: str, outcome: ReviewOutcome,
                reviewer: str) -> Optional[ReviewItem]:
        item = self._items.pop(event_id, None)
        if item is None:
            return None
        item.outcome = outcome
        item.reviewed_by = reviewer
        item.reviewed_at = datetime.now(timezone.utc)
        self._log("review_resolved", event_id,
                  outcome=outcome.value, reviewer=reviewer)
        return item

    # -- reads -------------------------------------------------------------
    def pending(self) -> List[ReviewItem]:
        return list(self._items.values())

    def audit_log(self) -> List[dict]:
        return list(self._audit)

    def labelled_outcomes(self):
        """(confidence, approved) pairs for gate recalibration."""
        for entry in self._audit:
            if entry["action"] == "review_resolved":
                yield entry  # joined by caller against gate_decision entries

    def _log(self, action: str, event_id: str, **fields) -> None:
        self._audit.append({
            "at": datetime.now(timezone.utc).isoformat(),
            "action": action, "event_id": event_id, **fields,
        })
