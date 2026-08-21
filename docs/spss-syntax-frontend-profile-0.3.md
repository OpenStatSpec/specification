# OpenStatSpec SPSS-like Syntax Frontend Profile 0.3

## Status and boundary

This optional frontend profile maps a deliberately bounded SPSS-like command
language to Transformation Plan 0.1 or 0.2. Its request contract is
`openstatspec-spss-syntax-frontend-v0.3`. It is not full IBM SPSS Statistics
syntax and MUST reject every command, expression, or coercion not defined here.

The request conforms to
[`../transformation/spss-syntax-frontend-0.3.schema.json`](../transformation/spss-syntax-frontend-0.3.schema.json).
All Frontend 0.2 lexical rules, command termination, exact source hashing,
case-insensitive name resolution, quote handling, and failure atomicity remain
in force. The input schema retains only ordered variables, storage kind,
variable and value labels, format family, width, decimals, and measurement
level. It does not declare physical identifiers.

## Compatibility and output-plan selection

Frontend 0.3 consumes unchanged Frontend 0.2 input-schema fields and unchanged
Plan 0.1 and Plan 0.2 contracts. Comments, `TO`, grouped syntax, open-ended
RECODE ranges, and additive value labels remain in the Plan 0.1 output subset.
Predicate aliases and `NOT` require the existing Plan 0.2 `conditional_assign`
syntax. A program containing only commands and productions in the Plan 0.1
subset MUST emit an exact Plan 0.1 object. A program containing a 0.2-only
predicate production MUST emit Plan 0.2. No command is dropped, and the
frontend performs no data mutation, SQL execution, branch operation, or Dolt
commit.

## Comments and source identity

Leading-star comments are recognized only when `*` is the first non-whitespace
token at a command boundary. Such a comment ends at the next command period.
The `COMMENT` command is a command comment and ends at its command period.
Non-nested `/* ... */` comments are accepted wherever whitespace is legal.
Unterminated or nested block comments MUST return `spss_syntax_error`.

Comments are retained in the LF-normalized source used for source hashing and
emit no operation. A comment-only program MUST return `spss_syntax_error`
because a valid plan cannot have zero operations. Source hashing remains
SHA-256 of UTF-8 source after CRLF and CR are converted to LF. The complete
emitted plan is hashed independently under its declared plan contract.

## Existing-variable lists

The bounded grammar is:

```text
existing-variable-list := existing-variable
                          ((existing-variable | TO existing-variable))*
comparison-operator    := "=" | "<" | "<=" | ">" | ">="
                          | "NE" | "<>" | "~="
predicate              := comparison | "(" predicate ")"
                          | NOT predicate
                          | predicate AND predicate
                          | predicate OR predicate
open-range             := LOWEST THRU finite-number
                          | finite-number THRU HIGHEST
                          | LOWEST THRU HIGHEST
```

`TO` expands inclusively using the current ordered input-schema state, not
variable spelling or a numeric suffix. Reverse ranges MUST return
`invalid_variable_range`; absent endpoints MUST return `unknown_variable`.
`TO` is forbidden for generated `INTO` target sequences. Resolved variables
retain their catalog spelling and source order; each occurrence is resolved at
the point its command is lowered.

## Predicate aliases and NOT lowering

`NE`, `<>`, and `~=` are aliases for ordered `< OR >` comparisons. `NOT` is
accepted only over the existing comparison and boolean grammar. It lowers
recursively using comparison complements and De Morgan's laws, while
preserving SQL three-valued truth. The complements are `=` to `< OR >`, `<` to
`>=`, `<=` to `>`, `>` to `<=`, and `>=` to `<`; `NE`, `<>`, and `~=` first
lower to `< OR >`. Boolean negation swaps `AND` and `OR` recursively.

The canonical lowering table is:

```text
NOT (left = right)  -> (left < right OR left > right)
NOT (left < right)  -> left >= right
NOT (left <= right) -> left > right
NOT (left > right)  -> left <= right
NOT (left >= right) -> left < right
NOT (a AND b)       -> NOT a OR NOT b
NOT (a OR b)        -> NOT a AND NOT b
```

Canonical lowering flattens maximal same-operator boolean expressions while
preserving operand order. Parentheses override precedence across different
operators, but parentheses around a same-operator expression do not prevent
required flattening. Missing comparisons remain UNKNOWN and no lowering may
turn UNKNOWN into TRUE or FALSE.

## Open-ended RECODE ranges

`RECODE` retains the Frontend 0.2 typed selector and result rules. In addition,
numeric selectors may use the open-range forms in the grammar above. `LOWEST`
is the finite binary64 value with bits `ffefffffffffffff`, and `HIGHEST` is the
finite binary64 value with bits `7fefffffffffffff`. These bounds include every
finite binary64 value in the corresponding direction. SQL NULL/system missing
is not included in an open range.

Open ranges are inclusive and lower to the existing ordered `recode` range
representation. Non-finite values, malformed finite numbers, and reverse
ranges are rejected with `spss_syntax_error` or `invalid_variable_range` as
applicable. The finite-number token remains the exact ASCII grammar inherited
from Frontend 0.2 and is interpreted as an exact base-ten value before
ties-to-even binary64 conversion.

## ADD VALUE LABELS

`ADD VALUE LABELS variable... value 'label' [value 'label' ...]
[/ variable... value 'label' ...].` resolves each existing variable against
the current typed schema. An existing typed value is updated at its current
ordinal. A new typed value is appended in source order. Duplicate values in a
single source group are invalid unless the operation is the update of that
same existing typed value according to this rule.

The frontend emits one complete `replace_value_labels` operation per variable,
in source variable order, preserving all existing labels and applying the
updates and appended values. Variable and value types MUST agree; no implicit
numeric/string coercion is performed. The command remains in the Plan 0.1
output subset.

## Failure contract

The frontend MUST produce no partial plan after any error. In addition to the
inherited 0.1 and 0.2 diagnostics, stable diagnostics include
`invalid_variable_range`, `unknown_variable`, and `spss_syntax_error` for the
rules defined here. Unsupported commands or productions return
`unsupported_spss_command` or `spss_syntax_error` as appropriate. Diagnostics
identify source spans but MUST NOT include credentials or unrelated row values.

## Conformance

Conformance cases for this profile are published in
[`../conformance/spss-syntax-frontend-0.3.json`](../conformance/spss-syntax-frontend-0.3.json).
The manifest declares 28 Frontend 0.3 cases and expands to 83 effective cases
after inherited cases and the two published comment supersessions are applied.
