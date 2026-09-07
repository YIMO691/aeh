# Decisions

- Synchronize the full canonical runtime snapshot through the trusted Upgrade
  path rather than editing `.aeh/runtime/schemas/change.schema.json` or the
  manifest by hand.
- Permit same-development-version refresh only when the runtime digest changes
  and the source revision advances; preserve collision blocks for final
  releases, identical revisions, downgrades, and source-integrity failures.
- Keep source version `0.3.0.dev0`: this is self-host installation-state repair,
  not a package release or a new published version.
- Add one focused regression because the prior suite verified installed-runtime
  integrity but did not compare the repository's installed snapshot with its
  canonical source contracts.
- Keep SCM administration, bypass, tag, Release, PyPI, and source schema
  semantics outside this Change.
