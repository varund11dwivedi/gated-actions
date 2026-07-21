"""The confidence gate. Small on purpose: the value is not cleverness,
it is that the threshold is explicit, logged, and recalibratable from
labelled outcomes instead of being a magic number in a prompt."""
from typing import Iterable, Tuple

from .schemas import Decision, Extraction, GateResult, IntakeEvent


class ConfidenceGate:
    def __init__(self, threshold: float = 0.75):
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be in (0, 1)")
        self.threshold = threshold

    def decide(self, event: IntakeEvent, extraction: Extraction) -> GateResult:
        decision = (Decision.auto_approved
                    if extraction.confidence >= self.threshold
                    else Decision.queued_for_review)
        return GateResult(event_id=event.event_id, decision=decision,
                          confidence=extraction.confidence,
                          threshold=self.threshold)

    def calibrate(self, labelled: Iterable[Tuple[float, bool]],
                  max_false_approval_rate: float = 0.05) -> float:
        """Choose the lowest threshold whose auto-approved set keeps the
        false-approval rate under the cap.

        `labelled` is (confidence, human_said_correct) from the review queue —
        the queue is not a fallback, it is the training data.
        """
        points = sorted(labelled, key=lambda p: p[0])
        best = 0.99
        candidates = sorted({round(c, 2) for c, _ in points})
        for t in candidates:
            above = [ok for c, ok in points if c >= t]
            if not above:
                continue
            false_rate = 1 - (sum(above) / len(above))
            if false_rate <= max_false_approval_rate:
                best = t
                break
        self.threshold = best
        return best
