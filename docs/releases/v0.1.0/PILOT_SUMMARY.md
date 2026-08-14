# AEH V0.1.0 Pilot Summary

Machine records: docs/pilots/_pilot_results.json, _adapter_results.json,
_regression_results.json. Narrative: docs/pilots/{dogfood,pilots,adapters}.md.

| Pilot | Classification | Verdict | Final state | CLI steps | Human confirmations | Blockages |
| --- | --- | --- | --- | --- | --- | --- |
| PILOT-A Lightweight | LIGHTWEIGHT | MERGE_READY | VERIFY | 8 | 0 | 0 |
| PILOT-B Standard | STANDARD | MERGE_READY | VERIFY | 8 | 0 | 0 |
| PILOT-C Critical | CRITICAL (hard escalation) | READY_WITH_WARNINGS | VERIFY | 9 | 1 | 0 |
| PILOT-D Explore | EXPLORE | HYPOTHESIS→EXPERIMENT→EVIDENCE→DECISION | INTAKE | 3 | 0 | 0 |

Dogfood: CHG-2026-0001 on the AEH repository itself — template file-handle leak
fix; STANDARD → CRITICAL escalation; RED/GREEN/REFACTOR/VERIFY + human MERGE_GATE
attestation → VERIFY_COMPLETE / READY_WITH_WARNINGS.

Adapters: same profile → Codex RENDERED, Claude RENDERED, semantics equal,
deny fields identical, GUIDANCE_ONLY reported honestly, original file content
preserved, managed sections idempotent.
