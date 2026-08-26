# AEH v0.2.1 Candidate Known Limitations

These limits are part of the candidate's honest acceptance boundary.

1. Product effectiveness remains `NOT_YET_PROVEN`; Phase 2 v1.10 recommended
   `REPOSITION` rather than always-on integration.
2. The Controller checkpoint is only authoritative when its external state
   directory is protected by an OS/filesystem boundary that both the coding
   agent and repository-controlled subprocesses cannot write. AEH does not
   provide that OS sandbox.
3. No remediation model rerun or A01–A08 attack evaluation has been performed.
4. Human approval remains an attestation, not cryptographically strong identity.
5. Some adapter capabilities remain `GUIDANCE_ONLY` and are reported as such.
6. Multi-file transactions are journaled and rollback-capable but are not one
   filesystem-wide atomic transaction.
7. Upgrade remains explicit; there is no network discovery, automatic or
   incremental upgrade, arbitrary historical migration, or multi-version mode.
8. Manual verification has no separate approval gate yet; M4 has not started.
9. CI deep integration into arbitrary user repositories, Web UI, RAG, mutation
   testing, impact analysis, and multi-agent orchestration are not implemented.
10. PyPI publication is not authorized and has not occurred.
