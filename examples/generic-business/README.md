# Example: generic business (order submission)

A neutral business fixture exercising the full five-level workflow.
The exact runs live under tests/fixtures/tdd-neutral* and the pilot records in
docs/pilots/ (PILOT-A Lightweight, PILOT-B Standard, PILOT-D Explore) plus the
CRITICAL path on tests/fixtures/tdd-repo (PILOT-C).

    aeh change new "order duplicate submit side effect" --level STANDARD
    aeh change ground CHG-2026-0001
    aeh change spec CHG-2026-0001 --reqs reqs.yaml
    aeh change test-design CHG-2026-0001 --plan plan.yaml --test-src ./tests
    aeh change red CHG-2026-0001
    # agent fixes src/order.py
    aeh change green CHG-2026-0001 --scope scope.yaml
    aeh change verify CHG-2026-0001

Expected final verdict: MERGE_READY (state VERIFY). AEH stops there — merge,
push and release remain external systems.

Note: a repository containing hard-escalation domain keywords (奖励/领取/money…)
escalates to CRITICAL at grounding — that is fail-safe by design. CRITICAL then
requires a declared integration/contract verification entry in the test plan and
human MERGE_GATE approval (aeh change approve).
