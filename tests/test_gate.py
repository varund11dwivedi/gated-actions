import pytest

from gated_actions.gate import ConfidenceGate
from gated_actions.schemas import Channel, Decision, Extraction, IntakeEvent


def make(conf):
    e = IntakeEvent(channel=Channel.email, sender="a@b.c", body="hello")
    x = Extraction(intent="support", urgency=3, summary="s", confidence=conf)
    return e, x


def test_high_confidence_auto_approves():
    g = ConfidenceGate(0.75)
    e, x = make(0.9)
    assert g.decide(e, x).decision == Decision.auto_approved


def test_low_confidence_queues():
    g = ConfidenceGate(0.75)
    e, x = make(0.5)
    assert g.decide(e, x).decision == Decision.queued_for_review


def test_boundary_is_inclusive():
    g = ConfidenceGate(0.75)
    e, x = make(0.75)
    assert g.decide(e, x).decision == Decision.auto_approved


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        ConfidenceGate(1.5)


def test_calibration_lowers_threshold_when_evidence_supports_it():
    g = ConfidenceGate(0.9)
    labelled = [(0.6, False), (0.7, True), (0.8, True), (0.85, True), (0.95, True)]
    t = g.calibrate(labelled, max_false_approval_rate=0.05)
    assert t <= 0.7
    assert g.threshold == t


def test_calibration_stays_high_when_model_is_overconfident():
    g = ConfidenceGate(0.75)
    labelled = [(0.8, False), (0.85, False), (0.9, True)]
    t = g.calibrate(labelled, max_false_approval_rate=0.05)
    assert t >= 0.9
