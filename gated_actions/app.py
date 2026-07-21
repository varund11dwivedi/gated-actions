"""FastAPI surface. Four endpoints, one rule: no action without a gate
decision on record, and no gate decision without an audit entry."""
from fastapi import FastAPI, HTTPException

from .extractor import MockExtractor
from .gate import ConfidenceGate
from .queue import ReviewQueue
from .schemas import Decision, IntakeEvent, ReviewOutcome

app = FastAPI(title="gated-actions",
              description="Confidence-gated agent pipeline, reference implementation")

extractor = MockExtractor()
gate = ConfidenceGate(threshold=0.75)
queue = ReviewQueue()


@app.post("/intake")
def intake(event: IntakeEvent):
    extraction = extractor.extract(event)          # schema-validated
    result = gate.decide(event, extraction)        # explicit threshold
    queue.record(event, extraction, result)        # audit before action
    return {"event_id": event.event_id,
            "decision": result.decision,
            "confidence": extraction.confidence,
            "intent": extraction.intent,
            "auto_actioned": result.decision == Decision.auto_approved}


@app.get("/review")
def review_queue():
    return {"pending": queue.pending()}


@app.post("/review/{event_id}/{outcome}")
def resolve(event_id: str, outcome: ReviewOutcome, reviewer: str = "reviewer"):
    item = queue.resolve(event_id, outcome, reviewer)
    if item is None:
        raise HTTPException(404, "not in queue")
    return {"event_id": event_id, "outcome": outcome,
            "note": "human decision recorded; feeds threshold calibration"}


@app.get("/audit")
def audit():
    return {"log": queue.audit_log()}


@app.get("/")
def health():
    return {"status": "ok", "threshold": gate.threshold,
            "pending_reviews": len(queue.pending())}
