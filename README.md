# gated-actions

![tests](https://github.com/varund11dwivedi/gated-actions/actions/workflows/tests.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

A reference implementation of the pattern I use in every agent system that
touches production data: **AI proposes, a calibrated gate decides who acts —
the system or a human.**

Most agent pipelines advance on completion and audit later, which is how
confidently-wrong output compounds. This one advances on evidence:

```
intake -> extract (schema-validated) -> confidence gate -> auto-action
                                              |
                                              v  below threshold
                                        review queue -> human decides
                                              |
                                              v
                                labelled outcomes recalibrate the gate
```

## Why each piece exists

- **Schemas at every boundary** (`schemas.py`) — malformed LLM output is
  rejected at the edge by pydantic, not discovered downstream.
- **Extractor as a Protocol** (`extractor.py`) — the pipeline depends on a
  contract, not a vendor. The included `MockExtractor` is deterministic and
  deliberately imperfect, so the whole system runs and tests without an API
  key, and the review queue actually gets exercised.
- **An explicit, recalibratable threshold** (`gate.py`) — the gate is ~40
  lines because the value isn't cleverness: it's that the threshold is a
  logged number, and `calibrate()` recomputes it from human-labelled outcomes
  under a false-approval cap. The review queue is not a fallback; it is the
  training data.
- **Audit before action** (`queue.py`) — append-only log; every decision
  records its confidence and the threshold it was judged against.

## Run it

```bash
pip install -r requirements.txt
uvicorn gated_actions.app:app --reload
```

```bash
# confident support request -> auto-actioned
curl -X POST localhost:8000/intake -H 'content-type: application/json' \
  -d '{"channel":"email","sender":"c@x.com","body":"Dashboard is down, urgent, error on login"}'
# -> {"decision":"auto_approved","confidence":0.85,"intent":"support","auto_actioned":true}

# vague message -> queued
curl -X POST localhost:8000/intake -H 'content-type: application/json' \
  -d '{"channel":"chat","sender":"c@x.com","body":"hi there"}'
# -> {"decision":"queued_for_review","confidence":0.45,"auto_actioned":false}

curl localhost:8000/review                     # see the queue
curl -X POST localhost:8000/review/<id>/approved
curl localhost:8000/audit                      # full decision trail
```

## Tests

```bash
python -m pytest tests/ -q     # 11 tests: gate boundaries, calibration, full flow
```

## Scope

In-memory stores, a mock extractor, no auth — this is a pattern reference,
not a product. The interfaces are the point: swap `MockExtractor` for a real
LLM adapter and `ReviewQueue` for Postgres and nothing else changes.

By [Varun Dwivedi](https://www.upwork.com/freelancers/~01a21ae95c23f6ff2d) —
AI agent & LLM engineering with an enterprise-BI foundation.
