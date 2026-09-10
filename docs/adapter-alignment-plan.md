# Reference-adapter alignment plan

## Scope and release boundary

Align Python and PHP with the optional SPSS Syntax Frontend 0.3 already
published in specification `v0.5.0`, pinned at
`864e84479f554b8ee250ffed44c4dfb963750d4a`. This is implementation work, not a
new normative profile or a claim of full SPSS compatibility.

Deliver the three blocks below in dependency order. Each has its own reviewed
pull request and local/CI evidence. Merge and package publication are separate
steps: Python `0.8.1` and PHP `0.7.1` do not gain these changes retroactively.
The merged PHP `0.7.2` preparation is not proof of registry publication.
Do not move published tags or silently rewrite saved plans and audit history.

## Block 1 — Separate Python extension identities

[Python PR #31](https://github.com/OpenStatSpec/python/pull/31).

- Emit `openstatspec-python-schema-change-plan-v0.1` and
  `openstatspec-python-schema-change-spss-v0.1` for Python's existing
  create/delete-variable extension; retain public constant names.
- Continue accepting the legacy Python plan identifier
  `openstatspec-transformation-plan-v0.3` with its exact canonical bytes,
  hash and operation semantics. Legacy acceptance is not official conformance.
- Do not reinterpret old frontend audit identifiers as official Frontend 0.3.
- Preserve official Plan 0.1/0.2 schema-operation rejection, dataset/table
  identity, native atomicity, and caller-owned Dolt history.
- Document reader upgrade order: older adapters do not recognize newly emitted
  Python-owned identifiers. No automatic stored-plan or catalog migration.

Gate: compatibility/hash and in-place tests, full Python service matrix,
read-only review, and merge before block 2. Implementation is in PR #31;
publication remains pending.

## Block 2 — Official Frontend 0.3 in Python

[Python PR #32](https://github.com/OpenStatSpec/python/pull/32), stacked on #31.

- Keep the existing default API behavior. Add explicit official selection via
  the exact `openstatspec-spss-syntax-frontend-v0.3` request contract and the
  live-apply frontend selector.
- Validate real request fields and types before compilation; do not establish
  conformance merely by changing a test's contract string.
- Support comments, dictionary-order `TO` lists, grouped supported commands,
  `NE`/`<>`/`~=`, recursive `NOT`, finite open recode ranges, and ordered
  `ADD VALUE LABELS` state.
- Emit only exact Plan 0.1/0.2 objects in official mode; reject Python-owned
  schema operations there. Preserve source hashes independently of plan hashes.
- Merge additive labels from live metadata under the dataset lock. Prevent
  stale pre-lock snapshots on MySQL/MariaDB without changing Dolt policy.

Gate: all 35 declared and 90 effective cases, exact inherited plans/hashes,
strict-input regressions, native in-place evidence, full service CI including
MySQL/MariaDB interleaved label updates, and read-only review.

## Block 3 — Official Frontend 0.3 in PHP

[PHP PR #16](https://github.com/OpenStatSpec/php/pull/16).

- Accept the exact official request contract explicitly; retain the existing
  Frontend 0.2 default and reuse the existing parser/binder and executor.
- Implement the same official syntax, typed metadata ordering, source hashing,
  canonical Plan 0.1/0.2 lowering, and fail-closed boundaries as Python.
- Keep the pure compiler's request-schema boundary explicit: additive labels
  merge against labels supplied in that schema; callers must provide current
  metadata. This is not a new live-database schema discovery API.
- Keep codec, database support, specification pin and Dolt commit ownership
  unchanged. Do not fold catalog refactoring into this block.

Gate: all 90 effective cases, request/grammar regressions, native SQLite
in-place evidence, `composer check`, full PHP service matrix and read-only
review. Compare both adapters' canonical results, not their internal classes.

## Shared interpretation and invariants

Both implementations use comparison evaluation before `NOT`, then `AND`, then
`OR`; parentheses override grouping. Tests make this interpretation explicit.
Negation preserves UNKNOWN and flattens same-operator boolean chains without
reordering operands. No additional expression operations or SQL binding version
are introduced.

Successful in-place applies preserve dataset and physical-table identity and
case count/order. No copied dataset, staging/output table, snapshot, or hidden
recovery version is introduced. Native transaction rollback is allowed; Dolt
remains the only persistent dataset history/versioning layer.

## Completion checklist

- [ ] Merge Python #31, then #32; retain final-commit CI evidence after any merge
  or follow-up edits rather than relying only on earlier branch runs.
- [ ] Merge PHP #16 after its final-commit CI and review gates.
- [ ] Update the roadmap's pending adapter claims with merged evidence. PR
  implementation is not a published-package support claim.
- [ ] Select package versions and perform each adapter's release checklist,
  including clean registry installation. Keep prepared PHP 0.7.2 release notes
  distinct from these new Unreleased features until release scope is selected.

Out of scope: new arithmetic/date/string profiles, case/group/cross-dataset
operations, MSSQL, SAS/Stata, unrelated optimization, and automatic publication.
