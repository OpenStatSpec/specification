# SPSS-like syntax applied in-place

Given one existing dataset `survey_2026` stored in the wide table
`data_survey_2026`, the caller selects a supported database profile. On Dolt,
the caller additionally selects a branch and verifies its current `HEAD`. This
syntax recodes the existing variable and replaces its labels without creating a
dataset, table, or column:

```spss
RECODE q1 (1,2 = 0) (3 THRU 5 = 1) (ELSE = SYSMIS).
VARIABLE LABELS q1 'Positive response'.
VALUE LABELS q1 0 'No' 1 'Yes'.
```

The canonical plan is the same language-neutral plan shown in the conformance
fixtures. The in-place binding applies it as:

1. `UPDATE data_survey_2026 SET q1 = CASE ... END`;
2. update the `variable`, `variable_catalog`, and typed value-label rows
   for that same dataset; and
3. insert one compact `transformation_apply` audit row with actor, plan/source
   hashes, database profile, and, on Dolt, branch and observed `HEAD`.

Before and after apply there is one dataset row and one persistent data table,
with the same identities. No derived, staging, snapshot, rollback, or hidden
copy table exists. The executor does not run `DOLT_COMMIT`; the caller reviews
the working-set diff and decides separately whether and how to commit it.

On MySQL-family implicit-commit DDL profiles, including Dolt when treated as
non-atomic, the analogous `RECODE q1 ... INTO q1_binary.` request fails with
`schema_change_not_atomic` before any schema, data, metadata, or audit mutation.
