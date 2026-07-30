# SQL transformation workflow example

This non-normative example filters a conformant core dataset. The import stays
untouched; the result is a separate optional-profile derived dataset.

## Versioned query

The executor binds `:minimum_age` through the database driver and resolves the
logical `parent` input alias to its fixed, fully qualified physical relation.
It owns staging/output names and creation of `__row_ordinal`.

```sql
SELECT respondent_id, age, region, survey_weight
FROM parent
WHERE age >= :minimum_age
ORDER BY respondent_id ASC NULLS LAST
```

```json
{
  "dialect_family": "postgresql",
  "server_version_constraint": ">=16 <18",
  "output_mode": "materialized",
  "row_semantics": "filter",
  "metadata_policy": "identity_only",
  "deterministic_order": [{"expression": "respondent_id", "direction": "ASC", "nulls": "LAST", "collation": null}],
  "output_schema": {
    "variables": [
      {"column_ordinal": 1, "physical_name": "respondent_id", "logical_storage_kind": "numeric", "is_nullable": false, "lineage_kind": "identity", "lineage": [{"input_alias": "parent", "parent_column": "respondent_id", "expression_role": "identity"}], "metadata": null},
      {"column_ordinal": 2, "physical_name": "age", "logical_storage_kind": "numeric", "is_nullable": true, "lineage_kind": "identity", "lineage": [{"input_alias": "parent", "parent_column": "age", "expression_role": "identity"}], "metadata": null},
      {"column_ordinal": 3, "physical_name": "region", "logical_storage_kind": "string", "is_nullable": false, "lineage_kind": "identity", "lineage": [{"input_alias": "parent", "parent_column": "region", "expression_role": "identity"}], "metadata": null},
      {"column_ordinal": 4, "physical_name": "survey_weight", "logical_storage_kind": "numeric", "is_nullable": false, "lineage_kind": "identity", "lineage": [{"input_alias": "parent", "parent_column": "survey_weight", "expression_role": "identity"}], "metadata": null}
    ],
    "weight": {
      "physical_name": "survey_weight",
      "derivation_kind": "identity",
      "meaning": null
    }
  },
  "parameters": [
    {
      "ordinal": 1,
      "name": "minimum_age",
      "logical_type": "integer",
      "nullable": false,
      "sensitive": false
    }
  ]
}
```

The adapter preflights definition and input hashes, executes into an
unpredictable profile-owned staging table, validates, prepends a contiguous
`__row_ordinal`, and atomically publishes relation and catalog records.

| `__row_ordinal` | `respondent_id` | `age` | `region` | `survey_weight` |
| ---: | ---: | ---: | --- | ---: |
| 1 | 104 | 25 | North | 0.92 |
| 2 | 109 | 41 | South | 1.08 |

All user columns have identity lineage. Since this is a row filter and
`survey_weight` is unchanged, its weight designation may propagate as
`identity`. Rescaling, aggregation, or row multiplication forbids this.

## Aggregate example

```sql
SELECT region, COUNT(*) AS unweighted_n, SUM(survey_weight) AS weighted_n
FROM parent
GROUP BY region
ORDER BY region COLLATE "C" ASC NULLS LAST
```

This declares `row_semantics = aggregate`. `region` has grouping lineage and
both counts have aggregate lineage. The result has no implicit weight:
`weighted_n` is an estimate, not a case weight.

## Failure example

```sql
DELETE FROM parent;
SELECT * FROM parent
```

This is rejected before execution. The adapter retains a failed run with an
`unsafe_sql` event, creates no derived dataset, and leaves no output or staging
relation.