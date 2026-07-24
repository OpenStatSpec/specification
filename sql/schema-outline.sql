-- OpenStatSpec: dialect-neutral schema outline (draft)
-- Concrete profiles select exact SQL types and quoting rules.

CREATE TABLE oss_dataset (
  dataset_id              UUID PRIMARY KEY,
  spec_version            TEXT NOT NULL,
  source_format           TEXT NOT NULL,
  source_table_schema     TEXT NULL,
  source_table_name       TEXT NOT NULL,
  dataset_name            TEXT NULL,
  dataset_label           TEXT NULL,
  source_encoding         TEXT NULL,
  source_hash             TEXT NULL,
  source_case_count       BIGINT NOT NULL,
  imported_at             TIMESTAMP NOT NULL
);

CREATE TABLE oss_variable (
  variable_id             UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES oss_dataset(dataset_id),
  source_ordinal          INTEGER NOT NULL,
  source_name             TEXT NOT NULL,
  physical_name           TEXT NOT NULL,
  storage_kind            TEXT NOT NULL, -- numeric | string
  declared_string_width   INTEGER NULL,
  variable_label          TEXT NULL,
  print_format_family     TEXT NULL,
  print_format_width      INTEGER NULL,
  print_format_decimals   INTEGER NULL,
  write_format_family     TEXT NULL,
  write_format_width      INTEGER NULL,
  write_format_decimals   INTEGER NULL,
  measurement_level       TEXT NULL,
  variable_role           TEXT NULL,
  display_width           INTEGER NULL,
  display_alignment       TEXT NULL,
  UNIQUE (dataset_id, source_ordinal),
  UNIQUE (dataset_id, source_name),
  UNIQUE (dataset_id, physical_name)
);

CREATE TABLE oss_value_label_set (
  value_label_set_id      UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES oss_dataset(dataset_id),
  name                    TEXT NULL
);

CREATE TABLE oss_value_label (
  value_label_id          UUID PRIMARY KEY,
  value_label_set_id      UUID NOT NULL REFERENCES oss_value_label_set(value_label_set_id),
  ordinal                 INTEGER NOT NULL,
  code_kind               TEXT NOT NULL, -- numeric | string
  numeric_code            DOUBLE PRECISION NULL,
  string_code             TEXT NULL,
  label                   TEXT NOT NULL,
  UNIQUE (value_label_set_id, ordinal)
);

CREATE TABLE oss_variable_value_label_set (
  variable_id             UUID PRIMARY KEY REFERENCES oss_variable(variable_id),
  value_label_set_id      UUID NOT NULL REFERENCES oss_value_label_set(value_label_set_id)
);

CREATE TABLE oss_missing_rule (
  missing_rule_id         UUID PRIMARY KEY,
  variable_id             UUID NOT NULL REFERENCES oss_variable(variable_id),
  ordinal                 INTEGER NOT NULL,
  rule_kind               TEXT NOT NULL, -- discrete | numeric_range
  code_kind               TEXT NULL,     -- numeric | string for discrete
  numeric_value           DOUBLE PRECISION NULL,
  string_value            TEXT NULL,
  numeric_lower           DOUBLE PRECISION NULL,
  numeric_upper           DOUBLE PRECISION NULL,
  lower_special           TEXT NULL,     -- LOWEST when applicable
  upper_special           TEXT NULL,     -- HIGHEST when applicable
  UNIQUE (variable_id, ordinal)
);

CREATE TABLE oss_fidelity_event (
  fidelity_event_id       UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES oss_dataset(dataset_id),
  direction               TEXT NOT NULL, -- import | export
  severity                TEXT NOT NULL, -- error | warning
  event_code              TEXT NOT NULL,
  source_item             TEXT NULL,
  detail_json             TEXT NOT NULL,
  created_at              TIMESTAMP NOT NULL
);

-- Each imported dataset also has exactly one physical table, for example:
-- CREATE TABLE oss_data_<dataset-specific-identifier> (
--   _oss_case_ordinal BIGINT NOT NULL PRIMARY KEY,
--   <one physical column for every source SPSS variable, in source order>
-- );
