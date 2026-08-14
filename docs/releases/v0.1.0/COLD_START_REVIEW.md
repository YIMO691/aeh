# AEH V0.1.0 — Cold-start Agent UX Review (R3)

Method: a fresh agent session with NO development history was pointed at the
repository and told only: "这是一个刚 clone 的仓库。请只根据仓库公开文档告诉我如何把
AEH 接入一个现有项目，并说明第一次开发任务应该怎么开始。" The agent was read-only
(repository files only) and had to answer 10 onboarding questions with file citations.

## Results

| # | Question | Answer quality | Source cited |
| --- | --- | --- | --- |
| 1 | What is AEH | Correct (SDD+TDD contract harness for Codex/Claude; LLM/Contract/Validator/Evidence roles) | README §1, docs/architecture.md |
| 2 | Supported agents | Correct (Codex via AGENTS.md, Claude via CLAUDE.md, pure renderers, GUIDANCE_ONLY honest) | README §3, adapters/*/adapter.yaml |
| 3 | Installation | Correct commands (venv + pip install -e . + aeh --help) | README §4, examples/minimal |
| 4 | Bootstrap | Correct (aeh bootstrap ., managed sections, original content preserved, --answers) | README §5/§6, architecture P-12 |
| 5 | Doctor + BLOCKED | Correct (read-only, overall=BLOCKED semantics, example blockages) | README §7, src/aeh/doctor/doctor.py |
| 6 | First change + lifecycle | Correct full 9-step chain, MERGE_READY boundary | README §8, examples/generic-business |
| 7 | Five levels + CRITICAL escalation | Correct (8 hard domains, fail-safe escalation, no silent downgrade) | README §9, core/classifications.yaml |
| 8 | Extension points | Correct (interview yaml, discovery yaml, adapters) | CONTRIBUTING.md |
| 9 | V0.1 limitations | Correct (listed 8+ of the 13 recorded items) | KNOWN_LIMITATIONS.md, README §12 |
| 10 | Honest gaps | 3 findings (below) — none blocked independent onboarding | — |

## Findings and fixes (RELEASE-FIX-007)

1. answers.yaml example was hidden inside tests/runtime/test_verify.py.
   → Fixed: examples/answers.yaml (complete, usable) + README §5 reference.
2. docs/repository-panorama.md (DRAFT v0.2 target shape) could be misread as the
   current tree.
   → Fixed: prominent banner clarifying V0.2 target vs V0.1 reality.
3. "aeh upgrade" tension between architecture (reserved semantics) and
   KNOWN_LIMITATIONS ("no upgrade system").
   → Fixed: explicit note that the semantics/manifest field are reserved but the
   command is not implemented in V0.1.
4. (Transient) scratch files at repo root during the review window.
   → Removed; final tree verified 0 scratch/garbage files.

## Verdict

cold_start:
  repository_understanding: PASS
  quick_start_discoverability: PASS
  bootstrap_understanding: PASS
  first_change_understanding: PASS
  codex_entry: PASS
  claude_entry: PASS
verdict: COLD_START_READY
