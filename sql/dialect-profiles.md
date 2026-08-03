# Initial SQL Dialect Profiles

The compact, machine-readable baseline is
[`dialect-profile-baseline.json`](dialect-profile-baseline.json). It is a
conformance input, not a substitute for the server-specific declaration each
adapter must publish.

The normative [SQL Server Version Policy](server-version-policy.md) separately
defines the maintained MySQL, MariaDB and PostgreSQL release-series claims and
the exact patch versions required as reference-adapter CI evidence.

This document is normative for the first SQL profiles. It defines only the
physical choices necessary to create the single dedicated wide table required
by the SPSS profile. It does not introduce a second data shape, EAV/cells
storage, JSON value storage, table splitting, or reshaping.

An adapter MUST publish the selected profile, server version range, and any
stricter deployment limits. The limits below are defaults, not permission to
silently exceed an engine's actual configuration.

## Common contract

For one imported dataset, an adapter MUST create exactly one physical data
table. Its first column is `__case_ordinal`, a non-null primary key populated
from 1 in SPSS source case order. Each SPSS variable MUST map to exactly one
subsequent physical column in source variable order.

Numeric SPSS values use the listed binary64 type; SPSS numeric system-missing
uses SQL NULL. Dates, times and currencies remain that numeric type plus format
metadata. Strings use the listed variable-length text type, are NOT NULL for
SPSS system-missingness, and retain an empty string as a value.

Before any DDL or catalog write, an importer MUST perform preflight for column
count, generated identifiers, string/value limits, and declared row limits.
Failure MUST be atomic. It MUST not split or transpose the source dataset.

Physical variable names are dialect-specific. The catalog mapping from exact
SPSS source name to quoted physical name MUST be total, deterministic and
unique. Source names beginning with `__` are never used as physical names.

Identifier limits are dimensioned. An adapter MUST publish the limit as a
value plus an engine-native unit (`bytes` or `characters`), its discovery or
policy source, and the character repertoire or encoding used to measure it.
Preflight measures the final generated physical name after normalization and
before DDL. It MUST NOT reinterpret a character limit as a byte limit or vice
versa.

The catalog relation names in the logical schema outline are not unqualified
physical names. Every adapter MUST declare an exclusive catalog binding,
resolve all catalog access through it using qualified names or a fixed dedicated-connection context, verify the single `catalog_identity` marker before use or migration, and fail without modifying foreign objects. Schema-capable engines use a dedicated schema/database. SQLite uses a dedicated database file/connection; an attached database or declared reserved prefix is also permitted.

Catalog relations and the data table MUST be written in one transaction where
the dialect supports transactional DDL. On dialects where DDL is not
transactional, the importer MUST complete all preflight before DDL and remove
every object it created if a later write fails.

## SQLite profile

| Property | Requirement |
| --- | --- |
| Quoting | Double-quote identifiers; escape an embedded quote by doubling it. |
| Identifier limit | Baseline policy: 255 bytes over ASCII-safe generated names. An adapter MAY publish a stricter limit. SQLite has no separate engine identifier-length setting. |
| Catalog binding | Dedicated database file/connection; an attached database or declared reserved table prefix is also permitted. |
| Maximum columns | 2,000 under the default build. Treat this as an inclusive physical-table limit, including `__case_ordinal`. |
| Numeric | `REAL`; adapters MUST document any non-finite-value limitation. |
| Text | `TEXT NOT NULL` for SPSS strings. |
| Primary key | `__case_ordinal INTEGER NOT NULL PRIMARY KEY`. |
| Row/value boundary | SQLite's configured length limit and the host build's column limit; adapter preflight MUST publish the effective values. |
| Atomicity | Use an explicit transaction; DDL is transactional in normal SQLite operation. |

SQLite's dynamic type system does not relax the source-value contract. A
conforming SQLite adapter MUST retain the logical storage kind in metadata.

## PostgreSQL profile

| Property | Requirement |
| --- | --- |
| Quoting | Double-quote identifiers; escape an embedded quote by doubling it. |
| Identifier limit | 63 bytes by default, discovered from active `max_identifier_length`; measure the generated name in the active server encoding. |
| Catalog binding | Dedicated PostgreSQL schema; use schema-qualified names or a connection with a fixed single-schema `search_path`. |
| Maximum columns | 1,600, including `__case_ordinal`; a lower effective limit may arise from row-size constraints. |
| Numeric | `DOUBLE PRECISION`. |
| Text | `TEXT NOT NULL` for SPSS strings. |
| Primary key | `__case_ordinal BIGINT NOT NULL PRIMARY KEY`. |
| Row/value boundary | The server's tuple and field limits; preflight MUST reject a source known to exceed them. |
| Atomicity | Use one explicit transaction; PostgreSQL DDL is transactional. |

PostgreSQL folds unquoted names to lower case. A conforming adapter MUST quote
every generated physical identifier or document an equivalent deterministic
policy that cannot collide through folding.

## MySQL and MariaDB profile

| Property | Requirement |
| --- | --- |
| Quoting | Backtick-quote identifiers; escape an embedded backtick by doubling it. |
| Identifier limit | 64 Unicode BMP characters. This is a character limit, not a UTF-8 byte limit. |
| Catalog binding | Dedicated MySQL/MariaDB database; use qualified names or a connection fixed to that selected database. |
| Maximum columns | 1,017 InnoDB columns, including `__case_ordinal`; the active engine may impose a lower limit. |
| Numeric | `DOUBLE`. |
| Text | `TEXT NOT NULL` where its row and index constraints are acceptable; a profile MAY use a lossless `VARCHAR(n)` only after preflighting every declared source width. |
| Primary key | `__case_ordinal BIGINT NOT NULL PRIMARY KEY`. |
| Row/value boundary | InnoDB row-size and LOB limits; the adapter MUST publish and preflight its effective boundary. |
| Atomicity | InnoDB DDL may cause implicit commits. Complete all preflight first and provide compensating cleanup for every created catalog/table object on failure. |

The profile applies only when all OpenStatSpec catalog and data tables use an
engine with the declared behavior. An adapter MUST reject a non-transactional
or incompatible storage configuration rather than claiming atomic import.

## Dolt profile

Dolt is an independent profile. Its MySQL wire compatibility is a transport and
SQL-syntax property only; it MUST NOT cause an adapter to select the
MySQL/MariaDB/InnoDB profile or inherit an InnoDB column, row, LOB, DDL, or
cleanup rule.

The repository baseline is a `symbolic_template` with conformance status
`pending`. Its `claimed_product_versions` and `tested_product_versions` arrays
are empty because no live Dolt conformance run is represented here. The
template MUST NOT be used to import data. A concrete adapter declaration is a
separate full-profile artifact under
[`dolt-adapter-declarations/`](dolt-adapter-declarations/) conforming to
[`dolt-adapter-declaration-schema.json`](dolt-adapter-declaration-schema.json).
It replaces symbols with evidenced values and changes status to `tested`;
partial overrides are not declarations.

| Property | Requirement |
| --- | --- |
| Wire protocol | MySQL. Wire compatibility alone is not product identity. |
| Positive product identity | On the same connection, trim and case-fold `@@version_comment` and require it to equal `Dolt`; require a non-empty `DOLT_VERSION()`; then require that exact string to be a member of `tested_product_versions` with resolving product-identity evidence applicable to that version. A claimed-but-untested version rejects before mutation. |
| Supported versions | A concrete declaration publishes unique exact `claimed_product_versions` and unique exact `tested_product_versions`; tested versions are a non-empty subset of claimed versions. Versions MUST match the published canonical exact-version syntax, be trim-identical, and contain no ranges, wildcards, placeholders, or raw wire versions. |
| Quoting | Backtick-quote identifiers; escape an embedded backtick by doubling it. Every identifier limit requires exact-version evidence. |
| Catalog binding | Dedicated Dolt database on one explicitly selected branch and working set. Qualify names or fix the connection to that database for the entire operation, and verify `catalog_identity` before import. |
| Numeric | `DOUBLE`. Finite supported values preserve their binary64 bit patterns. NaN and positive/negative infinity use the declared per-class policy. |
| Text | `LONGTEXT NOT NULL` for SPSS strings. No InnoDB inline-row or LOB assumption applies. |
| Primary key | `__case_ordinal BIGINT NOT NULL PRIMARY KEY`. |
| DDL atomicity | A machine-readable `ddl_atomicity` case records `atomic` or `non_atomic` behavior with exact-product-version evidence. The symbolic template remains pending and has no result. A Dolt repository commit is not an SQL transaction or cleanup boundary. |
| Version-control actions | Import MUST NOT branch, merge, commit, reset, checkout, or otherwise mutate Dolt version-control state. Any such workflow is a separate namespaced extension. |

Catalog installation and migration are separate explicit operations. Import may
start only after positive product identity, active-version membership, database
binding, and `catalog_identity` ownership have all been verified. Before that
boundary, an absent, foreign, or ambiguous catalog permits zero database or
Dolt-working-set mutations; diagnostics are out of band.

After verification, a capability preflight failure MUST persist the failed
`operation` row and its `target_capability_exceeded` `fidelity_event` whose
`dataset_id` is NULL. It creates no dataset row or physical data table. Other
failures restore the verified catalog and working set to the captured
pre-operation state, except for core audit rows explicitly permitted here.

### Dolt versioned declaration and limits

The symbolic template defines the required shape without claiming live facts.
Its layer values use only `N_plus_1`, `N`, `L`, `V`, `R`, and `S`; template
`exact_versions` arrays are empty. Placeholder product versions are forbidden.

A concrete adapter declaration MUST bind a unique canonical
`declaration_id`, stable `adapter_implementation_id`, exact canonical
`adapter_version`, exact lowercase 40-hex `specification_commit`, and unique
canonical `conformance_run_id`. Before any mutation, the adapter MUST find
exactly one concrete declaration matching the active `DOLT_VERSION()` and
those adapter/specification bindings; zero or multiple matches reject.

A concrete adapter declaration MUST:

1. publish non-empty unique canonical exact claimed and tested product-version arrays,
   with `tested_product_versions` a subset of `claimed_product_versions`, and
   bind the active product version to resolving applicable evidence;
2. bind every applicable limit layer and every conformance case to non-empty
   exact-version evidence that is a subset of `tested_product_versions`;
3. use positive integer values for every non-structural limit and calculate
   `effective` as the numeric minimum of applicable non-effective layers;
4. for every basis, declare physical columns as source variables plus one; and
5. represent a structural-row limit as a positive integer or select the single
   discriminated `not_applicable_proof` variant with reason, inspected
   structures, evidence ID, and exact versions.

The limit map is keyed by `physical_columns`, `source_variables`, `identifier`,
`value`, `structural_row`, and `emitted_statement`. Each value is an array with
one record for each basis: `theoretical_engine`, `live_observed_server`,
`active_configuration`, `adapter_policy`, `adapter_envelope`, and `effective`.
Every record has `value`, `unit`, `scope`, `basis`, `evidence`,
`exact_versions`, and `applicable`. A concrete declaration uses only canonical
units, contains no template evidence identifiers, and resolves every evidence
ID through its top-level `evidence_records`. Each applicable limit value is
machine-linked to a `limit` evidence record. The concrete `identifier_limit`
value and unit MUST equal the effective identifier limit `L`. Concrete L, V, and
numeric-R boundary-case units MUST be the matching effective units, never the
symbolic `declared_*_unit` markers. Every exact version claimed for an
applicable layer is covered by evidence for that same measurement and value.
Evidence artifact paths are canonical repository-relative paths under
`sql/dolt-adapter-declarations/evidence/`; a lowercase SHA-256 is verified
against the existing file, with absolute paths, `..`, and symlink escapes
rejected.

`physical_columns` includes `__case_ordinal`; `source_variables` does not. A
concrete adapter accepts `N` source variables as `N + 1` physical columns and
rejects `N + 1` source variables as `N + 2` physical columns.
`emitted_statement` limits one encoded SQL statement or batch, not total
dataset bytes. Larger datasets conform when split into atomic batches within
the statement limit. No symbolic value is a Dolt server maximum.

### Dolt boundary and fault conformance

Every case record declares a unique ID, measurement, measured value, unit,
expected result, observed result, evidence ID, and exact product versions. The
pending template uses NULL evidence IDs and empty version arrays. A concrete
tested declaration uses non-empty evidence IDs and version arrays drawn only
from `tested_product_versions`; every ID resolves to a typed evidence object
whose measurement, observed value, and exact versions cover the case.
Measured values are machine-checked against effective `L`, `N`, `V`, `S`, and
the selected numeric `R`, including each minus-one/at/plus-one boundary and the
fixed 65,535/65,536-byte probes.

The matrix requires:

1. `L - 1` and `L` identifier acceptance and round trip; `L + 1` rejection
   before mutation; declared-unit proof with multibyte input; escaped embedded
   backticks; quoted reserved words; safe handling of the reserved `__` prefix;
   and distinct round-tripping physical names after truncation, case-fold, and
   active-collation collisions;
2. acceptance at source `N` and physical `N + 1`, and rejection before mutation
   at source `N + 1` and physical `N + 2`;
3. introspected `LONGTEXT NOT NULL`; empty and UTF-8 byte-exact round trips;
   rejected SQL NULL; successful encoded 65,535- and 65,536-byte probes;
   acceptance at `V - 1` and `V`, and rejection before mutation at `V + 1`;
4. bit-exact round trips for signed zero, subnormal boundaries, the minimum
   normal, maximum finite, and representative ordinary finite values; semantic
   SPSS system-missing round trip through SQL NULL; and an explicit policy for
   each of NaN, positive infinity, and negative infinity. This template selects
   rejection before mutation for all three exceptional classes, so they cannot
   collide with the SQL-NULL system-missing representation;
5. exactly one structural-row variant in a concrete declaration: numeric
   `R - 1`/`R` acceptance with `R + 1` rejection, or the structured
   version-specific not-applicable proof;
6. statement acceptance at `S - 1` and `S`; reject or split before emitting
   `S + 1`; and accept a multi-batch dataset only when each batch is at most
   `S`; and
7. a machine-readable, uniquely identified fault-injection inventory covering
   every catalog/data DDL/DML mutation and compensating cleanup, with each
   fault case linked to the covered inventory IDs, expected operation status,
   residual state, diagnostic code, and complete post-failure inventory.

After cleanup failure, the adapter MUST reverify catalog identity before any
audit write. Core `operation.status` remains `failed`; `cleanup_failed` is a
stable diagnostic code, not an operation status. Only when reverification still
proves the catalog verified does the adapter write an error `fidelity_event`
whose machine-readable details contain `original_cause`, `cleanup_fault`,
`residual_object_inventory`, and `deterministic_recovery_evidence`. If
reverification is unverified or ambiguous, the same code and details are
emitted out of band and no further mutation is permitted. Cleanup failure can
never be reported as success. Verification covers catalog relations, the
physical table, residual objects, Dolt status/diff, branch, and commit head.

## Required indexes

The wide data table MUST have the primary-key index on `__case_ordinal`.
No index on a source variable is required by this specification. Catalog
implementations MUST enforce unique source ordinals and unique physical names
within a dataset. Additional indexes are implementation choices and MUST NOT
alter the one-table mapping.

## Adapter decision points

Each adapter needs to decide and declare:

1. the exact server versions and effective limits it supports;
2. its deterministic source-name-to-physical-name algorithm;
3. whether it supports non-finite SPSS binary64 values in each dialect;
4. its tested text encoding and maximum value/row limits;
5. its catalog transaction/cleanup procedure for MySQL, MariaDB and Dolt; and
6. its catalog binding, physical relation mapping, and ownership check.
