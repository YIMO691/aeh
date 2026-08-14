# AEH V0.1.0 Known Limitations

Frozen at release; none of these are hidden. See README §12 for the user-facing list.

1. Human approval = human attestation (actor.id string), not strong identity
   (no OIDC / IAM / signatures / approval TTL). ENF-APPROVAL-001 semantics.
2. Some adapter capabilities are GUIDANCE_ONLY (Codex git_push deny, Claude
   web_access deny, review.human_required_for on both) — reported honestly as
   unsupported_capabilities, never silently dropped or relaxed.
3. Multi-file install is rollback-capable (stage → validate → apply) but NOT a
   repository-wide atomic transaction.
4. Free-form command string execution is a compatibility path (shell=True);
   argv structured execution is preferred. No OS sandbox. RISK-EXEC-001.
5. No repair/recover subsystem.
6. No upgrade system (the architecture reserves the aeh upgrade semantics and a
   manifest field for it; the command itself is not implemented in V0.1).
7. No CI deep integration.
8. No automatic merge / push / PR — AEH stops at MERGE_READY.
9. No multi-agent orchestrator.
10. Manual verification items stay PENDING until the REVIEW phase (no separate
    approval gate for manual checks in V0.1; CD-097).
11. Editable install only (pip install -e .); relocatable wheel with packaged
    data files is post-V0.1.
12. Keyword-based hard escalation is heuristic: it escalates (fail-safe), it
    never silently downgrades.
13. CRITICAL escalation discovered at ground requires the test plan to declare
    integration/contract verification entries (README §8 documents the remedy).