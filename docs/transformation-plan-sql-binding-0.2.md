# In-Place Transformation Binding 0.2

## Status

Status: release candidate for the planned OpenStatSpec `v0.3.0` release. This profile is not a published stable specification until a `v0.3.0` tag targets its exact commit.

## Normative decision

This binding extends In-Place Transformation Binding 0.1 for Transformation
Plan 0.2. It preserves one logical dataset, one physical wide table, dataset
identity, physical table identity, case order, and case count. It creates no
derived dataset, persistent copy, snapshot, OpenStatSpec rollback layer, or
automatic database commit.

Existing-target `assign` compiles to a direct all-row `UPDATE`.
`conditional_assign` compiles to a direct `UPDATE ... WHERE predicate`;
only SQL TRUE rows change. Metadata operations update only their normative
catalog fields. `execute` compiles to no SQL statement.

## Target creation by SQL profile

SQLite and PostgreSQL MAY execute `target_mode=create` only where the adapter
has test evidence that schema, data, catalogs, and compact audit are one native
transaction.

MySQL, MariaDB, and Dolt MUST reject `target_mode=create` before mutation with
`schema_change_not_atomic`. Version 0.2 does not claim atomic create-target
apply on these profiles and MUST NOT use a copied table or compensating
recovery artifact to simulate it.

A caller that needs a new target on MySQL, MariaDB, or Dolt performs a separate,
explicit, versioned provisioning action before the transformation apply. That
action MUST create both:

- one nullable numeric physical column in the existing wide table; and
- one matching normative catalog variable with the same physical binding,
  unique variable identity, and next ordinal.

Provisioning is not a transformation apply and MUST NOT be hidden inside one.
It must leave no uncataloged physical column or catalog-only variable. Before a
later apply, the target resolves as an existing numeric variable, so
`COMPUTE target = ...` lowers to `assign target_mode=replace`. The apply then
contains only DML, metadata changes, and compact audit.

For Dolt, the provisioning action is committed separately by the caller. The
subsequent transformation apply begins from that clean committed HEAD and uses
that exact commit as `expected_head`. OpenStatSpec never calls `DOLT_COMMIT`
for either action.

## Controlled Dolt context

Every apply requires a non-empty actor. Dolt additionally requires
`expected_branch`, `expected_head`, and a clean working set. Branch, HEAD,
and cleanliness are checked before mutation. Branch and HEAD are checked again
before successful completion. Stable diagnostics are
`dolt_context_required`, `dolt_branch_mismatch`, `dolt_head_mismatch`,
`dolt_working_set_dirty`, and `dolt_context_changed`.

The apply remains on the same branch and MUST NOT commit, switch, merge, reset,
tag, or create a persistent recovery object. A successful apply leaves one
inspectable Dolt working-set diff. The audit's before and after HEAD identities
are equal.

## Atomicity and failure

All plan operations, normative and compatibility metadata changes, and the one
compact audit row belong to one public apply boundary. For an existing target,
the adapter uses the engine's native transaction semantics. A failure leaves
data, metadata, and audit unchanged.

Capability and target checks happen before mutation. A profile that cannot
provide the required boundary fails closed. Pre-existing unrelated state is
never treated as apply-owned cleanup state.

The compact audit and forbidden-artifact requirements from Binding 0.1 are
unchanged. It records exact plan/source hashes and operation count, not row
values or copied state.

## Audit schema compatibility

The versioned `sql/transformation-plan-profile-schema.sql` DDL accepts both the
0.1 and 0.2 in-place binding contract identifiers in the same logical
`transformation_apply` table. Before the first 0.2 apply, an installation whose
0.1 table still has the single-contract check MUST migrate that check using its
database profile's transactional DDL procedure where available. The migration
preserves every existing compact audit row and logical audit-table identity.

SQLite, whose `ALTER TABLE` cannot drop the existing table-level check, MUST
perform the standard create/copy/drop/rename table rebuild inside one native
transaction. The replacement table is strictly ephemeral migration state: it
must use the versioned DDL, receive only the existing compact audit rows, and be
renamed to `transformation_apply` before commit. After successful migration
there MUST be exactly one persistent audit table, with no dataset, data-table
copy, snapshot, rollback artifact, or recovery-version layer added. A failure
rolls back the entire rebuild. This schema migration is completed before an
apply and is not part of the transformation apply boundary.

Machine-readable binding cases are in
[`../conformance/in-place-transformation-0.2.json`](../conformance/in-place-transformation-0.2.json).
