"""Data contracts. Every boundary in the pipeline is a schema, not a convention."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Channel(str, Enum):
    web_form = "web_form"
    email = "email"
    chat = "chat"


class IntakeEvent(BaseModel):
    """Raw inbound request, normalized to one shape regardless of channel."""
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    channel: Channel
    sender: str
    body: str
    received_at: datetime = Field(default_factory=_now)


class Extraction(BaseModel):
    """What the model claims to have understood. Schema-validated:
    if the LLM returns malformed output, it never enters the pipeline."""
    intent: str
    urgency: int = Field(ge=1, le=5)
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class Decision(str, Enum):
    auto_approved = "auto_approved"
    queued_for_review = "queued_for_review"


class GateResult(BaseModel):
    event_id: str
    decision: Decision
    confidence: float
    threshold: float
    decided_at: datetime = Field(default_factory=_now)


class ReviewOutcome(str, Enum):
    approved = "approved"
    rejected = "rejected"


class ReviewItem(BaseModel):
    event: IntakeEvent
    extraction: Extraction
    gate: GateResult
    outcome: Optional[ReviewOutcome] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
