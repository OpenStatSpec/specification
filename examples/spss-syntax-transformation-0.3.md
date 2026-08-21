# SPSS-like transformation frontend 0.3 release-candidate example

This exact program combines the Frontend 0.3 syntax additions. The input
schema has `score_a`, `score_b`, and `score_c` as numeric variables in that
dictionary order. `mismatch` is an existing numeric target; the program does
not create it.

```spss
* Normalize the selected score block.
RECODE score_a TO score_c (LOWEST THRU 0 = 0) (1 THRU HIGHEST = 1).
ADD VALUE LABELS score_a TO score_c 0 'Non-positive' 1 'Positive'.
FORMATS score_a TO score_c (F1.0).
IF (NOT (score_a = score_b)) mismatch = 1.
EXECUTE.
```

`TO` expands inclusively in dictionary order, so each command addresses
`score_a`, `score_b`, and `score_c`, not names inferred from a suffix. The
finite open ranges lower `LOWEST` and `HIGHEST` to the finite binary64
endpoints defined by the profile; SQL NULL/system-missing remains outside the
range. `ADD VALUE LABELS` lowers to a complete additive-label replacement for
each variable, preserving the ordered existing label state and applying the
updates. `NOT (score_a = score_b)` lowers to the existing `< OR >` comparison
form, with SQL three-valued truth preserved.

The leading comment is retained in the LF-normalized source used for the
source SHA-256 hash, while comments emit no operation. The full emitted plan
has its own canonical plan hash. This program uses the Plan 0.1 subset for the
recode, labels, and formats, but the conditional assignment and lowered
predicate selects between the immutable Plan 0.1/0.2 outputs. A program without a Plan 0.2-only
predicate production selects Plan 0.1 instead. The corresponding manifest
cases prove each production independently, including
`recode-lowest-thru-upper`, `recode-lower-thru-highest`,
`add-value-labels-multiple-variable-group`, `formats-grouped-to-expands-source-order`,
and `not-equality-lowers-to-less-or-greater`.

Frontend 0.3 adds no SQL binding operation. The existing same-dataset and
same-physical-table policy is unchanged. MySQL, MariaDB, and Dolt still
require caller-owned pre-provisioning for a new target, and Dolt still keeps
branch, HEAD, working-set, and commit ownership with the caller; the frontend
does not call `DOLT_COMMIT`.
