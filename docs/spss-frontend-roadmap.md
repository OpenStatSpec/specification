# SPSS Syntax Frontend Roadmap

## Status and boundary

This roadmap describes intended work, not a compatibility claim or release-date
promise. The current published boundary remains the exact bounded grammar in
[SPSS Syntax Frontend 0.2](spss-syntax-frontend-profile-0.2.md). Every syntax
form outside a claimed frontend contract must continue to fail closed.

OpenStatSpec will expand the frontend in independently versioned stages. It will
not advertise general IBM SPSS Statistics compatibility, forward source
expressions into SQL, or weaken the same-dataset/same-table and caller-owned
Dolt history rules.

Frontend 0.3 is specification-complete as a release candidate. Adapter claims
remain pending and separately gated; adapter evidence does not block
specification publication.

## Command classification

| Capability | Intended boundary | Reason |
| --- | --- | --- |
| Comments, existing-variable `TO`, grouped labels and recodes | Frontend 0.3, Plan 0.1 | Compile-time syntax expansion only |
| Grouped `FORMATS` and `VARIABLE LEVEL` | Frontend 0.3, Plan 0.2 | Expands to existing Plan 0.2 metadata operations |
| `NOT`, `NE`, `<>`, `~=` over the existing predicate grammar | Frontend 0.3, Plan 0.2 | Canonically lowers to existing comparisons and booleans |
| `LOWEST`/`HIGHEST` recode ranges | Frontend 0.3, Plan 0.1/0.2 | Lowers to finite binary64 endpoints; system missing remains distinct |
| `ADD VALUE LABELS` | Frontend 0.3, Plan 0.1/0.2 | Lowers ordered metadata state to complete label replacement |
| Arithmetic, deterministic numeric/date functions, missing predicates | New Plan/Frontend/Binding generation | Adds expression shapes and normative evaluation semantics |
| `MISSING VALUES` and additional numeric/date formats | New Plan/Frontend/Binding generation | Adds catalog operations and format semantics |
| Restricted `DO IF` | New Plan/Frontend/Binding generation | Requires branch-once and ordered-body semantics |
| `NUMERIC`, `STRING`, string expressions/functions, rename/delete | Separate Plan/Frontend/Binding generation | Adds types, physical DDL, catalog cleanup, and atomicity rules |
| `SELECT IF`, `SORT CASES` | Separate case-transformation profile | Changes current case-count/order invariants |
| Restricted add-variable aggregate and keyed lookup | Separate group/cross-dataset profile | Introduces group and multi-dataset semantics |
| `TEMPORARY`, `FILTER`, procedures, state/order-dependent functions | Explicit non-goal | Requires procedure/session state outside the mutation frontend |

## Milestone 0: integrity and classification

- [x] Specification-complete: Plan, Frontend, and In-Place schemas, manifests,
  references, canonical bytes, and source/plan hashes are validated.
- [x] Add specification-owned validation for Plan, Frontend, and In-Place schemas,
  manifests, references, canonical bytes, and source/plan hashes.
- Keep release status consistent across profile documents, roadmap, changelog,
  tags, and releases.
- Classify every proposed command as frontend-only, new Plan/Binding work, a
  separate profile, or an explicit non-goal before accepting syntax.

Adapter claims remain pending and separately gated; adapter evidence does not
block specification publication.

## Milestone 1: Frontend 0.3 over Plan 0.1/0.2

- [x] Specification-complete: the schema, profile, 35 declared cases,
  inherited compatibility, and repository validation are present.
Frontend 0.3 adds syntax depth without adding plan operations:

- `COMMENT`, leading-star comments, and inline block comments;
- existing-variable lists with dictionary-order `TO` expansion;
- grouped forms of supported labels and recodes (Plan 0.1), plus grouped `FORMATS` and `VARIABLE LEVEL` (Plan 0.2);
- `NOT`, `NE`, `<>`, and `~=` over the existing predicate grammar with
  three-valued truth semantics;
- `LOWEST` and `HIGHEST` recode ranges; and
- `ADD VALUE LABELS`, lowered to a complete value-label replacement using the
  ordered metadata state initialized from the request and updated by preceding
  commands.

The manifest must list only Plan 0.1 and Plan 0.2 outputs and prove that all
inherited programs retain their exact prior plans and hashes. No SQL binding or
executor change belongs in this milestone.

Adapter claims remain pending and separately gated; adapter evidence does not
block specification publication.

## Milestone 2: typed numeric expressions and metadata

Define a new Plan, Frontend, and In-Place Binding generation for:

- arithmetic parentheses, unary minus, `+`, `-`, `*`, and `/`;
- a deterministic numeric-function whitelist;
- `MISSING`, `SYSMIS`, `NMISS`, and `NVALID`;
- `MISSING VALUES` metadata;
- numeric `E`, `COMMA`, `DOT`, and `PCT` formats; and
- deterministic date construction, extraction, arithmetic, and display over
  SPSS numeric serial values; and
- restricted `DO IF`/`ELSE IF`/`ELSE` blocks.

The canonical expression model must define precedence, binary64 behavior,
domain errors, missing propagation, and sequential evaluation independently of
backend SQL behavior. Random, current-time, order-dependent, and
locale-dependent functions remain excluded. A conditional-block branch is
selected once from row state at block entry; its body then executes in source
order.

## Milestone 3: strings and physical schema

Define a separate contract milestone for:

- `NUMERIC` and `STRING` declarations;
- string assignment, comparison, and a small deterministic function whitelist;
- simultaneous `RENAME VARIABLES`; and
- controlled `DELETE VARIABLES` with dependency checks and complete catalog
  cleanup.

The contract must specify fixed-width strings, blanks, padding, truncation,
Unicode indexing, collation, initialization, and physical/catalog identity.
Every SQL profile needs exact add/rename/drop-column atomicity and rollback
evidence. Non-atomic profiles retain explicit pre-provisioning for new targets.
Rename and delete fail before mutation where native DDL cannot satisfy the
contract; copied or staging tables are not recovery mechanisms. Dolt branch,
HEAD, clean-working-set, and caller-owned commit policy remain in force.

## Milestone 4: case operations

Treat row-count and row-order changes as a separate case-transformation profile:

- `SELECT IF` may be considered as an explicit destructive operation with
  affected-case evidence and exact UNKNOWN handling.
- `SORT CASES` waits for a persistent logical case-order model with stable
  tie-breaking, missing ordering, and string collation.

Neither command may be retrofitted into a binding that claims to preserve case
count and order. Physical SQL row order is not logical case order.

## Milestone 5: group and cross-dataset operations

Only bounded, row-count-preserving forms are candidates:

- `AGGREGATE OUTFILE=* MODE=ADDVARIABLES` with a small deterministic function
  set; and
- a unique-key lookup that adds selected columns to the active dataset without
  changing its row count.

Full `AGGREGATE OUTFILE`, unrestricted `MATCH FILES`, persistent outputs,
staging tables, snapshots, rollback copies, and hidden recovery datasets remain
outside this roadmap.

## Explicit non-goals

- Full SPSS syntax compatibility or statistical procedures.
- `TEMPORARY`, `FILTER`, weighting, `SPLIT FILE`, or procedure-scoped state.
- Random, current-time, `LAG`, cumulative, or environment-dependent functions.
- Macros, loops, vectors, extension-language execution, unrestricted joins,
  reshaping, or `ALTER TYPE`.
- Any OpenStatSpec-managed persistent version or rollback layer. Dolt remains
  the sole persistent version/history mechanism for successful edits.

## Evidence sources

The priorities are based on IBM's
[Command Syntax Reference](https://www.ibm.com/docs/en/SSLVMB_25.0.0/pdf/en/IBM_SPSS_Statistics_Command_Syntax_Reference.pdf),
[string-function documentation](https://www.ibm.com/docs/en/spss-statistics/25.0.0?topic=expressions-string-functions),
[FORMATS rules](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=formats-syntax-rules-command),
[SELECT IF reference](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=reference-select-if),
[Aggregate Data documentation](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=transformations-aggregate-data),
and [MATCH FILES reference](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=reference-match-files).
GNU PSPP and UCLA OARC documentation provide secondary implementation and
usage evidence; IBM semantics and OpenStatSpec's normative contracts remain
authoritative.
