# M5 Security Boundary

> Status: **CURRENT**  
> Source line: `0.3.0.dev0`

M5 strengthens two boundaries: AEH-managed command execution and approval
credentials. The goal is fail-closed, replayable enforcement without claiming
security properties the portable Python runtime cannot provide.

## Constrained process execution

AEH executes test and verification commands through one policy-enforced path:

- structured argv always runs without a shell;
- legacy command strings are parsed into argv and run without a shell;
- shell metacharacters are rejected by default;
- shell execution requires both `shell: true` in the locked test plan and an
  explicit `--allow-shell` flag on the current RED/GREEN/REFACTOR/VERIFY call;
- cwd must resolve inside the target repository;
- the installed policy caps timeouts and filters inherited environment names.

Example of an explicitly declared shell command:

```yaml
verification:
  - id: INTEG-001
    type: integration
    command: python -m unittest && python scripts/check_contract.py
    shell: true
```

It remains blocked unless the operator invokes the relevant command with
`--allow-shell`.

This is a **portable constrained-process boundary**, not a kernel sandbox. It
does not provide filesystem, network, syscall, container, VM, or complete
process-tree isolation. Repository-controlled test code still runs with the OS
permissions of the AEH process.

## Credential-bound approvals

New approval decisions require an external HMAC-SHA256 credential. A key may be
stored at `.aeh/private/approval-keys/<key-id>.key` (already Git-ignored) or
supplied with `--credential-file`.

Generate a random key with an approved local secret-management tool and keep at
least 32 random bytes. Then record an approval:

```bash
aeh change approve CHG-2026-0001 \
  --gate MERGE_GATE --status APPROVED --actor reviewer \
  --key-id release-reviewer
```

For verification on another machine or CI, provision the same secret outside
the repository and bind it explicitly:

```bash
aeh change verify CHG-2026-0001 \
  --approval-key release-reviewer=/secure/path/reviewer.key
```

The credential binds the Change ID, Gate, decision, actor, timestamps, TTL, and
evidence reference. Revocation preserves the original credential and appends a
separately signed revocation credential.

HMAC proves possession of a configured shared secret. It does not prove legal
identity, hardware custody, enterprise IAM, or public-key non-repudiation.
Historical unsigned approvals remain readable, but they cannot unlock M5
protected manual or CRITICAL merge Gates.

## Threat-model summary

M5 blocks accidental or injected shell syntax on the default path, hidden plan
shell enablement, cwd escape, excessive declared timeout, non-allowlisted
environment inheritance, approval payload tampering, wrong-key verification,
and cross-Change/Gate credential replay.

Residual risks include arbitrary behavior by explicitly executed repository
code, authorized shell power, shared-key custody, descendants that outlive a
timed-out parent on some platforms, and all OS/IAM controls outside AEH.

M6 remains separate: remote user-project CI enforcement and bounded multi-agent
concurrency are not delivered by M5.
