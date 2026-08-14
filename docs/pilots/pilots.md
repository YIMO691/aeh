# Pilot Matrix (V0.1 release evidence)

All pilots ran on fresh fixture targets with the installed CLI chain
(python -m aeh.cli, PYTHONPATH=src). Nothing was faked; every gate was real.

| Pilot | Classification | Overall verdict | Final state | CLI steps | Retries | Human confirmations | Blockages | Wall time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PILOT-A | LIGHTWEIGHT | MERGE_READY | VERIFY | 8 | 0 | 0 | 0 | 7.2s |
| PILOT-B | STANDARD | MERGE_READY | VERIFY | 8 | 0 | 0 | 0 | 6.4s |
| PILOT-C | CRITICAL | READY_WITH_WARNINGS | VERIFY | 9 | 0 | 1 | 0 | 6.7s |
| PILOT-D | EXPLORE | n/a (EXPLORE) | INTAKE | 3 | 0 | 0 | 0 | s |

## Observations

- **PILOT-A (Lightweight Bug)**: full chain completed without a single human
  confirmation and without blockages — light changes stay light (8 CLI steps, 7.2s).
- **PILOT-B (Standard Feature)**: same shape plus the standard gates; MERGE_READY
  with zero retries (8 steps, 6.4s).
- **PILOT-C (Critical)**: hard escalation to CRITICAL, declared integration
  verification, one human confirmation (MERGE_GATE attestation) →
  VERIFY_COMPLETE / READY_WITH_WARNINGS (9 steps, 6.7s).
- **PILOT-D (Explore)**: workflow phases are HYPOTHESIS/EXPERIMENT/EVIDENCE/
  DECISION with terminal options DISCARD/PROMOTE_TO_STANDARD/PROMOTE_TO_CRITICAL;
  tdd_forced = false — AEH does not force exploration through TDD.
- No scope violations, no regressions observed in any pilot.
- Subjective burden: low for scripted driving; a human following the same chain
  interacts mainly at change new, plan/scope manifest authoring, and (CRITICAL)
  approval. See README §8 (First Change) for the exact commands.