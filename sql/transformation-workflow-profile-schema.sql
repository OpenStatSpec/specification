-- Optional OpenStatSpec SQL Transformation Workflow Profile 0.1.
-- This logical catalog is separate from the source-faithful core catalog.

CREATE TABLE transformation_profile_identity (
  profile_identity_key       INTEGER PRIMARY KEY, -- exactly 1
  contract_id                TEXT NOT NULL UNIQUE,
  schema_version             INTEGER NOT NULL,
  core_contract_id           TEXT NOT NULL,
  created_at                 TIMESTAMP NOT NULL,
  CHECK (profile_identity_key = 1),
  CHECK (contract_id = 'openstatspec-sql-transformation-workflow-v0.1'),
  CHECK (core_contract_id = 'openstatspec-strict-wide-table-v1')
);

CREATE TABLE transformation_definition (
  transformation_id          UUID PRIMARY KEY,
  stable_name                TEXT NOT NULL UNIQUE,
  title                      TEXT NOT NULL,
  description                TEXT NULL,
  created_at                 TIMESTAMP NOT NULL
);

CREATE TABLE transformation_version (
  transformation_version_id  UUID PRIMARY KEY,
  transformation_id          UUID NOT NULL REFERENCES transformation_definition(transformation_id),
  version_number             INTEGER NOT NULL,
  query_sql                  TEXT NOT NULL,
  dialect_family             TEXT NOT NULL, -- sqlite | postgresql | mysql | mariadb
  server_version_constraint  TEXT NOT NULL,
  output_mode                TEXT NOT NULL, -- materialized | view
  row_semantics              TEXT NOT NULL, -- one_to_one | filter | aggregate | join | reshape | other
  metadata_policy            TEXT NOT NULL, -- none | identity_only | declared
  output_schema_json          TEXT NOT NULL,
  deterministic_order_json   TEXT NOT NULL,
  definition_hash            TEXT NOT NULL,
  published_at               TIMESTAMP NOT NULL,
  UNIQUE (transformation_id, version_number),
  UNIQUE (transformation_version_id, definition_hash)
);

CREATE TABLE transformation_parameter (
  transformation_version_id  UUID NOT NULL REFERENCES transformation_version(transformation_version_id),
  parameter_ordinal          INTEGER NOT NULL,
  parameter_name             TEXT NOT NULL,
  logical_type               TEXT NOT NULL,
  is_nullable                BOOLEAN NOT NULL,
  default_canonical_json     TEXT NULL,
  is_sensitive              BOOLEAN NOT NULL,
  PRIMARY KEY (transformation_version_id, parameter_ordinal),
  UNIQUE (transformation_version_id, parameter_name)
);

-- A run exists before a result exists and remains as the failure audit root.
CREATE TABLE transformation_run (
  transformation_run_id      UUID PRIMARY KEY,
  transformation_version_id  UUID NOT NULL,
  status                     TEXT NOT NULL, -- started | succeeded | failed
  executor_identity          TEXT NOT NULL,
  correlation_id             TEXT NOT NULL,
  staging_relation_key       TEXT NULL, -- durably recorded before staging DDL; retained for recovery/audit
  engine_name                TEXT NOT NULL,
  engine_version             TEXT NOT NULL,
  dialect_profile            TEXT NOT NULL,
  capability_snapshot_json   TEXT NOT NULL,
  specification_commit       TEXT NOT NULL,
  definition_hash            TEXT NOT NULL,
  parameters_hash            TEXT NOT NULL,
  input_set_hash             TEXT NOT NULL,
  started_at                 TIMESTAMP NOT NULL,
  completed_at               TIMESTAMP NULL,
  UNIQUE (transformation_run_id, status),
  FOREIGN KEY (transformation_version_id, definition_hash)
    REFERENCES transformation_version(transformation_version_id, definition_hash)
);

CREATE TABLE transformation_run_parameter (
  transformation_run_id      UUID NOT NULL REFERENCES transformation_run(transformation_run_id),
  parameter_ordinal          INTEGER NOT NULL,
  parameter_name             TEXT NOT NULL,
  logical_type               TEXT NOT NULL,
  value_envelope             TEXT NOT NULL,
  value_hash                 TEXT NOT NULL,
  is_sensitive              BOOLEAN NOT NULL,
  PRIMARY KEY (transformation_run_id, parameter_ordinal),
  UNIQUE (transformation_run_id, parameter_name)
);

CREATE TABLE transformation_run_input (
  transformation_run_id      UUID NOT NULL REFERENCES transformation_run(transformation_run_id),
  input_ordinal              INTEGER NOT NULL,
  input_alias                TEXT NOT NULL,
  input_kind                 TEXT NOT NULL, -- core | derived
  core_dataset_id            UUID NULL REFERENCES dataset(dataset_id),
  derived_dataset_id         UUID NULL,
  physical_relation_schema_snapshot   TEXT NULL,
  physical_relation_name_snapshot     TEXT NOT NULL,
  physical_relation_key_snapshot      TEXT NOT NULL,
  schema_hash                TEXT NOT NULL,
  snapshot_hash_kind         TEXT NOT NULL, -- relation_snapshot
  snapshot_hash_algorithm    TEXT NOT NULL, -- sha256
  snapshot_hash_version      TEXT NOT NULL, -- openstatspec-relation-snapshot-v1
  content_or_source_hash     TEXT NOT NULL,
  PRIMARY KEY (transformation_run_id, input_ordinal),
  UNIQUE (transformation_run_id, input_alias),
  CHECK (
    (input_kind = 'core' AND core_dataset_id IS NOT NULL AND derived_dataset_id IS NULL)
    OR
    (input_kind = 'derived' AND core_dataset_id IS NULL AND derived_dataset_id IS NOT NULL)
  )
);

CREATE TABLE derived_dataset (
  derived_dataset_id         UUID PRIMARY KEY,
  transformation_run_id      UUID NOT NULL UNIQUE,
  run_status                 TEXT NOT NULL, -- succeeded
  physical_relation_schema   TEXT NULL,
  physical_relation_name     TEXT NOT NULL,
  physical_relation_key      TEXT NOT NULL UNIQUE,
  output_mode                TEXT NOT NULL, -- materialized | view
  row_count                  BIGINT NOT NULL,
  schema_hash                TEXT NOT NULL,
  content_hash               TEXT NOT NULL,
  content_hash_policy        TEXT NOT NULL, -- computed
  content_hash_kind          TEXT NOT NULL, -- relation_snapshot
  content_hash_algorithm     TEXT NOT NULL, -- sha256
  content_hash_version       TEXT NOT NULL, -- openstatspec-relation-snapshot-v1
  published_at               TIMESTAMP NOT NULL,
  CHECK (run_status = 'succeeded'),
  FOREIGN KEY (transformation_run_id, run_status)
    REFERENCES transformation_run(transformation_run_id, status)
);

-- Concrete DDL creates derived_dataset before adding this forward reference.
ALTER TABLE transformation_run_input
  ADD CONSTRAINT transformation_run_input_derived_fk
  FOREIGN KEY (derived_dataset_id) REFERENCES derived_dataset(derived_dataset_id);

CREATE TABLE derived_variable (
  derived_variable_id        UUID PRIMARY KEY,
  derived_dataset_id         UUID NOT NULL REFERENCES derived_dataset(derived_dataset_id),
  column_ordinal             INTEGER NOT NULL,
  physical_name              TEXT NOT NULL,
  logical_storage_kind       TEXT NOT NULL,
  is_nullable                BOOLEAN NOT NULL,
  variable_label             TEXT NULL,
  metadata_json              TEXT NULL,
  metadata_hash              TEXT NULL,
  lineage_kind               TEXT NOT NULL, -- identity | computed | aggregate | constant
  UNIQUE (derived_dataset_id, column_ordinal),
  UNIQUE (derived_dataset_id, physical_name)
);

CREATE TABLE derived_variable_lineage (
  derived_variable_id        UUID NOT NULL REFERENCES derived_variable(derived_variable_id),
  source_ordinal             INTEGER NOT NULL,
  transformation_run_id      UUID NOT NULL,
  input_ordinal              INTEGER NOT NULL,
  core_variable_id           UUID NULL REFERENCES variable(variable_id),
  parent_derived_variable_id UUID NULL REFERENCES derived_variable(derived_variable_id),
  expression_role            TEXT NOT NULL, -- identity | contributing | grouping | ordering
  PRIMARY KEY (derived_variable_id, source_ordinal),
  FOREIGN KEY (transformation_run_id, input_ordinal)
    REFERENCES transformation_run_input(transformation_run_id, input_ordinal),
  CHECK (
    (core_variable_id IS NOT NULL AND parent_derived_variable_id IS NULL)
    OR
    (core_variable_id IS NULL AND parent_derived_variable_id IS NOT NULL)
  )
);

CREATE TABLE derived_dataset_weight_variable (
  derived_dataset_id         UUID PRIMARY KEY REFERENCES derived_dataset(derived_dataset_id),
  derived_variable_id        UUID NOT NULL UNIQUE REFERENCES derived_variable(derived_variable_id),
  derivation_kind            TEXT NOT NULL, -- identity | computed
  meaning                    TEXT NULL
);


CREATE TABLE derived_dataset_disposition_event (
  disposition_event_id       UUID PRIMARY KEY,
  derived_dataset_id         UUID NOT NULL REFERENCES derived_dataset(derived_dataset_id),
  event_ordinal              INTEGER NOT NULL,
  event_kind                 TEXT NOT NULL, -- retired | physical_removal_requested | physical_removed
  actor_identity             TEXT NOT NULL,
  reason                     TEXT NOT NULL,
  prior_content_hash         TEXT NOT NULL,
  created_at                 TIMESTAMP NOT NULL,
  UNIQUE (derived_dataset_id, event_ordinal)
);

CREATE TABLE transformation_event (
  transformation_event_id    UUID PRIMARY KEY,
  transformation_run_id      UUID NOT NULL REFERENCES transformation_run(transformation_run_id),
  event_ordinal              INTEGER NOT NULL,
  severity                   TEXT NOT NULL, -- error | warning | info
  event_code                 TEXT NOT NULL,
  execution_phase            TEXT NOT NULL,
  safe_detail_json           TEXT NOT NULL,
  created_at                 TIMESTAMP NOT NULL,
  UNIQUE (transformation_run_id, event_ordinal)
);

-- Concrete dialect DDL additionally enforces enum domains, lowercase
-- 64-character SHA-256 values, contiguous ordinals, run-state transitions,
-- append-only publication/disposition events, same-dataset weight references,
-- lineage variables belonging to the selected run input, exact hash domains,
-- and state transitions beyond the logical composite keys above. A run with
-- recoverable quarantined staging remains started until the recorded,
-- profile-owned staging relation is absent; only then may it become failed.
