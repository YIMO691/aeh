# AEH Review Projection — CHG-2026-0008

> This file is a human-readable projection only. Machine truth lives in
> verification.yaml / traceability.yaml / approvals.yaml.

- classification: CRITICAL
- overall verdict: READY_WITH_WARNINGS
- state: VERIFY (stop — no merge/push/PR is performed by AEH)

## Verification results

- VER-001 [target_test] verdict=pass (exit 0)
- VER-002 [regression] verdict=pass (exit 0)
- VER-003 [regression] verdict=pass (exit 0)
- VER-004 [contract] verdict=pass (exit 0)

## Warnings
- verified credential key_id=chg-2026-0008-pr24-merge-20260906-01
- CRITICAL MERGE_GATE approved by user

## Traceability
- REQ-001: AC=AC-001-01 TEST= CODE= VER=VER-002,VER-003
- REQ-002: AC=AC-002-01 TEST= CODE= VER=VER-002,VER-003
- REQ-003: AC=AC-003-01,AC-003-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,README.md,README.zh-CN.md,adapters/codex/AGENTS.template.md,docs/codex-usage.md,schemas/authority-envelope.schema.json,schemas/change.schema.json,src/aeh/cli.py,src/aeh/runtime/agent_flow.py,src/aeh/runtime/change.py,src/aeh/runtime/classify.py,src/aeh/runtime/grounding.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-004: AC=AC-004-01,AC-004-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,README.md,README.zh-CN.md,adapters/codex/AGENTS.template.md,docs/codex-usage.md,schemas/authority-envelope.schema.json,schemas/change.schema.json,src/aeh/cli.py,src/aeh/runtime/agent_flow.py,src/aeh/runtime/change.py,src/aeh/runtime/classify.py,src/aeh/runtime/grounding.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-005: AC=AC-005-01,AC-005-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,README.md,README.zh-CN.md,adapters/codex/AGENTS.template.md,docs/codex-usage.md,schemas/authority-envelope.schema.json,schemas/change.schema.json,src/aeh/cli.py,src/aeh/runtime/agent_flow.py,src/aeh/runtime/change.py,src/aeh/runtime/classify.py,src/aeh/runtime/grounding.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-006: AC=AC-006-01,AC-006-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,README.md,README.zh-CN.md,adapters/codex/AGENTS.template.md,docs/codex-usage.md,schemas/authority-envelope.schema.json,schemas/change.schema.json,src/aeh/cli.py,src/aeh/runtime/agent_flow.py,src/aeh/runtime/change.py,src/aeh/runtime/classify.py,src/aeh/runtime/grounding.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-007: AC=AC-007-01,AC-007-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,README.md,README.zh-CN.md,adapters/codex/AGENTS.template.md,docs/codex-usage.md,schemas/authority-envelope.schema.json,schemas/change.schema.json,src/aeh/cli.py,src/aeh/runtime/agent_flow.py,src/aeh/runtime/change.py,src/aeh/runtime/classify.py,src/aeh/runtime/grounding.py VER=VER-001,VER-002,VER-003,VER-004

## Human approval

AEH records attributed decisions with externally held approval credentials.
HMAC proves configured credential possession, not legal identity or non-repudiation.
Approval can never override a technical failure.
