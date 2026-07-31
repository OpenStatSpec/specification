# In-Place Transformation Binding 0.1

## Normative decision

This binding applies an OpenStatSpec Transformation Plan 0.1 to one existing
logical dataset and its existing physical wide table on a supported SQL
profile. It is the normative architecture for the SPSS-like frontend. It MUST
NOT publish a derived dataset or create an OpenStatSpec undo/version model.

For every successful apply:

- `dataset_id`, physical schema, and physical table name remain unchanged;
- the number of dataset catalog rows and persistent physical data tables remains
  unchanged;
- `RECODE` uses direct `UPDATE` for an existing target; a new target MAY use
  `ALTER TABLE ... ADD COLUMN` plus `UPDATE` only when the selected engine
  preserves the complete data, schema, metadata, and audit apply in one native
  transaction;
- `VARIABLE LABELS` and `VALUE LABELS` mutate the existing dataset's authoritative
  metadata rows;
- no full-table copy, derived output, snapshot table, rollback table, staging
  dataset, final-candidate table, retirement record, or recovery dataset is
  created; and
- normal completion leaves no temporary physical object.

OpenStatSpec does not version successful data states and does not implement
rollback on any engine. A deployment uses its database's own transaction,
backup, or version-control facilities. On Dolt, history, branching, diff, merge,
and restoration belong exclusively to Dolt.

## Additional controlled Dolt context

Every apply requires an actor. When the active product is Dolt, the caller MUST
also provide the expected active branch and expected `HEAD` commit identity.
Before Dolt mutation the executor MUST verify both and MUST require a clean Dolt
working set so unrelated changes cannot be attributed to the apply. These Dolt
arguments do not block in-place apply on SQLite, PostgreSQL, MySQL, or MariaDB.

The apply MUST remain on the same branch and MUST NOT call `DOLT_COMMIT`, switch
branches, merge, reset, or create a tag. Its successful changes remain in the
Dolt working set. Commit/publish policy is a separate orchestration decision by
the caller. The compact audit records the branch and `HEAD` observed before and
after apply; both commit identities are equal unless an external actor violated
the controlled context, in which case apply fails.

## Atomicity and temporary state

The executor uses only the transaction semantics naturally provided by the
selected database engine. It MUST NOT emulate rollback with a persistent copy,
compensating dataset, snapshot relation, or OpenStatSpec recovery/version layer.
Minimal engine-internal ephemeral state is permitted only within one operation,
must not be published as a dataset, and must have zero residue after normal
completion. Direct `UPDATE`, `ALTER TABLE`, and metadata mutation are preferred.

A plan that creates a target or otherwise changes physical schema MUST be
rejected with `schema_change_not_atomic` before the first mutation unless the
active implementation profile proves that the engine keeps the entire schema,
data, metadata, and compact-audit apply within one native transaction.
MySQL-family implicit-commit DDL, including Dolt when treated as non-atomic,
does not satisfy this rule. This binding never uses a copy, compensating
relation, or recovery layer to make such a schema change appear atomic.

## Compact audit

One `transformation_apply` row MAY record the apply ID, database profile,
dataset/schema/table identity, canonical plan and syntax-source hashes, actor,
timestamps, status, operation count, and optional Dolt branch/commit identity.
For a non-Dolt profile every Dolt-specific field is NULL. For Dolt, the branch
and pre-apply `HEAD` are present; a successful apply also records the equal
post-apply `HEAD`. This is an operation audit, not a dataset version. It MUST
NOT reference a copied data relation or contain row values.

The logical table is defined in
[`../sql/transformation-plan-profile-schema.sql`](../sql/transformation-plan-profile-schema.sql).
Machine-readable invariants are in
[`../conformance/in-place-transformation-0.1.json`](../conformance/in-place-transformation-0.1.json).

## Failure boundary

Before mutation, unknown product/version, branch or HEAD mismatch, or dirty
working set fails closed. During apply, the engine's ordinary transaction error
semantics apply. OpenStatSpec does not create rollback artifacts and does not
claim to restore a prior data state; the caller uses Dolt for inspection and
restoration.

The stable Dolt-context diagnostics are `dolt_branch_mismatch`,
`dolt_head_mismatch`, and `dolt_working_set_dirty`. Each is detected before the
first data, schema, or metadata mutation.
