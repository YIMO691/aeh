# Spec

machine truth in spec.yaml

## REQ-001 [DESIRED] The AEH repository exposes one immutable, hash-bound GitHub assurance workflow and the installed runtime uses the same enforcement policy.
- AC-001-01 (invariant) The source policy and installed runtime policy bind the exact prerelease wheel, the exact workflow digest, the exact check name, and GitHub Actions App 15368.
- AC-001-02 (automated) The committed workflow bytes hash to the configured SHA-256 and contain only the pinned actions and immutable wheel inputs.
