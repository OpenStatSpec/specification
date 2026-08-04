-- OpenStatSpec In-Place Transformation Bindings 0.1 and 0.2 compact operation audit.
-- This table is not a dataset-version catalog and stores no row data or copies.

CREATE TABLE transformation_apply (
  apply_id                    UUID PRIMARY KEY,
  contract_id                TEXT NOT NULL,
  database_profile           TEXT NOT NULL,
  dataset_id                 UUID NOT NULL REFERENCES dataset(dataset_id),
  physical_table_schema      TEXT NULL,
  physical_table_name        TEXT NOT NULL,
  source_hash                CHAR(64) NOT NULL,
  plan_hash                  CHAR(64) NOT NULL,
  canonical_plan_json        TEXT NOT NULL,
  actor                       TEXT NOT NULL,
  status                      TEXT NOT NULL,
  dolt_branch                 TEXT NULL,
  dolt_head_before            TEXT NULL,
  dolt_head_after             TEXT NULL,
  operation_count             INTEGER NOT NULL,
  started_at                  TIMESTAMP NOT NULL,
  completed_at                TIMESTAMP NOT NULL,
  CHECK (contract_id IN (
    'openstatspec-in-place-transformation-v0.1',
    'openstatspec-in-place-transformation-v0.2'
  )),
  CHECK (database_profile IN ('sqlite', 'postgresql', 'mysql', 'mariadb', 'dolt')),
  CHECK (status IN ('succeeded', 'failed')),
  CHECK (operation_count > 0),
  CHECK (
    (NOT (database_profile = 'dolt')
      AND dolt_branch IS NULL
      AND dolt_head_before IS NULL
      AND dolt_head_after IS NULL)
    OR
    (database_profile = 'dolt'
      AND dolt_branch IS NOT NULL
      AND dolt_head_before IS NOT NULL
      AND (status = 'failed' OR dolt_head_after = dolt_head_before))
  )
);

-- Concrete DDL validates lowercase hashes and exact dataset/schema/table
-- identity against the referenced dataset row at apply start and completion.
-- No derived, staging, snapshot, rollback, plan-version, or recovery relation
-- belongs to this binding.
