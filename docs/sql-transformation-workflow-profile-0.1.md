# OpenStatSpec SQL Transformation Workflow Profile 0.1

## Status and scope

This document defines an optional workflow profile layered beside the
source-faithful OpenStatSpec core. The key words **MUST**, **MUST NOT**,
**SHOULD**, **SHOULD NOT**, and **MAY** are normative.

Implementing this profile does not change core conformance. A core `dataset`
row and its dedicated wide table remain an immutable, source-faithful import.
A derived result is registered only in this profile's catalog; it MUST NOT be
inserted into the core `dataset` relation, presented as an imported source, or
exported through a source-package profile unless a separate export profile
permits that conversion.

The profile covers deterministic SQL transformations whose result is one
rectangular relation. It does not define an analysis language, scheduler,
credential store, arbitrary SQL migration runner, or harmonization standard.

## Conformance identity and isolation

The profile contract identifier is
`openstatspec-sql-transformation-workflow-v0.1`. Its logical relations are in
[`../sql/transformation-workflow-profile-schema.sql`](../sql/transformation-workflow-profile-schema.sql).
They MUST occupy a declared exclusive namespace. An implementation MUST verify
both core `catalog_identity` and `transformation_profile_identity` before use.

Profile conformance requires a conformant core catalog but is claimed and
versioned independently. Implementations MUST publish the exact specification
commit, profile version, database engine/version, dialect profile, and declared
capability limits used by every execution.

## Immutable objects

Core source datasets and tables, published transformation versions, started
run inputs and parameters, published derived datasets and their relations,
metadata, lineage, hashes, and events are append-only. Corrections create a new
transformation version and derived dataset. This profile has no mutable
`retired_at` field. Retirement and physical removal append ordered
`derived_dataset_disposition_event` records. Removal first appends
`physical_removal_requested` with actor, reason, time, and prior content hash;
only then may the relation be removed. Successful deletion appends
`physical_removed`. A crash reconciler MUST resume or safely reverse every
request lacking a terminal event before further garbage collection. The
immutable derived-dataset row and prior disposition history remain.
Definition/version deletion and mutation are outside v0.1.

## Definitions, SQL, and versions

A `transformation_definition` supplies stable human identity. Every immutable
`transformation_version` MUST contain:

1. a positive version unique within the definition;
2. exactly one SQL query, optionally beginning with CTEs, whose outer statement
   is `SELECT`;
3. a dialect family and server-version constraint;
4. output mode `materialized` or `view`;
5. row semantics and metadata policy;
6. a canonical ordered expected-output schema;
7. a complete ordered parameter declaration; and
8. a `definition_hash`.

`output_schema_json` MUST be an RFC 8785 canonical object with `variables` and
`weight` members. `variables` is a non-empty array ordered by contiguous
`column_ordinal`; every descriptor contains `physical_name`,
`logical_storage_kind`, `is_nullable`, `lineage_kind`, `lineage`, and
`metadata`. `lineage` is an ordered array of input alias, parent column, and
expression-role descriptors. `metadata` is a canonical object or NULL. `weight`
is NULL or identifies an output physical name, derivation kind (`identity` or
`computed`), and documented meaning. Implementations MAY add namespaced
descriptor members, which then participate in `definition_hash`.

The expected schema is validated against the database result before
publication. Runtime-generated IDs and physical relation names are excluded;
column descriptors, lineage assertions, metadata, nullability, and weight
designation are included.

`deterministic_order_json` is an RFC 8785 array of outer-query order items.
Each item stores the parsed expression, `ASC` or `DESC`, explicit NULL ordering,
and collation. `collation` MUST be NULL exactly when the expression's logical
storage kind is non-collatable. A textual expression MUST name a fixed dialect
collation and the outer SQL AST MUST explicitly apply it; a session/database
default is insufficient. The dialect AST of the outer `ORDER BY` MUST match
this array.
Before publication the executor evaluates the complete order tuple for every
row and MUST reject duplicate tuples with `non_unique_order_key`; declaring a
key unique is insufficient. View creation performs the same check, and its
immutable inputs preserve that result. Session collation, timezone, and other
result-affecting settings are fixed and recorded in the capability snapshot.

The query MUST NOT contain DDL, DML, transaction/session control, dynamic SQL,
external I/O, or volatile calls. The executor, not the query, creates and
publishes the staging table/view. Input identifiers resolve from declared
aliases (the single-parent shorthand alias is `parent`). Parameters MUST NOT
be used as identifiers.

SQL is versioned exactly after CRLF and CR are converted to LF and the result is
UTF-8 encoded. The stored `query_sql` MUST already equal that LF-normalized
value before hashing. Implementations MUST NOT infer equivalence by formatting
or regenerating SQL.

### Parameters

Named parameters MUST be bound through the database driver; text substitution
is forbidden. Each declares ordinal, name, logical type, nullability, optional
canonical JSON default, and sensitivity. Types are `boolean`, `integer`,
`decimal`, `binary64`, `string`, `date`, `timestamp`, `uuid`, and `json`.

A run stores a typed canonical value and hash for each binding. Sensitive
values MUST be encrypted at rest or represented by a stable secret reference
plus non-reversible keyed fingerprint. They MUST NOT occur in SQL, logs,
events, or plaintext catalog fields. Database credentials are environment
secrets, never transformation parameters.

A persistent `view` version MUST have zero parameters. Parameterized versions
MUST be materialized because bound values cannot remain bound in a view.

## Inputs and lineage

Run inputs are ordered and uniquely aliased. Each identifies either a core
dataset or a published derived dataset by UUID. Exactly one input kind is set.
The run stores relation identity, schema hash, snapshot hash kind, algorithm,
version, and value. Missing, unpublished, changed, or cyclic inputs MUST be
rejected; the derived lineage graph is a DAG.

The query may read only declared input aliases. Lookup relations are forbidden
in v0.1, including immutable lookups. Undeclared catalogs, user temporaries,
mutable application tables, network tables, table-valued external-I/O
functions, and extension relations are forbidden.

Every output variable has zero or more lineage entries. Identity passthrough
identifies the exact parent variable. Computed/aggregate output identifies all
known contributors. Zero-parent output is allowed only for constants or
execution metadata and MUST be marked as such. Allowed `lineage_kind` values are
`identity`, `computed`, `aggregate`, and `constant`. Allowed
`expression_role` values are `identity`, `contributing`, `grouping`, and
`ordering`; the two enums are distinct and other values are invalid.

Every non-constant lineage row MUST reference an `input_ordinal` belonging to
the producing run. Its core or derived parent variable MUST belong to the UUID
selected by that exact run input. Concrete DDL MUST enforce this with composite
keys/triggers, or publication validation MUST prove it in the same transaction.
Cross-input or cross-run variable references are invalid.

## Output relation

A successful run publishes exactly one relation and one `derived_dataset`.
Column names and order are explicit and unique; `__` is reserved.

Materialized output MUST have `__row_ordinal BIGINT NOT NULL PRIMARY KEY`,
contiguous from one in deterministic query order. The query MUST define a total
order; incidental row order is non-conformant. A view MUST expose an equivalent
deterministic, unique, non-null ordinal and reference immutable inputs only.
Its name resolution and definition are immutable.

Every published relation has a NOT NULL, UNIQUE `physical_relation_key`: the
dialect family plus the engine-native, fully qualified and quoted relation
identity, including database/attachment identity where applicable. This key,
not a nullable `(schema, name)` uniqueness constraint, prevents collisions.

The catalog records every user column's ordinal, physical name, logical storage
kind, nullability, and optional label. Derived data is not required to retain
source-package naming or storage restrictions.

## Metadata and weight propagation

Propagation is explicit and conservative:

- `none` copies no source metadata.
- `identity_only` may copy labels, value labels, missing rules, formats,
  measurement level, and role only for a value-preserving passthrough.
- `declared` defines output metadata independently with cited provenance and
  MUST NOT claim identity for recoded, cast, aggregated, or changed values.

Unknown metadata is omitted, never guessed. Conflicts MUST fail validation or
be resolved by a declared rule.

An input weight propagates automatically only when row semantics are
`one_to_one` or `filter`, exactly one input weight is passed unchanged, no join,
duplication, aggregation, imputation, or rescaling changes its interpretation,
and output weight lineage is `identity`. Otherwise there is no weight unless a
declared output variable is designated `computed` with documented meaning.
Allowed row semantics are `one_to_one`, `filter`, `aggregate`, `join`,
`reshape`, and `other`.

## Hashes

Hashes use SHA-256 lowercase hex. JSON uses RFC 8785 canonicalization over a
strict profile domain: valid Unicode scalar strings, objects with string keys,
arrays, booleans, NULL, and integers from -9007199254740991 through
9007199254740991. Object keys sort by UTF-16 code units. Raw fractional or
out-of-range JSON numbers and unpaired surrogates are forbidden in hash
payloads; binary64 and decimal values use typed canonical string envelopes.
This restricted serialization is exactly RFC 8785, not an approximation.

- `definition_hash` hashes the exact canonical object containing contract,
  `transformation_id`, positive `version_number`, LF-normalized `query_sql`,
  dialect constraint, output/row/metadata policy, canonical expected-output
  schema, deterministic order declaration, and ordered parameter declarations;
- `parameters_hash` hashes `{"hash_kind":"parameter_set",
  "hash_version":"openstatspec-parameter-set-v1","parameters":[...]}` where
  each ordered entry contains ordinal, name, logical type, and typed value;
- `input_set_hash` hashes `{"hash_kind":"input_set",
  "hash_version":"openstatspec-input-set-v1","inputs":[...]}` where each
  ordered entry contains input ordinal, `input_alias`, input kind, UUID,
  relation key, schema hash, and snapshot hash kind/algorithm/version/value;
- `schema_hash` covers ordered output descriptors, weight, and metadata hashes;
- `content_hash` covers materialized output when a named/versioned canonical
  row-hash algorithm is declared.

The canonical relation snapshot uses `hash_kind = relation_snapshot`,
`hash_algorithm = sha256`, and
`hash_version = openstatspec-relation-snapshot-v1`. Rows are ordered by the
verified unique technical ordinal (`__case_ordinal` or `__row_ordinal`). The
hashed RFC 8785 envelope contains the hash kind/version, `schema_hash`, and all
rows. Every row begins with its ordinal as `{"t":"i","v":"<decimal>"}`;
remaining values are `{"t":"null"}`, binary64 IEEE-754 bits as exactly 16
lowercase hex digits in `{"t":"f64","v":"..."}`, or an exact, unnormalized
Unicode string in `{"t":"s","v":"..."}`. v0.1 derived storage kinds are
therefore `numeric` and `string`; later profiles may add typed envelopes.

The snapshot value is SHA-256 of the envelope's UTF-8 RFC 8785 bytes. Schema
hashing uses the same algorithm over the canonical ordered descriptor object.
Source-file hashes are provenance only and MUST NOT replace a relation snapshot.
Materialized derived outputs MUST compute this content hash. A view records the
same hash at publication plus its immutable-input hashes; `not_computed` is not
a conformant published output in v0.1.

Input snapshot calculation, query execution, validation, and publication MUST
share one database snapshot. Inputs are write-protected by ownership/privileges
and, where needed, engine locks for the whole run. If the engine cannot prevent
concurrent input changes and provide a repeatable snapshot, execution fails
with `input_not_immutable`; a before/after hash outside one snapshot is not an
acceptable substitute.

## Execution, audit, and atomicity

A run is inserted as `started` before execution and records executor,
engine/dialect capability snapshot, immutable specification commit, hashes,
timestamps, and correlation ID. It transitions once to `succeeded` or `failed`.
Events are append-only, machine-readable, and safe for logs. Stable error codes
include `definition_hash_mismatch`, `dialect_not_supported`,
`parameter_invalid`, `input_not_immutable`, `input_hash_mismatch`,
`undeclared_relation_access`, `unsafe_sql`, `volatile_sql`,
`external_io_forbidden`, `non_unique_order_key`, `target_capability_exceeded`,
`output_validation_failed`, `publication_failed`, and `cleanup_failed`.

Before execution, validate definition, bindings, inputs, privileges, dialect,
expected shape, and capacity. Execute into an unpredictable profile-owned
staging relation, validate, hash, then atomically publish relation and catalog.
Transactional engines MUST perform staging through run success in one
transaction. Engines with implicit DDL commits MUST use documented atomic
rename/catalog-pointer publication plus compensating cleanup.

Failure retains the run/events but MUST leave no derived-dataset row, published
output name, or staging object. Cleanup failure is audited and cannot be
reported as success. Crash recovery MUST reconcile `started` runs and only
profile-owned staging objects.

## Dialect and security boundary

Each version targets exactly one declared dialect family and server constraint;
no portability is inferred. Execution uses fixed qualification and least
privilege: read only declared inputs, write only profile staging/output and
audit catalogs. Caller-controlled search paths/default databases are forbidden.
A dialect-aware AST parser MUST prove one outer `SELECT`, exact declared
relations, declared parameter nodes, matching outer order items, and absence of
DDL/DML/session/transaction, volatile, external-I/O, extension, and dynamic-SQL
nodes. In addition, the database MUST enforce an authorizer or equivalent
least-privilege role that can read only resolved inputs and write only owned
staging/output/audit objects. Neither AST validation nor authorization alone is
sufficient; regex filtering is never sufficient.

Authoring, approval, execution, and output-read roles SHOULD be separately
auditable. Logs MUST redact secrets and SHOULD avoid row values. Limits MUST
cover time, rows, bytes, temporary storage, and concurrency.

## Validation and conformance

Before publication, a conformant adapter validates:

1. identities and hashes recompute;
2. dialect/server constraints match;
3. bindings are complete, typed, and driver-bound;
4. inputs are write-protected, snapshot-hashed in the run transaction, and acyclic;
5. AST and database authorization restrict SQL to declared input aliases;
6. outer order declaration matches the AST and evaluated tuples are unique;
7. output names, ordinals, types, nullability, and row ordinals are valid;
8. metadata, lineage/input consistency, and weight rules hold; and
9. atomic publication completed.

Machine-readable cases are in
[`../conformance/sql-transformation-workflow-0.1.json`](../conformance/sql-transformation-workflow-0.1.json).
Claims identify passing cases and MUST NOT infer untested dialect, output mode,
parameter type, or hash-policy support.
