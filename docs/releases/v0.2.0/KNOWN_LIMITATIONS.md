# AEH v0.2.0 Known Limitations

These limits are accepted for the v0.2.0 release candidate and are not claims
of product effectiveness.

1. Product effectiveness remains `NOT_YET_PROVEN`; the Phase 2 / 72-run pilot
   is not authorized.
2. Human approval is an attestation, not cryptographically strong identity.
3. Some adapter capabilities remain `GUIDANCE_ONLY`; AEH reports them rather
   than presenting them as runtime enforcement.
4. Multi-file transactions are journaled, backup-backed, drift-protected, and
   rollback-capable, but are not one repository-wide atomic filesystem action.
5. Upgrade is explicit and supports an integrity-valid v0.1.0 runtime snapshot;
   there is no automatic/network discovery, incremental patching, arbitrary
   historical migration, or multi-version coexistence.
6. Repair will not cross an upgrade/version-integrity boundary and blocks when
   the current package cannot prove the expected source authority.
7. Manual verification items remain pending until REVIEW; a separate manual
   approval gate is planned for a later milestone.
8. CI deep integration into arbitrary user repositories, automatic merge/push,
   Web UI, RAG, mutation testing, impact analysis, and multi-agent orchestration
   are not implemented.
9. Keyword-based classification hints are conservative heuristics: they may
   escalate, but do not silently downgrade risk.
10. The test suite emits known file-handle `ResourceWarning` messages in test
    code. They did not cause a functional, deterministic-build, or CI failure
    and are tracked as P2 engineering debt.
