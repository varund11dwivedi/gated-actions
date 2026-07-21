from fastapi.testclient import TestClient

import gated_actions.app as appmod
from gated_actions.app import app

client = TestClient(app)


def _reset():
    appmod.queue._items.clear()
    appmod.queue._audit.clear()


def test_confident_message_is_auto_actioned():
    _reset()
    r = client.post("/intake", json={
        "channel": "email", "sender": "cust@example.com",
        "body": "Our dashboard is down with an error, urgent - please help, "
                "this outage is blocking the whole team right now."})
    assert r.status_code == 200
    body = r.json()
    assert body["auto_actioned"] is True
    assert body["intent"] == "support"
    assert client.get("/review").json()["pending"] == []


def test_ambiguous_message_is_queued_not_actioned():
    _reset()
    r = client.post("/intake", json={
        "channel": "chat", "sender": "x", "body": "hi there"})
    assert r.json()["auto_actioned"] is False
    pending = client.get("/review").json()["pending"]
    assert len(pending) == 1


def test_human_decision_resolves_and_audits():
    _reset()
    r = client.post("/intake", json={
        "channel": "chat", "sender": "x", "body": "quick question maybe"})
    eid = r.json()["event_id"]
    ok = client.post(f"/review/{eid}/approved", params={"reviewer": "varun"})
    assert ok.status_code == 200
    assert client.get("/review").json()["pending"] == []
    actions = [e["action"] for e in client.get("/audit").json()["log"]]
    assert actions == ["gate_decision", "review_resolved"]


def test_resolving_unknown_event_404s():
    _reset()
    assert client.post("/review/nope/approved").status_code == 404


def test_malformed_intake_rejected_by_schema():
    _reset()
    r = client.post("/intake", json={"channel": "carrier_pigeon",
                                     "sender": "x", "body": "hi"})
    assert r.status_code == 422
