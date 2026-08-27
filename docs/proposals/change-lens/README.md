# AEH Change Lens Implementation Proposal

> Status: **HANDED OFF TO INDEPENDENT REPOSITORY / NOT IMPLEMENTED**
> Authority: **NON-NORMATIVE**
> Baseline: `main@394f7f644c08ed33e967207cb5ec792ea9d7970b`
> Machine-readable companion: [proposal.yaml](proposal.yaml)

This proposal defines a bounded implementation path for a read-only tool that
explains an AI-assisted code change as an evidence-linked transition from the
old logic path to the new logic path. It does not change AEH runtime contracts,
Gates, current milestone status, or release claims.

The Owner resolved the entry decisions on 2026-08-27 and selected an independent
repository. The canonical bilingual plan now lives at
[YIMO691/aeh-change-lens](https://github.com/YIMO691/aeh-change-lens), with
Chinese as the authoritative language. This document remains the AEH-side
proposal record; implementation still requires a separate explicit start
authorization and is not an AEH roadmap or release claim.

## 0. Owner decision and handoff

- first analyzed language: C#, focused on Unity/gameplay code;
- delivery: independent repository with Python orchestration and a .NET/Roslyn analyzer worker;
- language policy: Chinese launch product/UI; Chinese plan authoritative, English plan retained;
- execution policy: deterministic and offline by default;
- LLM explanation: explicit opt-in only;
- primary users: change authors and reviewers;
- pilot: 10-20 manually annotated Changes;
- current Gate: `PLAN_READY / IMPLEMENTATION_AUTHORIZATION_NOT_GRANTED`.

## 1. Outcome

For one AEH Change, a reviewer must be able to answer five questions without
reading the entire diff:

1. What behavior and code path existed before the change?
2. What behavior and code path exists after the change?
3. Which nodes and relationships were added, removed, moved, or modified?
4. Why was each material change made, and which requirement or evidence
   supports that explanation?
5. Which tests or runtime observations verify the new path, and what remains
   uncertain?

The tool explains an externally recorded decision rationale. It must not claim
to expose, reconstruct, or preserve a model's hidden chain of thought.

## 2. Product boundary

### 2.1 MVP in scope

- one local Git repository;
- one explicit `CHG-*` Change;
- base revision versus worktree or explicit target revision;
- one language adapter selected by the Owner;
- changed symbols plus at most one configurable caller/callee hop;
- function/method calls, key branches, returns/errors, and recognized side
  effects;
- syntax-aware add/delete/update/move mapping;
- links to AEH requirement, acceptance, evidence, test, code, and verification
  IDs;
- source and evidence digest validation with a visible `STALE` state;
- deterministic `explain-bundle.json` generation;
- a local read-only Web view and static HTML export;
- offline analysis by default; optional LLM explanation only behind an explicit
  policy decision.

### 2.2 Explicitly out of scope

- full-repository knowledge graphs;
- hidden chain-of-thought capture;
- automatic approval, Gate mutation, or release decisions;
- modification of `.aeh` normative machine truth;
- multi-agent orchestration;
- arbitrary cross-service reconstruction;
- complete reflection, dynamic dispatch, dependency-injection, generated-code,
  or runtime configuration resolution;
- automatic claims that inferred business behavior is confirmed;
- support for multiple languages in the first implementation increment;
- cloud upload, telemetry, or source-code transmission by default.

Any pull request that introduces an out-of-scope item must first amend this
proposal through the change-control process in section 12.

## 3. Truth and trust model

Change Lens is a projection over existing sources; it is not a new authority.

| Information | Authority | Change Lens treatment |
|---|---|---|
| Git revision and source bytes | Project SCM/worktree | Hash and reference, never rewrite |
| AEH Change state and Gate verdict | AEH runtime artifacts | Read-only projection |
| Requirement/test/code traceability | AEH artifacts | Preserve IDs and source hashes |
| Syntax relationships | Parser output | Mark `STRUCTURAL` |
| Symbol/reference relationships | Compiler or semantic index | Mark `CONFIRMED_STATIC` |
| Runtime path | Captured runtime evidence | Mark `OBSERVED_RUNTIME` |
| AI explanation | Derived narrative | Mark `INFERRED` until supported |

Every displayed node, edge, and explanation must carry provenance and one of:

- `CONFIRMED_STATIC` — compiler/indexer-resolved;
- `OBSERVED_RUNTIME` — present in captured runtime evidence;
- `STRUCTURAL` — directly present in the parsed syntax;
- `INFERRED` — rule or LLM inference;
- `UNKNOWN` — unresolved.

Lower-confidence information must never be rendered with the same visual or
textual certainty as confirmed information. An LLM may summarize evidence but
may not upgrade confidence or invent a source reference.

## 4. Proposed architecture

```text
Git base/target snapshots
        |
        v
Snapshot Resolver -----> source hashes / rename map / stale detection
        |
        v
Language Adapter ------> symbols / syntax / calls / branches / side effects
        |
        v
Semantic Differ -------> old-new node mapping / add-delete-update-move
        |
        +-----------------------------+
        |                             |
        v                             v
AEH Evidence Reader             Optional Runtime Trace Reader
        |                             |
        +--------------+--------------+
                       v
               Evidence Linker
                       |
                       v
              Explain Bundle Builder
                       |
              +--------+--------+
              v                 v
         Local Web View     Static HTML Export
```

Recommended module boundaries:

```text
src/aeh_change_lens/
  snapshot/       read Git objects and worktree state
  languages/      language adapter interface and first implementation
  semantic_diff/  stable node matching and graph delta
  evidence/       read and verify AEH artifacts
  explain/        build evidence-linked explanations
  bundle/         schema, canonical serialization, digest calculation
  server/         local read-only API and static assets
ui/               old-path/new-path interactive view
schemas/          explain bundle and adapter contracts
tests/            unit, golden, adversarial, and end-to-end fixtures
```

The first implementation should live in a separate repository or package. AEH
may later add a thin `aeh explain` integration only after the projection
contract and security boundary are proven stable.

## 5. External techniques to reuse

| Need | Candidate | Decision boundary |
|---|---|---|
| Fast syntax trees | [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) | Recommended MVP parser layer; syntax is not semantic resolution |
| Stable symbols/references | [SCIP](https://github.com/scip-code/scip) | Optional semantic adapter after the first parser slice |
| AST node mapping | [GumTree](https://github.com/GumTreeDiff/gumtree) | Evaluate as an external adapter; review LGPL-3.0 distribution obligations |
| Unified AST/CFG/data-flow model | [Joern CPG](https://docs.joern.io/code-property-graph/) | Borrow the layered graph model; do not require Joern in the MVP |
| Change-focused graph UI | [React Flow](https://reactflow.dev/) | Recommended for the bounded interactive view |
| Large graph algorithms | [Cytoscape.js](https://js.cytoscape.org/) | Reconsider only if the bounded graph exceeds the MVP scale |

The differentiating implementation is not parsing or graph drawing. It is the
evidence-preserving correlation of `old path -> graph delta -> new path` with
AEH `REQ -> AC -> TEST -> CODE -> VER` truth.

## 6. Entry decisions and prerequisites

The Owner resolved the following entry decisions on 2026-08-27:

| ID | Decision | Recommended default | Why it matters |
|---|---|---|---|
| CL-DEC-001 | First supported language | C# for Unity/gameplay code | Fixes parser, compiler/indexer, fixtures, and oracle |
| CL-DEC-002 | Delivery topology | Separate repository; Python orchestration + .NET/Roslyn worker | Prevents experimental UI/analysis dependencies entering AEH's TCB |
| CL-DEC-003 | LLM policy | Offline deterministic core; LLM explanation opt-in | Protects source confidentiality and repeatability |
| CL-DEC-004 | Target user | Change author and code reviewer | Determines graph depth and explanation language |
| CL-DEC-005 | Pilot corpus | 10-20 manually annotated Changes | Required to measure graph correctness and usefulness |
| CL-DEC-006 | Language policy | Chinese launch product/UI; Chinese plan authoritative, English plan retained | Prevents presentation order and translation authority from drifting |

Technical prerequisites:

- Git is available and the base revision is reachable;
- AEH Change artifacts are readable and pass existing integrity checks;
- the selected language parser/indexer can run locally;
- the project supplies representative fixtures, including rename, move,
  branch, error, side-effect, and ambiguous dynamic-call cases;
- an approved local evidence/output directory exists;
- no source or artifacts leave the machine without explicit authorization.

The decision Gate is `PLAN_READY`. Implementation authorization remains
`NOT_GRANTED`; resolving product defaults does not authorize code execution,
source upload, or implementation work.

## 7. Acceptance criteria

### P0 — required for an MVP claim

- **CL-AC-001 Deterministic input binding:** the bundle records base/target
  revisions, every source artifact digest, AEH artifact digests, analyzer
  versions, and configuration. Identical inputs produce byte-identical
  canonical semantic content.
- **CL-AC-002 Stale detection:** any bound source or AEH artifact change makes
  the previous bundle visibly `STALE`; stale output cannot be represented as
  current.
- **CL-AC-003 Old/new separation:** every mapped code node identifies its old
  location, new location, and change kind without mixing revisions.
- **CL-AC-004 Provenance:** every displayed material node, edge, rationale, and
  verification result has a provenance source and confidence class.
- **CL-AC-005 No false authority:** the tool cannot write AEH Gate state,
  approvals, runtime contracts, manifests, profiles, or normative Change truth.
- **CL-AC-006 No chain-of-thought claim:** generated explanation is labeled as
  an evidence-linked rationale, never as hidden model reasoning.
- **CL-AC-007 Bounded graph:** the default graph contains only changed symbols,
  the connecting path, and the configured local neighborhood; full-repository
  expansion is not automatic.
- **CL-AC-008 Evidence linkage:** each material modified node links to at least
  one requirement/evidence/test reference or is visibly marked `UNLINKED`.
- **CL-AC-009 Fail closed:** unresolved revisions, missing artifacts, parser
  failures, schema violations, path escapes, and unsupported file kinds produce
  an explicit blocked/partial result rather than a complete-looking graph.
- **CL-AC-010 Reviewer outcome:** on the approved pilot corpus, reviewers can
  identify the intended behavior change, primary changed symbols, supporting
  tests, and known uncertainty from the report alone.

### P1 — required before broader adoption

- **CL-AC-011 Semantic resolution:** compiler/SCIP-backed symbol references are
  available for the selected language.
- **CL-AC-012 Runtime overlay:** approved runtime traces can be shown separately
  from static and inferred paths.
- **CL-AC-013 Accessibility:** core comparison and evidence details are usable
  with keyboard navigation and do not rely on color alone.
- **CL-AC-014 Performance budget:** a representative bounded Change produces a
  first useful report within the Owner-approved local budget.
- **CL-AC-015 Export integrity:** static export preserves bundle digest,
  provenance, uncertainty, and source revision labels.

## 8. Invariants

- **CL-INV-001:** projections never become AEH normative truth.
- **CL-INV-002:** old and new revisions are always represented separately.
- **CL-INV-003:** confidence can be lowered by later evidence but never raised
  without a stronger source.
- **CL-INV-004:** absence of analysis is not evidence that no relationship
  exists.
- **CL-INV-005:** LLM output cannot create confirmed nodes, edges, test results,
  or approval state.
- **CL-INV-006:** a displayed source location is bound to content digest and
  revision.
- **CL-INV-007:** analysis never executes project code in the deterministic
  static MVP path.
- **CL-INV-008:** runtime observation is opt-in, sandboxed by an authorized
  external execution path, and visually distinct.
- **CL-INV-009:** local file reads reject path escape, symlink/reparse escape,
  and unsupported filesystem objects.
- **CL-INV-010:** generated reports contain no source body beyond the explicit
  local/export disclosure policy.

## 9. Work packages and Gates

Work packages are sequential unless an approved revision changes the dependency
graph. No package is complete based only on code existence.

### CL-WP-00 — Contract freeze and pilot fixtures

Outputs:

- Owner decisions `CL-DEC-001` through `CL-DEC-005`;
- v1 Explain Bundle Schema;
- language adapter interface;
- manually annotated pilot and adversarial fixtures;
- explicit privacy and export policy.

Exit Gate `CL-GATE-00`:

- all P0 criteria have planned checks and observable oracles;
- all open decisions are resolved;
- fixtures cover add/delete/update/move, rename, branch, error, side effect,
  unresolved dynamic call, and stale input;
- no runtime or UI implementation has begun before contract review.

### CL-WP-01 — Snapshot resolver

Outputs:

- Git object/worktree reader without checkout;
- base/target/file digest manifest;
- rename and binary/unsupported-file classification;
- path-boundary and stale-input checks.

Exit Gate `CL-GATE-01`:

- `CL-AC-001`, `CL-AC-002`, `CL-AC-003`, `CL-AC-009` pass for snapshot
  fixtures;
- repository state is unchanged after analysis;
- path escape and symlink/reparse adversarial cases fail closed.

### CL-WP-02 — First language adapter

Outputs:

- functions/classes and stable fallback node IDs;
- calls, branches, returns/errors, and configured side-effect recognizers;
- parser limitations and confidence mapping.

Exit Gate `CL-GATE-02`:

- golden fixtures reproduce the annotated structural graph;
- syntax-error input returns a partial result with limitations;
- dynamic or unresolved calls are not reported as confirmed.

### CL-WP-03 — Semantic differ

Outputs:

- old/new node matching;
- `ADDED`, `REMOVED`, `UPDATED`, `MOVED`, `UNCHANGED_CONTEXT` actions;
- graph delta and ambiguity records.

Exit Gate `CL-GATE-03`:

- mapping quality is measured against the pilot corpus;
- rename and move cases do not degrade into misleading delete/add output when
  the selected analyzer can establish identity;
- ambiguous mappings remain explicit.

### CL-WP-04 — AEH evidence linker and bundle

Outputs:

- read-only AEH artifact adapter;
- `REQ/AC/EV/TEST/CODE/VER` linkage;
- canonical Explain Bundle serialization and schema validation;
- source and artifact digest verification.

Exit Gate `CL-GATE-04`:

- `CL-AC-001` through `CL-AC-009` pass;
- mutation attempts against protected AEH files are absent or blocked;
- missing and forged references fail closed;
- deterministic bundle generation passes repeated-build comparison.

### CL-WP-05 — Evidence-constrained explanation

Outputs:

- deterministic template explanation;
- optional schema-constrained LLM explanation adapter;
- citation validator and unsupported-claim detection;
- alternatives/unknowns representation.

Exit Gate `CL-GATE-05`:

- every material statement resolves to a source reference or is marked
  `INFERRED`;
- prompt injection in source comments or AEH narrative cannot change authority,
  scope, or confidence;
- disabling the LLM retains a complete deterministic report.

### CL-WP-06 — Local viewer and export

Outputs:

- synchronized old-path/new-path lanes;
- change, provenance, confidence, requirement, and test overlays;
- source/evidence detail view;
- static HTML export.

Exit Gate `CL-GATE-06`:

- `CL-AC-010`, `CL-AC-013`, and `CL-AC-015` pass;
- added/removed/updated/moved/uncertain states are understandable without color;
- the default view remains bounded on the largest pilot Change;
- no browser network request occurs in offline mode.

### CL-WP-07 — Pilot and adoption decision

Outputs:

- accuracy results for node/edge/mapping/provenance;
- reviewer task-success and time measurements;
- performance, failure, and privacy results;
- `CONTINUE`, `REPOSITION`, or `STOP` recommendation.

Exit Gate `CL-GATE-07`:

- all P0 criteria are evidenced;
- failure and uncertainty rates are reported, not hidden in an average;
- the Owner explicitly decides whether to integrate with AEH, continue as a
  separate project, reposition, or stop.

## 10. Traceability matrix

| Acceptance | Work package | Required evidence |
|---|---|---|
| CL-AC-001 | WP-01, WP-04 | repeated bundle digest test |
| CL-AC-002 | WP-01, WP-04 | source/artifact mutation tests |
| CL-AC-003 | WP-01, WP-03 | revision-separated golden mapping |
| CL-AC-004 | WP-02, WP-04, WP-05 | provenance completeness report |
| CL-AC-005 | WP-04 | protected-file before/after manifest |
| CL-AC-006 | WP-05, WP-06 | terminology and rendered-output check |
| CL-AC-007 | WP-02, WP-06 | graph-boundary test |
| CL-AC-008 | WP-04 | linkage coverage report |
| CL-AC-009 | WP-01 through WP-05 | adversarial blocked/partial cases |
| CL-AC-010 | WP-06, WP-07 | reviewer outcome study |
| CL-AC-011 | Post-MVP | semantic index integration tests |
| CL-AC-012 | Post-MVP | static/runtime separation test |
| CL-AC-013 | WP-06 | keyboard and non-color checks |
| CL-AC-014 | WP-07 | benchmark report |
| CL-AC-015 | WP-06 | export equivalence and digest test |

## 11. Risk register

| Risk | Failure mode | Required mitigation |
|---|---|---|
| CL-RISK-001 False certainty | Static or AI-inferred edge appears factual | Per-edge provenance/confidence and uncertainty-first rendering |
| CL-RISK-002 Graph explosion | Whole-repository graph becomes unusable | Change-scoped slice, hop/depth budgets, collapsed context |
| CL-RISK-003 Stale explanation | Source changes after analysis | Digest binding and mandatory `STALE` verdict |
| CL-RISK-004 TCB expansion | Viewer can mutate AEH truth | Separate process/package, read-only adapter, protected manifest check |
| CL-RISK-005 Source disclosure | UI/export sends or embeds sensitive code | Offline default, explicit export policy, bounded snippets |
| CL-RISK-006 Prompt injection | Comments/evidence instruct the explainer | Treat all repository text as data; schema-constrained output and reference validation |
| CL-RISK-007 Analyzer mismatch | Unsupported language feature produces wrong path | Adapter capability matrix and explicit partial/unknown result |
| CL-RISK-008 License conflict | Reused analyzer constrains distribution | Dependency/license review at WP-00; isolate copyleft tools behind adapters |
| CL-RISK-009 Product non-value | Correct graph does not help reviewers | Measured pilot with continue/reposition/stop Gate |

## 12. Anti-drift change control

Every implementation pull request must:

1. name exactly one primary `CL-WP-*` work package;
2. list the `CL-AC-*`, `CL-INV-*`, and `CL-RISK-*` IDs it touches;
3. include tests and raw evidence for the package exit Gate;
4. state whether scope, trust boundary, external data flow, dependencies, or
   confidence semantics changed;
5. leave unrelated work for a separate proposal or pull request;
6. update `proposal.yaml` and this document together if a governed field changes;
7. receive an explicit Owner decision before adding an out-of-scope capability;
8. never describe a package as complete until its exit Gate evidence passes.

A proposal change requires a decision record when it alters any of:

- goal or target user;
- in-scope/out-of-scope boundary;
- authority or mutation boundary;
- confidence semantics;
- P0 acceptance criteria or invariants;
- work-package dependency order;
- offline/privacy default;
- first language or delivery topology.

Suggested pull-request declaration:

```text
Primary work package: CL-WP-02
Acceptance criteria: CL-AC-004, CL-AC-007, CL-AC-009
Invariants: CL-INV-002, CL-INV-004, CL-INV-007
Risks: CL-RISK-001, CL-RISK-007
Scope change: no
Gate evidence: <immutable paths or CI run>
```

## 13. Verification plan

Minimum test layers:

- schema and contract tests for legal/illegal Explain Bundles;
- golden parser graphs for the selected language;
- semantic diff fixtures for add/delete/update/move/rename;
- adversarial fixtures for path escape, symlink/reparse escape, malformed YAML,
  forged IDs, stale hashes, prompt injection, binary files, and syntax errors;
- determinism tests with fixed inputs and epochs;
- protected-file before/after manifests;
- UI tests for synchronized selection, uncertainty display, keyboard operation,
  offline behavior, and export equivalence;
- pilot review tasks with manually established ground truth.

Static inspection alone may support a failure finding but is not sufficient for
a release-ready claim. A future implementation self-check must capture an exact
source snapshot, explicit execution authorization, raw evidence, and an
independently recomputed Gate report.

## 14. Success and stop conditions

Success is not "a graph can be rendered." The MVP succeeds only if:

- the graph is demonstrably bound to the correct old and new revisions;
- material changes and evidence links are accurate enough for the approved
  pilot threshold;
- uncertainty is visible and understood;
- reviewers complete the five outcome questions more reliably or faster than
  with the normal diff and AEH artifacts alone;
- the tool remains read-only with respect to AEH truth.

The Owner should stop or reposition the project when:

- semantic ambiguity makes the primary target language misleading;
- reviewers prefer the normal diff and evidence files;
- analysis cost exceeds the accepted review benefit;
- maintaining language adapters dominates product work;
- the UI encourages users to trust inferred paths as facts.

## 15. Proposed command surface

The command names are illustrative and do not change the current AEH CLI:

```text
aeh-change-lens analyze <repo> --change CHG-2026-0001
aeh-change-lens view <explain-bundle.json>
aeh-change-lens export <explain-bundle.json> --output report.html
```

Possible later AEH integration, subject to `CL-GATE-07`:

```text
aeh explain CHG-2026-0001 --serve
aeh explain CHG-2026-0001 --export report.html
```

No current AEH documentation or CLI should advertise these commands as
available until implementation, verification, and an explicit release decision
are complete.
