# SPSS Frontend Expansion Design

## Goal

Expand the bounded SPSS syntax frontend in independently claimable stages
without promising general IBM SPSS Statistics compatibility, changing published
Plan 0.1/0.2 identities, or weakening the in-place and Dolt ownership
contracts.

## Research basis

The design compares the current Frontend 0.2 grammar and conformance artifacts
with IBM's command reference and focused data-management references from GNU
PSPP and UCLA OARC. The highest-value gaps are comments, variable-list syntax,
ordinary predicates, arithmetic, missing-value handling, deterministic
functions, string preparation, and selected dictionary operations.

The current plan vocabulary creates a hard version boundary. Comments,
variable-list expansion, alternate predicate syntax, open-ended recode ranges,
and additive value-label syntax can lower to unchanged Plan 0.1/0.2 operations.
Arithmetic, functions, missing predicates, string expressions, schema changes,
case deletion, ordering, grouping, and joins require new normative semantics.

Primary references:

- [IBM SPSS Statistics Command Syntax Reference](https://www.ibm.com/docs/en/SSLVMB_25.0.0/pdf/en/IBM_SPSS_Statistics_Command_Syntax_Reference.pdf)
- [IBM COMMENT command](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=comment-overview-command)
- [IBM string functions](https://www.ibm.com/docs/en/spss-statistics/25.0.0?topic=expressions-string-functions)
- [IBM SELECT IF](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=reference-select-if)
- [IBM FORMATS syntax rules](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=formats-syntax-rules-command)
- [IBM date and time arithmetic](https://www.ibm.com/docs/SSLVMB_sub/statistics_reference_project_ddita/spss/base/syn_date_and_time_arithmetic_operations_date_time_variables.html)
- [IBM Aggregate Data](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=transformations-aggregate-data)
- [IBM MATCH FILES](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=reference-match-files)

Secondary references are the [GNU PSPP manual](https://www.gnu.org/software/pspp/manual/)
and [UCLA OARC SPSS resources](https://stats.oarc.ucla.edu/spss/).

## Selected approach

Use a contract staircase instead of one broad release.

1. Frontend 0.3 accepts only syntax that deterministically emits an exact Plan
   0.1 or Plan 0.2 object.
2. A later Plan, Frontend, and In-Place Binding release adds typed numeric
   expressions and dictionary metadata together.
3. String and physical-schema operations form a separate contract milestone
   with independent SQL atomicity evidence.
4. Case-count/order operations and group/cross-dataset operations use separate
   profiles rather than stretching the current same-cases in-place contract.

This approach creates useful progress before SQL executor changes, keeps old
canonical bytes and hashes immutable, and prevents experimental adapter
identifiers from becoming de facto specification contracts.

## Contract architecture

Every accepted syntax expansion increments the frontend contract because the
contract selects accepted grammar, diagnostics, source spans, and output-plan
selection. A frontend-only release may still emit older plan contracts.

A new Plan contract is required when an addition introduces a new operation,
expression shape, type rule, evaluation rule, or meaning for an existing
operation. A new In-Place Binding contract is required when SQL execution,
catalog mutation, audit behavior, rollback, or profile capability rules change.

Older schemas, fixtures, canonical JSON, hashes, and diagnostics remain
immutable. New manifests inherit successful and failing older cases and prove
that old source continues to emit the same old plans. An inherited case is
identical in the effective set, apart from its namespaced ID and request
contract override, unless its ID appears in `superseded_cases`. A superseding
replacement must use the same request input alias, input schema, and source
text; it may change only the expected diagnostic and expected plan fields that
describe the revised frontend behavior.

## Milestones

### 0. Specification integrity and classification

- Align release-status wording across roadmap, profile documents, changelog,
  tags, and releases.
- Extend repository validation to cover Plan, Frontend, and In-Place manifests,
  schemas, unique IDs, references, canonical bytes, and hashes.
- Publish a command-classification table assigning each proposed SPSS form to
  Frontend-only, new Plan/Binding, a separate profile, or explicit non-goal.

### 1. Frontend 0.3: syntax depth over Plan 0.1/0.2

- Command comments (`COMMENT` and leading `*`) and inline block comments.
- Existing-variable lists and dictionary-order `TO` expansion.
- Grouped forms of already supported labels, formats, levels, and recodes.
- `NOT`, `NE`, `<>`, and `~=` over the existing comparison/boolean grammar,
  with explicit three-valued semantics and canonical lowering to existing
  predicate nodes.
- `LOWEST`/`HIGHEST` recode ranges with finite canonical endpoints.
- `ADD VALUE LABELS`, compiled to a complete ordered
  `replace_value_labels` operation using ordered metadata state initialized
  from the request and updated by preceding commands.

Frontend 0.3 lists only Plan 0.1 and Plan 0.2 as outputs. It does not add an
executor operation or change an in-place binding.

### 2. Typed numeric expressions and dictionary metadata

- Parentheses, unary minus, `+`, `-`, `*`, and `/` with defined precedence,
  overflow, division, and system-missing behavior.
- A deterministic numeric-function whitelist, initially `ABS`, `MOD`, `TRUNC`,
  `RND`, `SQRT`, `LN`, `LG10`, `EXP`, `MIN`, `MAX`, `SUM`, and `MEAN`.
- `MISSING`, `SYSMIS`, `NMISS`, and `NVALID`, distinguishing system missing
  from metadata-defined user missing.
- `MISSING VALUES` as a catalog-only operation.
- Numeric output formats `E`, `COMMA`, `DOT`, and `PCT`; locale-dependent
  currency formats remain excluded.
- Deterministic date construction, extraction, arithmetic, and display based on
  SPSS numeric serial values; current-time and locale-ambiguous parsing remain
  excluded.
- Restricted `DO IF`/`ELSE IF`/`ELSE` containing only operations in the same
  contract. A branch condition is evaluated once against the row state at block
  entry, while selected body operations retain their source order.

The Plan expression IR is typed and source-neutral. Adapters must not insert
source expressions into backend SQL or inherit backend coercion, function,
locale, collation, or error behavior.

### 3. String expressions and schema operations

- `NUMERIC` and `STRING` declarations with exact initialization and width
  semantics.
- String assignment and comparison with explicit fixed-width, blank, Unicode,
  padding, truncation, and collation rules.
- A deterministic string-function whitelist: `CONCAT`, `UPCASE`, `LOWER`,
  `LTRIM`, `RTRIM`, `LENGTH`, `SUBSTR`, `INDEX`, and `REPLACE`.
- Simultaneous `RENAME VARIABLES` with collision and case-only rename rules.
- Controlled `DELETE VARIABLES` with catalog-reference cleanup and dependency
  validation.

Each SQL profile must publish add, rename, and drop-column atomicity evidence.
MySQL, MariaDB, and Dolt continue to require pre-provisioned new targets where
native add-column DDL cannot satisfy one-transaction apply. Rename and delete
must fail before mutation on a profile whose native DDL cannot satisfy the
contract; an output/staging table or full-table copy is not an allowed
workaround. Dolt commits remain caller-owned.

### 4. Case operations

- `SELECT IF` is a destructive, row-count-changing operation with exact TRUE,
  FALSE, and UNKNOWN behavior and explicit affected-case evidence.
- `SORT CASES` is deferred until the standard defines persistent logical case
  order, stable tie-breaking, missing ordering, and string collation. Physical
  table order is never treated as canonical case order.

These operations use a separate case-transformation profile because the current
in-place binding preserves case count and order.

### 5. Group and cross-dataset operations

- Consider only `AGGREGATE OUTFILE=* MODE=ADDVARIABLES` with a small,
  deterministic function set and unchanged row count.
- Consider a restricted keyed lookup with one active dataset and one unique-key
  lookup dataset, explicit selected columns, and unchanged active row count.

Full `AGGREGATE OUTFILE`, unrestricted `MATCH FILES`, and any hidden output,
staging, snapshot, rollback, or copied dataset remain forbidden. Dolt is the
sole persistent version/history layer for successful edits.

## Explicit non-goals

- No claim of full SPSS syntax compatibility.
- No statistical procedures, procedure output, weighting, `SPLIT FILE`, or
  session-wide analysis state.
- No `TEMPORARY` or `FILTER` until a real procedure/query scope exists.
- No random, current-time, `LAG`, cumulative, locale-dependent, or other
  order/state-dependent functions in the deterministic expression profile.
- No macros, loops, vectors, extension-language execution, unrestricted joins,
  reshaping, or `ALTER TYPE` in these milestones.
- No persistent output/staging copies or OpenStatSpec-managed rollback state.

## Conformance and release gates

Each milestone provides a profile document, request/plan schema where
applicable, positive and failure manifest cases, exact source/plan hashes,
stable diagnostics and spans, and inherited compatibility cases.

Specification validation checks artifact structure and identity. Adapter claims
remain downstream: each adapter pins the exact specification commit and runs
the complete applicable frontend/plan suites. Every binding claim also runs
SQLite plus every claimed PostgreSQL, MySQL, MariaDB, Dolt, or future dialect
service profile, including rollback and forbidden-artifact cases.

Specification publication precedes adapter claims and does not wait for them.
No adapter may claim an official contract identifier before that contract is
published from an immutable specification commit. Experimental adapter syntax
uses an explicitly adapter-owned identifier until publication and is not
interoperability evidence for the future official contract.
