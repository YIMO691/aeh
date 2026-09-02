# Agent Engineering Workspace Integration

> Status: **CURRENT** for the `0.3.0.dev0` source line. AEH owns Change
> Assurance truth; AEW owns workspace coordination. See
> [current architecture](../architecture-current.md) for the complete boundary.

## Purpose

AEH is a Change Assurance system. An Agent Engineering Workspace (AEW) is an
operational environment that may own Project, Task, Run, provider session,
runtime, recovery, and evidence-index state. The integration joins these systems
without creating duplicate mutable truth.

```text
AEW or another workspace             AEH
-------------------------            -----------------------------
Project / Task / Run IDs      --->   external references
workflow invocation           --->   governed Change operations
runtime and provider state           (not copied into AEH)
                              <---   Change phase and gates
                              <---   native assurance verdict
                              <---   artifact/evidence hashes
```

## Commands

### Inspect SCM boundaries

```text
aeh integration inspect <target> [--max-depth N] [--max-directories N]
```

The command recognizes a Git root, SVN working-copy root, or no root SCM. It
also finds nested Git/SVN boundaries within bounded traversal limits. It does
not contact a remote, recurse into repository metadata, compute an unbounded SVN
status, or write to the target.

### Export Change Assurance truth

```text
aeh integration export <change-id> --workdir <target> \
  [--project-id <external-project>] \
  --task-id <external-task> --run-id <external-run>
```

Task and Run IDs are mandatory because their canonical owner is external. The
v2 envelope is derived from one stable Change snapshot and is not stored back
into the governed repository. It adds required coordination provenance:
protocol/state, repository and workspace hashes, nullable lease revision,
accepted truth and receipt digests, and an optional external workspace-ref
hash. It never exports a raw path, repository identifier, token, credential,
or state-root value.

## Truth ownership

| Truth | Canonical owner |
| --- | --- |
| Project/Task/Run lifecycle | AEW or external workspace |
| Provider session/runtime state | provider/runtime owner |
| Repository content | SCM/project |
| AEH Change lifecycle and gates | AEH |
| RED/GREEN/Test Lock/traceability | AEH |
| Native Change Assurance verdict | AEH |
| Portable verdict projection | integration envelope |

## Verdict mapping

| AEH native state | Portable state |
| --- | --- |
| no verification artifact | `NOT_VERIFIED` |
| `MERGE_READY` | `VERIFIED` |
| `READY_WITH_WARNINGS` | `VERIFIED` |
| `BLOCKED` with an explicit failed/rejected result | `FAILED` |
| other `BLOCKED` cases | `INCONCLUSIVE` |

The portable value never replaces the native AEH verdict. In particular,
`INCONCLUSIVE` does not weaken an AEH `BLOCKED` decision.

## Six cross-cutting fields

Every envelope declares:

- Scope — the exact AEH Change;
- Ownership — external operational state, AEH engineering state, SCM source;
- Authority — Change Assurance, not general runtime authority;
- Lifecycle — a derived read-only snapshot;
- Provenance — source artifact hashes and count;
- Cost — bounded local reads, zero writes, zero network.

## Security and privacy

- Artifact and evidence bodies are never included.
- Repository paths in the envelope are relative; the external caller supplies
  its own project identity.
- The evidence walk is bounded to 1,000 files per Change.
- Nested SCM discovery has explicit depth and directory limits.
- Subprocesses use argument arrays with `shell=False`.
- SVN repository URLs are deliberately omitted.
- Activated Changes must have no unresolved operation and must match their last
  accepted truth before and after export; legacy Changes remain
  `NOT_ACTIVATED` without creating a coordination store.

## Non-goals

This integration does not implement an AEW state database, memory service,
provider runtime, sandbox, peer-agent organization, automatic merge, or release.
Those capabilities remain separate owners and may consume this contract through
an adapter.
