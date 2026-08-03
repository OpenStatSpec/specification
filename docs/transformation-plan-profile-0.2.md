# OpenStatSpec Transformation Plan Profile 0.2

## Status and scope

This optional profile is the backward-compatible successor to Transformation
Plan 0.1. Its contract identifier is
`openstatspec-transformation-plan-v0.2`. The key words **MUST**, **MUST NOT**,
**SHOULD**, **SHOULD NOT**, and **MAY** are normative.

Version 0.2 retains every 0.1 operation unchanged and adds bounded numeric
assignment, conditional assignment, display-format, measurement-level, and
execution-boundary operations. It remains a language-neutral plan rather than
an arbitrary expression language, SQL fragment, or execution program. A plan
MUST conform to
[`../transformation/plan-0.2.schema.json`](../transformation/plan-0.2.schema.json).

## Canonical identity and backward compatibility

A 0.2 plan contains exactly `contract`, `input_alias`, and a non-empty ordered
`operations` array. Canonical JSON and `plan_hash` use the same restricted RFC
8785 and SHA-256 rules as Plan 0.1. The hash covers the complete exact plan
object, including every expression node and metadata operation. Object member
order is immaterial; array order, expression shape, typed binary64 bits, and
exact unnormalized Unicode strings are material.

The 0.1 schemas, contract identifiers, fixtures, canonical bytes, and hashes are
immutable. A consumer MUST validate a plan against the schema named by its
contract and MUST NOT silently reinterpret, normalize, or upgrade a 0.1 plan as
0.2. An implementation that migrates source text recompiles it explicitly,
produces a separately identified plan, and preserves the prior plan and audit.
A 0.2-capable SPSS frontend emits a 0.1 plan for a program containing only the
0.1 command subset; this preserves old plan hashes.

Typed values, finite binary64 requirements, positive-zero canonicalization,
exact strings, reserved identifiers, and existing `recode`,
`set_variable_label`, and `replace_value_labels` semantics are unchanged
from Plan 0.1.

## Ordered operations

Operations execute strictly in array order. Each operation observes data,
schema, and metadata resulting from all preceding operations in the same plan.
This sequential rule is material: an `assign` may initialize a variable and a
following `conditional_assign` may selectively replace its initialized value.

### Numeric operands and predicates

Version 0.2 operands are either:

- `{"kind":"variable","variable":"name"}`, resolved to one numeric variable; or
- `{"kind":"literal","value":typed-value}`, where the bounded assignment and
  predicate subset requires a finite numeric binary64 value.

String operands and string predicates are outside 0.2. They fail before
mutation with `expression_type_unsupported`. This avoids implicit SQL
collation or coercion semantics.

A comparison node has `expression=comparison`, two operands, and one of
`=`, `<`, `<=`, `>`, or `>=`. A boolean node has
`expression=boolean`, `operator=and|or`, and at least two ordered predicate
operands. Nested boolean nodes preserve parentheses and associativity from the
frontend. Implementations MUST NOT simplify, reorder, deduplicate, distribute,
or constant-fold nodes before canonical hashing.

Predicates use SQL three-valued truth semantics. A comparison with numeric
system missing (SQL `NULL`) is UNKNOWN. `AND` and `OR` use their standard
three-valued truth tables. A conditional assignment writes only where its
predicate is TRUE; FALSE and UNKNOWN both retain the current target value.

### assign

`assign` contains `target`, `target_mode=create|replace`, and one numeric
operand. It evaluates that operand against the pre-operation row and writes the
result to every case. A variable operand that is system missing writes system
missing. `create` appends a fresh numeric variable; `replace` requires an
existing numeric target and retains identity, ordinal, and metadata.

### conditional_assign

`conditional_assign` contains a predicate, an existing numeric `target`, and
one numeric operand. It evaluates the predicate and value against the
pre-operation row, writes only when the predicate is TRUE, and otherwise leaves
the target unchanged. The target MUST already exist when this operation binds.
It has no implicit ELSE branch and never creates a variable.

### metadata and execute

`set_format` replaces only the numeric variable's print/write format with
family `F`, width 1 through 40, and decimals 0 through 16. Width and decimals
MUST form a valid SPSS F format; when decimals are nonzero, width MUST provide
space for a sign, decimal separator, and the requested decimals. Invalid forms
fail with `invalid_format`.

`set_measurement_level` replaces only the variable measurement level with
`nominal`, `ordinal`, or `scale`.

`execute` is an explicit ordered execution boundary retained in the canonical
plan. In one atomic public apply it does not commit, start a second apply, or
publish intermediate state. It performs no row or metadata mutation by itself.

Newly created variables begin without labels, value labels, missing-value
metadata, or measurement metadata. Later ordered metadata operations establish
those properties. Existing targets retain metadata except for the exact
metadata component explicitly replaced by a later operation.

## Binding, validation, and diagnostics

Structural validation, name resolution, type checking, target-state checking,
predicate validation, and backend capability checks all precede mutation.
Stable 0.2 diagnostics add `expression_type_unsupported`,
`conditional_target_missing`, `invalid_format`, and retain the 0.1
diagnostics.

The in-place SQL binding is
[`transformation-plan-sql-binding-0.2.md`](transformation-plan-sql-binding-0.2.md).
A fixed plan, bound schema, implementation version, and target profile MUST
compile deterministically. Generated SQL is not canonical identity.

Machine-readable independent golden cases are in
[`../conformance/transformation-plan-0.2.json`](../conformance/transformation-plan-0.2.json).
