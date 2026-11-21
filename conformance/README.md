# Conformance manifests

Each JSON file in this directory is the machine-readable conformance manifest
of one profile. This page describes the manifest keys and how a runner reads
them. It adds no requirement; the profile documents remain normative.

## Common keys

- `manifest_version`, `profile` (display name) and `contract` (the exact
  contract identifier under test; the SAV/ZSAV manifest has none).
- `schema`, `request_schema`, `plan_schema`, `plan_schemas` and `audit_schema`
  are paths relative to the manifest file.
- `cases`: ordered case objects. `id` is unique within the manifest, also after
  inherited cases are expanded. `expected_error` is the stable diagnostic code
  the case must return, or null (or absent) for a successful case.

## Transformation Plan manifests

`transformation-plan-0.1.json` and `transformation-plan-0.2.json`: each case
gives the `plan` object under test and its `expected_plan_hash` (lowercase
SHA-256 of the canonical plan bytes), which is null for a failing case.

## SPSS syntax frontend manifests

`spss-syntax-frontend-0.1.json`, `-0.2.json` and `-0.3.json`: each case gives
the complete frontend `request` (`contract`, `input_alias`, `input_schema`,
`source_text`) and the `expected_source_hash`. A successful case declares
exactly one expected plan with one of these keys:

- `expected_plan`: the expected plan inline.
- `expected_plan_case`: a case `id` in a Transformation Plan manifest
  (`transformation-plan-0.1.json` for Frontend 0.1 cases,
  `transformation-plan-0.2.json` for Frontend 0.2 cases). The expected plan
  and hash are that case's `plan` and `expected_plan_hash`.
- `expected_plan_0_1`: an exact Plan 0.1 object inline, used in the 0.2 and
  0.3 manifests for programs that stay inside the Plan 0.1 subset.
- `expected_plan_case_0_1`: a case `id` in the Frontend 0.1 manifest
  `spss-syntax-frontend-0.1.json`, not in a plan manifest. Used only in the
  0.2 and 0.3 manifests. The expected plan is that Frontend 0.1 case's
  resolved expected plan (its inline `expected_plan`, or the plan named by its
  `expected_plan_case`).

`expected_plan_contract` optionally names the expected plan's contract.
`expected_plan_hash`, when present, is the hash of the resolved expected plan.
`expected_output_metadata` lists variable metadata expected after the plan is
applied.

The 0.3 manifest has `inherited_manifests`. Each entry names an older frontend
`manifest` whose cases also run under Frontend 0.3, the
`request_contract_override` written into every inherited request, and
`superseded_cases`, which maps an inherited case id to the declared 0.3 case
that replaces it. Inherited case ids are prefixed with their source version,
for example `0.1/recode-labels-and-value-labels`.

## In-place binding manifests

`in-place-transformation-0.1.json` and `in-place-transformation-0.2.json`:
each case names its `database_profile`. A case states its input as
`source_text` (0.1) or as the paired `applied_plan_case` and
`applied_frontend_case` (0.2), which name a Transformation Plan 0.2 case and a
Frontend 0.2 case that lower to the same plan. Dolt context is given by
`expected_context`/`observed_context` (0.1) or `expected_branch`,
`expected_head` and `working_set_clean` (0.2). Other keys describe the stated
state and expectations: `actor`, `target_mode`, `target_preprovisioned`,
`before`, `after`, `before_rows`, `after_rows`, `after_failure`,
`expected_audit`, `required_audit_fields`, `forbidden_artifacts`,
`mutation_started`, `failure_point`, `completion_context` and
`rollback_probe`.

Some cases give no plan (`source_text` or `applied_plan_case`) and no data,
for example `mysql-create-target-fails-before-mutation`,
`mariadb-create-target-fails-before-mutation`,
`dolt-create-target-fails-before-mutation`,
`dolt-empty-actor-fails-before-mutation` and the 0.1 `reject-dolt-*` cases.
They test a check made before mutation. A runner may run such a case with any
valid plan of the stated `target_mode` against a synthetic dataset; the
expected diagnostic and `mutation_started` do not depend on that choice. When a
case states no `target_mode`, as `dolt-empty-actor-fails-before-mutation`
does, a runner can use a `replace` plan, so that no create-target refusal
(such as `schema_change_not_atomic` on Dolt) comes before the check the case
names. For the completion check in
`dolt-context-changed-after-mutation-rolls-back`, see the runner note in
[In-Place Transformation Binding 0.2](../docs/transformation-plan-sql-binding-0.2.md).

## SPSS SAV/ZSAV manifest

`spss-sav-zsav-1.0.json` lists `required_capabilities`, the round-trip
`comparison` and `fixtures`. Each fixture gives `id`, `source` (relative to
this directory), `directions`, `expects` and, where given, `expected_catalog`.
The `preflight-failure` source `fixtures/preflight-too-wide.sav` is not
committed: as [`fixtures/README.md`](fixtures/README.md) states, the runner
generates it with one more variable than the target profile permits.

## SQL Transformation Workflow manifest

`sql-transformation-workflow-0.1.json` gives the `hash_profile`, input
`fixtures`, workflow `cases`, `recovery_cases` and `canonicalization_cases`
defined by the
[SQL Transformation Workflow Profile 0.1](../docs/sql-transformation-workflow-profile-0.1.md).
