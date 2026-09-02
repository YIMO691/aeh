# AEH Review Projection — CHG-2026-0004

> This file is a human-readable projection only. Machine truth lives in
> verification.yaml / traceability.yaml / approvals.yaml.

- classification: CRITICAL
- overall verdict: READY_WITH_WARNINGS
- state: VERIFY (stop — no merge/push/PR is performed by AEH)

## Verification results

- VER-001 [target_test] verdict=pass (exit 0)
- VER-002 [regression] verdict=pass (exit 0)
- VER-003 [regression] verdict=pass (exit 0)
- VER-004 [integration] verdict=pass (exit 0)

## Warnings
- MERGE_GATE is delegated to the authenticated SCM merge action; no HMAC identity claim is made
- MERGE_GATE approval has no expiry
- CRITICAL MERGE_GATE approved by user

## Traceability
- REQ-001: AC=AC-001-01 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-002: AC=AC-002-01 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-003: AC=AC-003-01,AC-003-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-004: AC=AC-004-01,AC-004-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-005: AC=AC-005-01,AC-005-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-006: AC=AC-006-01,AC-006-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-007: AC=AC-007-01,AC-007-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-008: AC=AC-008-01,AC-008-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-009: AC=AC-009-01,AC-009-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004
- REQ-010: AC=AC-010-01,AC-010-02 TEST=TEST-001 CODE=.github/workflows/regression.yml,CHANGELOG.md,README.md,docs/architecture-current.md,docs/decisions.md,docs/documentation-contract.yaml,docs/engineering-guide.md,docs/integrations/aew.md,docs/m6-3-coordination.md,docs/roadmap-v0.2.md,docs/status.md,schemas/aew-governance-adapter.schema.json,src/aeh/ci.py,src/aeh/integrations/aew.py,src/aeh/runtime/change.py,src/aeh/runtime/coordination.py,tests/contract/fixtures/legal/aew-governance-adapter.ok.json,tests/runtime/test_coordination_readers.py VER=VER-001,VER-002,VER-003,VER-004

## Human approval

AEH records attributed decisions with externally held approval credentials.
HMAC proves configured credential possession, not legal identity or non-repudiation.
Approval can never override a technical failure.
