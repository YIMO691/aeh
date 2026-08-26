# From Black Box to Harness to Workflow to AEH to AEW

## 1. The problem was never merely “can AI write code?”

The project began with a less comfortable question:

> When an AI system says the work is finished, why should an engineer believe
> it?

A model can produce excellent code while remaining a partially opaque,
probabilistic component. It can misunderstand scope, omit a regression, modify
its own test oracle, confuse a tool failure with success, or summarize a result
more confidently than the evidence permits. More prompting can improve the
average answer, but it cannot by itself create an independent acceptance
boundary.

The project's intellectual path is therefore a progressive relocation of
trust:

```text
Black-box model
    ↓ surround execution
Agent Harness
    ↓ externalize deterministic control
Workflow / state machine
    ↓ separate implementation from acceptance
AEH — Change Assurance
    ↓ support long-lived, cross-provider operation
AEW — Agent Engineering Workspace
```

The goal is not to make the model internally infallible. The goal is to make
the engineering system externally inspectable, controllable, recoverable and
verifiable.

## 2. Stage zero — the black box

“Black box” does not mean that nothing can be known about a model. It means the
engineering system cannot rely on a stable, complete explanation of how an
output was produced or assume that the same input always produces the same
decision.

This creates three different notions of success:

```text
Agent success
  “I completed the task.”

Task success
  The requested artifact or behavior appears to exist.

Assurance success
  Independent, trustworthy evidence shows that the artifact satisfies the
  intended requirements without violating protected constraints.
```

These can disagree. A patch may look correct but have no reliable regression
evidence. A test command may return zero without loading the intended tests. A
trajectory may show diligent work without proving the outcome. The first core
invariant follows:

```text
Agent self-report ≠ verification
```

## 3. Stage one — Harness makes the model an engineering participant

A Harness surrounds the model with the machinery required to act in a real
repository:

```text
Intent
  ↓
Context and instructions
  ↓
Agent loop
  ↓
Tools / approvals / policy
  ↓
Runtime / filesystem / network
  ↓
Repository and artifacts
  ↓
Events / results / recovery
```

The Codex and Qwen Code case studies showed why this is a major advance over a
bare chat interface. Hierarchical instructions, progressive Skills, project
trust, protected control paths, sandbox/approval separation, worktree-aware
state and durable events all turn an LLM call into an engineering execution
system.

But Harness is not synonymous with trust. A Harness can contain stale model
assumptions, unsafe defaults, ambiguous state ownership, race conditions or an
incorrect success signal. As Harness capability grows, it inherits classic
distributed-systems and security problems: locks, lifecycle, replay,
containment, resource limits, secrets and reconciliation.

This produces several boundaries:

```text
Harness ≠ Runtime
Worktree isolation ≠ security sandbox
Instruction ≠ enforced policy
Session transcript ≠ authoritative task state
```

Harness makes action possible. It does not, by itself, prove that the action
was correct.

## 4. Stage two — Workflow turns intention into explicit control

Some decisions should remain agentic: exploring a repository, proposing a
design, localizing a defect. Other decisions should not depend on whether the
model remembers a sentence in a prompt:

- required ordering;
- branch and retry rules;
- timeouts;
- approval interrupts;
- protected state transitions;
- recovery and termination;
- aggregation of parallel results.

Those belong in a Workflow or state machine.

```text
Workflow decides:
  when, in what order, under which gate, and what happens on failure.

Agent decides:
  which bounded action is most useful inside the current allowed step.
```

This is not an attempt to eliminate autonomy. It places autonomy inside an
explicit control envelope. It also makes a long-running task recoverable
without treating chat history as the database.

The multi-agent research strengthened this conclusion. Complexity does not
automatically justify more Agents. The preferred decision ladder is:

```text
Deterministic rule?          → code or Workflow
Repeatable procedure?       → Skill
Bounded independent inquiry?→ delegated Agent
Responsibility transfer?    → Handoff
Human authority required?   → durable approval interrupt
```

The safest concurrency default is one canonical writer with bounded,
read-oriented explorers, reviewers and testers. Coordination is a cost that
must earn its place.

## 5. Stage three — AEH separates making the change from accepting it

AEH emerged when Workflow alone was still insufficient. A sequence can be
followed perfectly while the underlying evidence is weak, forged, stale or
attached to the wrong artifact.

AEH is therefore best understood as a vendor-neutral **Change Assurance**
system. It owns the engineering meaning of a governed change:

```text
Ground
  → Specification
  → Test design
  → RED
  → Test Lock
  → GREEN / REFACTOR
  → Verify
  → Approval / Review
```

Its distinctive responsibility is not writing the code. It is maintaining
machine-readable contracts and independently enforcing whether a transition or
verdict is legal.

Important AEH ideas include:

- specification and acceptance criteria before acceptance;
- change-scoped state rather than one global mutable task file;
- RED/GREEN evidence with protected test-oracle integrity;
- traceability from requirement to test, code and verification;
- hashes and provenance instead of trust-me summaries;
- four honest verification outcomes: `VERIFIED`, `FAILED`, `INCONCLUSIVE`,
  `NOT_VERIFIED`;
- human approval that can authorize policy decisions but cannot convert a
  technical failure into success;
- risk-adaptive workflows rather than maximum ceremony for every edit.

AEH deliberately does not become a general Agent loop, memory service,
sandbox fleet, provider session manager or peer-agent organization. Coding
agents are improving quickly; rebuilding their entire Harness inside AEH would
increase coupling and make AEH's core assurance boundary less stable.

## 6. Stage four — AEW handles the long-lived operational system

AEH answers:

> Is this engineering Change acceptably grounded, specified, tested and
> verified?

It does not fully answer:

> How do many projects, tasks, runs, provider sessions, runtimes, worktrees,
> memories, handoffs and recovery operations remain coherent over months?

That is the AEW problem.

AEW is a governed, provider-neutral operational environment around software
engineering work. Its leading model is Run-centric rather than Chat-centric:

```text
Project
  └─ Task
      └─ Run
          ├─ provider session references
          ├─ workflow and ownership state
          ├─ runtime / worktree references
          ├─ interrupts and handoffs
          ├─ artifacts
          ├─ verification attempts
          └─ evidence references
```

AEW research also separates concepts that are often collapsed:

```text
Context  = what the model can use now
State    = where the current work is
Memory   = what may influence future decisions
Evidence = why a claim should be believed
Policy   = what is enforced
```

AEW is not “AEH with more folders.” It is the operational substrate that may
invoke AEH as its engineering-governance provider.

## 7. Why AEH and AEW must not merge

Both systems contain words such as state, workflow, verification and evidence,
which makes a merger seem attractive. It would also create two serious risks:

1. one giant system would accumulate unrelated responsibilities;
2. the same fact could gain two editable owners and silently diverge.

The correct design is explicit truth ownership:

| Truth | Canonical owner |
| --- | --- |
| Repository content and history | SCM / project |
| Project, Task and Run operational lifecycle | AEW or external workspace |
| Provider session execution | provider, referenced by AEW |
| Runtime observed state | runtime provider, reconciled by AEW |
| Engineering Change phases and gates | AEH |
| RED/GREEN/Test Lock/traceability | AEH |
| AEH native assurance verdict | AEH |
| Evidence bodies | original evidence owner |
| Cross-system evidence index | references and hashes, not duplicate truth |
| Reviewed project knowledge | project knowledge owner / SCM |
| Private memory | its scoped memory owner |

The integration contract merged in PR #9 follows this rule: external
Project/Task/Run IDs reference an AEH Change; AEH exports a deterministic,
read-only envelope containing its native state, verdict and artifact hashes.
Neither system silently edits the other's canonical state.

## 8. Six questions every durable object must answer

Cross-case research found that many failures were boundary failures rather than
reasoning failures. A worktree shared the wrong memory; a child inherited
mutable state; a cache reused a verdict for a changed artifact; multiple
writers lacked a merge owner.

Every durable or security-relevant object should therefore answer:

1. **Scope** — where is it valid?
2. **Ownership** — who controls mutation and lifecycle?
3. **Authority** — how strongly may it influence behavior or verdicts?
4. **Lifecycle** — how is it created, versioned, recovered and expired?
5. **Provenance** — where did it come from and why is it trustworthy?
6. **Cost** — what context, compute, storage, coordination and human burden
   does it add?

This is why the project is contract-centric rather than folder-centric or
Agent-persona-centric.

## 9. One concrete end-to-end example

Consider a high-risk bug fix:

```text
Owner intent
  ↓
AEW creates Task and Run; records authority and provider/runtime references
  ↓
Harness gives the coding Agent scoped context, tools and permissions
  ↓
Workflow invokes AEH Change Assurance gates
  ↓
Agent grounds the repository and produces a specification
  ↓
AEH requires a reproducing RED test and locks the test oracle
  ↓
Agent implements the fix; bounded readers/reviewers may assist
  ↓
AEH independently rechecks protected state, regression and traceability
  ↓
AEH emits native verdict and evidence hashes
  ↓
AEW records operational completion and recovery state by reference
  ↓
Human/SCM merge policy decides whether the verified change is integrated
```

No single layer is asked to be everything. The model reasons, the Harness
executes, the Workflow controls, AEH accepts or blocks the Change, AEW preserves
operational continuity, and SCM owns the repository.

## 10. Is all of this always necessary?

No. Governance has a cost.

For a disposable exploration, full Change Assurance may be wasteful. For a
security boundary, migration or difficult-to-verify behavior, accepting an
agent's self-report is irresponsible. The intended rule is proportionality:

```text
Risk
× irreversibility
× blast radius
× verification difficulty
× security sensitivity
  ↓
required workflow, isolation, approval, verification and evidence
```

The system should be judged by real outcomes: defect rate, rework, recovery,
human burden, context cost, verification quality and auditability. If a
capability's coordination or governance cost exceeds its measured benefit, it
should be simplified, deferred or removed.

## 11. The deepest idea

The project is a move from **intelligence-centric engineering** to
**system-centric trust**.

It does not ask users to believe that a newer model will never make a mistake.
It asks whether the surrounding system can expose the mistake, contain its
effects, preserve the evidence, recover the work and refuse an unsupported
claim of success.

That is why the path runs from black box, to Harness, to Workflow, to AEH, and
finally to AEW.
