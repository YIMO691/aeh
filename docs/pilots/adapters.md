# Codex / Claude dual-platform verification (V0.1 release evidence)

Fresh fixture repository (minimal-py), full bootstrap, then both adapters
rendered from the same compiled profile.

| Check | Result |
| --- | --- |
| bootstrap | BOOTSTRAP_COMPLETE |
| codex render | RENDERED |
| claude render | RENDERED |
| semantics equal (one profile, no drift) | True |
| codex deny fields | permissions.git_push, permissions.web_access |
| claude deny fields | permissions.git_push, permissions.web_access |
| codex unsupported (honest GUIDANCE_ONLY) | permissions.git_push, review.human_required_for |
| claude unsupported (honest GUIDANCE_ONLY) | permissions.web_access, review.human_required_for |
| AGENTS.md managed section | True |
| CLAUDE.md managed section | True |
| AGENTS.md original content preserved | True |
| CLAUDE.md original content preserved | True |

Additional coverage: tests/adapters/test_adapters.py (16 tests) including
push-deny-not-relaxed, semantic-equivalence-across-adapters, managed-section
idempotence, private-policy-zero-leak, and the release-fix 004 handle-leak
regression test.

Note: a full agent-executed change (Codex/Claude CLI driving the workflow) was
not part of this release gate; adapter-level equivalence and the dogfood/pilot
chains are the machine evidence. No core semantics were changed for platform
compatibility.
