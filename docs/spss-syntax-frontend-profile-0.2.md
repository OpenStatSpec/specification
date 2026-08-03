# OpenStatSpec SPSS-like Syntax Frontend Profile 0.2

## Status and boundary

Status: release candidate for the planned OpenStatSpec `v0.3.0` release. This profile is not a published stable specification until a `v0.3.0` tag targets its exact commit.

This optional frontend maps a bounded SPSS-like command language to
Transformation Plan 0.1 or 0.2. Its request contract is
`openstatspec-spss-syntax-frontend-v0.2`. It is not full IBM SPSS Statistics
syntax and MUST reject every command, expression, or coercion not defined here.

All lexical rules, command termination, exact source hashing, case-insensitive
name resolution, quote handling, and failure atomicity from Frontend 0.1 remain
in force. The input request conforms to
[`../transformation/spss-syntax-frontend-0.2.schema.json`](../transformation/spss-syntax-frontend-0.2.schema.json).

The 0.1 commands `RECODE`, `VARIABLE LABELS`, and `VALUE LABELS` are
unchanged. A program containing only that subset MUST emit an exact Plan 0.1
object. A program containing any command introduced below emits Plan 0.2.

## Numeric expression grammar

The bounded grammar is:

```text
operand     := numeric-variable | finite-number
comparison  := operand ("=" | "<" | "<=" | ">" | ">=") operand
predicate   := comparison | "(" predicate ")"
             | predicate AND predicate
             | predicate OR predicate
```

Comparison binds tighter than `AND`; `AND` binds tighter than `OR`.
Parentheses override precedence and are preserved as the equivalent nested
plan shape. Keywords are ASCII case-insensitive. Unary operators, arithmetic,
functions, strings, `NOT`, `~=`, `<>`, `MISSING`, locale-dependent
numbers, and implicit numeric/string coercion are unsupported.

A numeric variable is resolved at the point its command is lowered, including
variables created by preceding commands. All referenced variables and assigned
values in this subset MUST be numeric.

## Added commands

`COMPUTE target = operand.` lowers to one ordered `assign`. If `target`
does not yet exist, it uses `target_mode=create`; otherwise it uses
`target_mode=replace`. No expression beyond the bounded operand form is
accepted in 0.2.

`IF (predicate) target = operand.` lowers to one `conditional_assign`.
Parentheses around the complete predicate are required. The target MUST exist
at that point in command order. There is no ELSE form: a row is changed only
when the predicate is TRUE. FALSE and UNKNOWN retain the previous target value.

`FORMATS variable (Fwidth.decimals) [variable
(Fwidth.decimals) ...].` lowers each pair in source order to `set_format`.
Only the numeric `F` family is supported. Family is canonicalized to uppercase;
width and decimals are canonical decimal integers.

`VARIABLE LEVEL variable-list (NOMINAL|ORDINAL|SCALE)
[/ variable-list (level) ...].` lowers one `set_measurement_level` operation
per resolved variable, preserving group and variable order. Levels are
canonicalized to lowercase.

`EXECUTE.` lowers to `{"op":"execute"}`. It marks source intent and ordered
identity but does not perform or authorize a database commit.

For example:

```spss
COMPUTE target = 0.
IF (source_a = 1 AND source_b = 1) target = 1.
VARIABLE LABELS target 'Example label'.
VALUE LABELS target 0 'No' 1 'Yes'.
FORMATS target (F1.0).
VARIABLE LEVEL target (NOMINAL).
EXECUTE.
```

lowers to sequential initialization, conditional replacement, label, value
labels, format, measurement level, and execution-boundary operations. No
command may be dropped.

## System missing

A variable operand may evaluate to numeric system missing. `COMPUTE` copies
that missing value. Comparisons involving missing are UNKNOWN, boolean
predicates use SQL three-valued truth, and `IF` writes only for TRUE. The
frontend MUST NOT silently turn missing into zero or FALSE.

## Failure contract

The frontend returns no partial plan on error. In addition to 0.1 diagnostics,
stable diagnostics include `expression_type_unsupported`,
`conditional_target_missing`, and `invalid_format`. Unsupported commands or
expression productions return `unsupported_spss_command` or
`spss_syntax_error` as appropriate. Diagnostics identify source spans without
including credentials or unrelated row values.

The source hash remains SHA-256 of UTF-8 source after CRLF and CR are converted
to LF. The complete emitted plan is hashed independently under its declared
plan contract.

Machine-readable golden cases are in
[`../conformance/spss-syntax-frontend-0.2.json`](../conformance/spss-syntax-frontend-0.2.json).
