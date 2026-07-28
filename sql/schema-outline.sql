-- OpenStatSpec SPSS SAV/ZSAV Profile 1.0: normative logical schema outline
-- Concrete profiles select exact SQL types and quoting rules.

CREATE TABLE dataset (
  dataset_id              UUID PRIMARY KEY,
  spec_version            TEXT NOT NULL,
  source_format           TEXT NOT NULL,
  physical_table_schema   TEXT NULL,
  physical_table_name     TEXT NOT NULL,
  dataset_name            TEXT NULL,
  dataset_label           TEXT NULL,
  source_encoding         TEXT NULL,
  source_hash             TEXT NULL,
  source_case_count       BIGINT NOT NULL,
  imported_at             TIMESTAMP NOT NULL
);

-- An operation exists before a dataset can exist. It records preflight
-- failures as well as completed imports and exports.
CREATE TABLE operation (
  operation_id            UUID PRIMARY KEY,
  operation_kind          TEXT NOT NULL, -- import | export
  status                  TEXT NOT NULL, -- started | succeeded | failed
  source_format           TEXT NULL,
  started_at              TIMESTAMP NOT NULL,
  completed_at            TIMESTAMP NULL
);

CREATE TABLE variable (
  variable_id             UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES dataset(dataset_id),
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

CREATE TABLE dataset_weight_variable (
  dataset_id              UUID PRIMARY KEY REFERENCES dataset(dataset_id),
  variable_id             UUID NOT NULL UNIQUE REFERENCES variable(variable_id)
);

CREATE TABLE value_label_set (
  value_label_set_id      UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES dataset(dataset_id),
  name                    TEXT NULL
);

CREATE TABLE value_label (
  value_label_id          UUID PRIMARY KEY,
  value_label_set_id      UUID NOT NULL REFERENCES value_label_set(value_label_set_id),
  ordinal                 INTEGER NOT NULL,
  code_kind               TEXT NOT NULL, -- numeric | string
  numeric_code            DOUBLE PRECISION NULL,
  string_code             TEXT NULL,
  label                   TEXT NOT NULL,
  UNIQUE (value_label_set_id, ordinal)
);

CREATE TABLE variable_value_label_set (
  variable_id             UUID PRIMARY KEY REFERENCES variable(variable_id),
  value_label_set_id      UUID NOT NULL REFERENCES value_label_set(value_label_set_id)
);

CREATE TABLE missing_rule (
  missing_rule_id         UUID PRIMARY KEY,
  variable_id             UUID NOT NULL REFERENCES variable(variable_id),
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

CREATE TABLE dataset_attribute (
  dataset_attribute_id    UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES dataset(dataset_id),
  attribute_name          TEXT NOT NULL,
  array_ordinal           INTEGER NOT NULL DEFAULT 1,
  attribute_value         TEXT NOT NULL,
  UNIQUE (dataset_id, attribute_name, array_ordinal)
);

CREATE TABLE variable_attribute (
  variable_attribute_id   UUID PRIMARY KEY,
  variable_id             UUID NOT NULL REFERENCES variable(variable_id),
  attribute_name          TEXT NOT NULL,
  array_ordinal           INTEGER NOT NULL DEFAULT 1,
  attribute_value         TEXT NOT NULL,
  UNIQUE (variable_id, attribute_name, array_ordinal)
);

CREATE TABLE document (
  document_id             UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES dataset(dataset_id),
  source_ordinal          INTEGER NOT NULL,
  document_text           TEXT NOT NULL,
  UNIQUE (dataset_id, source_ordinal)
);

CREATE TABLE variable_set (
  variable_set_id         UUID PRIMARY KEY,
  dataset_id              UUID NOT NULL REFERENCES dataset(dataset_id),
  set_name                TEXT NOT NULL,
  UNIQUE (dataset_id, set_name)
);

CREATE TABLE variable_set_member (
  variable_set_id         UUID NOT NULL REFERENCES variable_set(variable_set_id),
  variable_id             UUID NOT NULL REFERENCES variable(variable_id),
  source_ordinal          INTEGER NOT NULL,
  PRIMARY KEY (variable_set_id, source_ordinal),
  UNIQUE (variable_set_id, variable_id)
);

CREATE TABLE multiple_response_set (
  multiple_response_set_id UUID PRIMARY KEY,
  dataset_id               UUID NOT NULL REFERENCES dataset(dataset_id),
  set_name                 TEXT NOT NULL,
  set_label                TEXT NULL,
  set_kind                 TEXT NOT NULL, -- MD | MC
  counted_value_kind       TEXT NULL,     -- numeric | string for MD
  counted_numeric_value    DOUBLE PRECISION NULL,
  counted_string_value     TEXT NULL,
  category_label_behavior  TEXT NULL,
  label_source             TEXT NULL,
  UNIQUE (dataset_id, set_name)
);

CREATE TABLE multiple_response_member (
  multiple_response_set_id UUID NOT NULL REFERENCES multiple_response_set(multiple_response_set_id),
  variable_id              UUID NOT NULL REFERENCES variable(variable_id),
  source_ordinal           INTEGER NOT NULL,
  PRIMARY KEY (multiple_response_set_id, source_ordinal),
  UNIQUE (multiple_response_set_id, variable_id)
);

CREATE TABLE fidelity_event (
  fidelity_event_id       UUID PRIMARY KEY,
  operation_id            UUID NOT NULL REFERENCES operation(operation_id),
  dataset_id              UUID NULL REFERENCES dataset(dataset_id),
  direction               TEXT NOT NULL, -- import | export
  severity                TEXT NOT NULL, -- error | warning
  event_code              TEXT NOT NULL,
  source_item             TEXT NULL,
  detail_json             TEXT NOT NULL,
  created_at              TIMESTAMP NOT NULL
);

-- Each imported dataset also has exactly one physical table, for example:
-- CREATE TABLE data_<dataset-specific-identifier> (
--   __case_ordinal BIGINT NOT NULL PRIMARY KEY,
--   <one physical column for every source SPSS variable, in source order>
-- );
