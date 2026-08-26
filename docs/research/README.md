# AEH / AEW Research Narrative

This section explains why AEH and AEW exist, how the ideas evolved, and where
the evidence stops. It is a public-safe synthesis of the project research—not
a dump of internal workspaces, session history, or raw research archives.

## Start here

1. [From Black Box to AEW](01_From_Black_Box_to_AEW.md) — the shortest complete
   account of the intellectual path from model uncertainty to a governed
   engineering workspace.
2. [Research Method and Evidence](02_Research_Method_and_Evidence.md) — how the
   conclusions were reached, challenged, and bounded.
3. [Research Source Map](03_Research_Source_Map.md) — which research phase
   supports which public conclusion, including missing and unfinished work.

For the full AEH engineering model, continue with the
[AEH Engineering Architecture Handbook](../handbook/README.md). For the exact
AEH/AEW ownership contract, see the [AEW integration guide](../integrations/aew.md).

## The thesis in one paragraph

A coding model is a probabilistic, partially opaque component. A Harness makes
it useful by supplying context, tools, policy, runtime and observation. A
Workflow makes the required control flow explicit and recoverable. AEH adds an
independent Change Assurance boundary so that an agent's claim of completion is
not accepted as proof. AEW extends the system around longer-lived Project,
Task, Run, runtime, state, memory and provider concerns. AEH and AEW remain
separate because engineering acceptance truth and operational execution truth
must not become competing mutable copies.

## Publication policy

The original research was produced as snapshot-bound phase packages. Those
packages can contain machine-local paths, internal inventory, unfinished
proposals and operational artifacts. Publishing them verbatim would make the
public repository harder to understand and could turn historical observations
into apparently current facts.

This public series therefore follows four rules:

- preserve the questions, findings, counter-evidence and limitations;
- identify the phase and snapshot scope behind material claims;
- publish conclusions and decision lineage, not machine-private state;
- return to current authoritative sources before claiming present product
  behavior.

The raw phase packages remain research evidence, not public runtime truth.
