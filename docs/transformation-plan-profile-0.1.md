# OpenStatSpec Transformation Plan Profile 0.1

## Status and scope

This optional profile defines a canonical, dialect-neutral transformation plan.
Its contract identifier is `openstatspec-transformation-plan-v0.1`. The key
words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are
normative.

The plan is an intermediate representation, not an analysis language, SQL
dialect, parser source tree, scheduler, or dataset-version store. A frontend
MAY produce it and an executor MAY compile it, but neither frontend syntax nor
generated SQL is the canonical expression of its semantics. The JSON instance
MUST conform to
[`../transformation/plan-0.1.schema.json`](../transformation/plan-0.1.schema.json).

## Canonical form and identity

A plan contains exactly `contract`, `input_alias`, and a non-empty ordered
`operations` array. It is serialized using the restricted RFC 8785 domain and
SHA-256 rules from SQL Transformation Workflow 0.1. `plan_hash` is lowercase
SHA-256 of the UTF-8 RFC 8785 bytes of the complete plan object. Object member
order is immaterial; array order and exact Unicode strings are material.

Numeric literals are IEEE-754 binary64 values represented by exactly sixteen
lowercase hexadecimal bits under type=binary64. NaN and positive or negative
infinity are forbidden in v0.1. Negative zero MUST be canonicalized to positive
zero (0000000000000000) before plan construction; the negative-zero bit
pattern is not a valid plan value. Strings are exact, unnormalized Unicode scalar
sequences. A system
missing result is distinct from a literal and compiles to SQL NULL only for a
numeric output. A string variable has no system-missing state.

Variable names in a canonical plan are the exact catalog names resolved during
binding. Names beginning with `__` are reserved. The plan has one symbolic
target alias; the in-place binding resolves it to one existing dataset and physical
wide table.

## Ordered execution

Operations execute in array order, and every operation observes the schema,
values, and metadata produced by preceding operations. The in-place
binding mutates that same logical dataset and its existing wide table. It MUST
preserve `dataset_id`, physical table identity, case order, and case count, and
MUST NOT publish a new or derived dataset.

`recode` evaluates rules in order and uses the first matching rule. Discrete
value matching is typed and exact. A numeric range is inclusive at both ends.
Its `lower` value MUST compare no greater than `upper`. System missing matches
only numeric system missing. The explicit `unmatched` result is applied when no
rule matches; there is no executor-specific default.

`target_mode=create` requires a target that does not yet exist and appends it
after the current last variable. `target_mode=replace` requires `source` and
`target` to resolve to the same existing variable and retains its ordinal.
All literal rule results, `COPY`, and the target storage kind MUST be compatible.
`COPY` yields the operation's source value. A create operation whose results do
not determine one unambiguous storage kind is invalid.

The in-place binding additionally rejects `target_mode=create` before mutation
when the selected engine cannot include the schema change, data update,
metadata changes, and compact audit in one native transaction. The stable
diagnostic is `schema_change_not_atomic`; implicit-commit DDL MUST NOT be
hidden behind an OpenStatSpec copy or recovery layer.

An unchanged variable retains identity lineage and all metadata. A recoded target
has computed lineage to its source. Creating a target starts with no variable
label, value labels, missing-value metadata, display metadata, or measurement
metadata. Replacing a target preserves all metadata, including its variable
label, value labels, missing-value metadata, display metadata, and measurement
metadata. Later metadata operations modify only the metadata component they
name; set_variable_label and replace_value_labels do not implicitly modify
each other or any missing-value declaration.

`set_variable_label` replaces the target variable label, including with the
empty string. `replace_value_labels` replaces the complete value-label map for
one variable. Label values MUST match the variable storage kind, MUST be unique
by exact typed value, and preserve array order as label ordinal. System missing
cannot have a value label.

## Validation and diagnostics

Structural validation precedes catalog binding. Binding then proves name
resolution, target state, type compatibility, finite numeric literals, range
ordering, and metadata uniqueness before database mutation.
Stable diagnostics include `plan_schema_invalid`, `unknown_variable`,
`target_already_exists`, `target_type_ambiguous`, `mixed_result_types`,
`type_mismatch`, `system_missing_for_string`, `reserved_target_name`,
`duplicate_value_label`, `invalid_numeric_range`, and
`schema_change_not_atomic`.

Compilation MUST be deterministic for a fixed plan, compiler version, target
profile, and bound target schema. It emits direct `UPDATE`, transaction-safe
optional same-table `ALTER TABLE`, and catalog metadata mutations. It MUST NOT emit data-copy,
derived-output, snapshot, rollback, staging-publication, retirement, or recovery
operations.

Machine-readable conformance cases are in
[`../conformance/transformation-plan-0.1.json`](../conformance/transformation-plan-0.1.json).

## In-place binding and audit

The normative architecture is
[`transformation-plan-sql-binding-0.1.md`](transformation-plan-sql-binding-0.1.md).
OpenStatSpec stores at most one compact operation-audit row per apply. It does
not store dataset versions, copied relations, rollback state, or plan-version
history. Source text is LF-normalized before hashing. OpenStatSpec owns none of
the database's undo/version history; on Dolt those capabilities remain Dolt's.
