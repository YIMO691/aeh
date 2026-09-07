# Design

## Problem

PR #24 added structured Agent-driven classification fields to the canonical
Change schema. The repository's committed self-host runtime snapshot still
comes from revision `8e993ce5a42355dd872fd4eacfcc5474d7429037`, so GitHub assurance validates
the next Change with an older installed schema and fails before replay.

## Bounded solution

1. Add a repository regression that compares the canonical source runtime
   digest, installed runtime digest, and manifest runtime digest. It also proves
   that the installed Change schema accepts the new structured fields.
2. Extend the trusted Upgrade path so an unreleased development version may
   refresh a changed runtime snapshot only when the source revision advances,
   then use that path to refresh `.aeh/runtime` and `.aeh/manifest.yaml` from
   the exact PR #24 merge baseline
   `d167b3ad899159cec809ef1819671b03b3838ffc`.
3. Retain only the resulting runtime/manifest differences; do not alter source
   schema semantics, workflow policy, package version, or GitHub configuration.
4. Apply the already-reviewed Agent-driven documentation alignment and verify
   both contracts together.

## Failure and rollback

Before synchronization, the new regression must fail with
`SELF_HOST_RUNTIME_DRIFT`. Any unexpected Upgrade output, runtime-integrity
failure, or scope expansion blocks the Change. Git reversion of the unmerged
commit and the Upgrade transaction journal provide rollback before merge.
