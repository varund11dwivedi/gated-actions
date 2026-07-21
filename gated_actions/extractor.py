"""Extraction layer. The Protocol is the point: the pipeline depends on the
contract, not on any vendor. MockExtractor lets the whole system run and be
tested without an API key; swap in a real adapter without touching the gate,
queue, or app."""
from typing import Protocol

from .schemas import Extraction, IntakeEvent


class Extractor(Protocol):
    def extract(self, event: IntakeEvent) -> Extraction: ...


_URGENT = ("outage", "down", "urgent", "asap", "immediately", "broken")
_INTENTS = {
    "refund": ("refund", "money back", "charge"),
    "cancellation": ("cancel", "unsubscribe"),
    "support": ("error", "bug", "broken", "help", "issue", "down", "outage"),
    "sales": ("pricing", "quote", "demo", "buy", "upgrade"),
}


class MockExtractor:
    """Deterministic keyword extractor standing in for an LLM call.

    Deliberately imperfect: short or ambiguous messages produce low confidence,
    which is exactly what exercises the review queue."""

    def extract(self, event: IntakeEvent) -> Extraction:
        text = event.body.lower()
        intent, hits = "general", 0
        for name, keywords in _INTENTS.items():
            n = sum(k in text for k in keywords)
            if n > hits:
                intent, hits = name, n
        urgency = 5 if any(k in text for k in _URGENT) else (3 if hits else 2)
        # Confidence grows with evidence and message length; capped below 1.0
        # because certainty is earned by calibration, not asserted.
        confidence = min(0.55 + 0.15 * hits + min(len(text), 200) / 1000.0, 0.98)
        if hits == 0:
            confidence = min(confidence, 0.45)
        summary = event.body[:140]
        return Extraction(intent=intent, urgency=urgency,
                          summary=summary, confidence=round(confidence, 3))
