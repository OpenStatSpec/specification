# Initial SQL Dialect Profiles

The compact, machine-readable baseline is
[`dialect-profile-baseline.json`](dialect-profile-baseline.json). It is a
conformance input, not a substitute for the server-specific declaration each
adapter must publish.

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

Catalog relations and the data table MUST be written in one transaction where
the dialect supports transactional DDL. On dialects where DDL is not
transactional, the importer MUST complete all preflight before DDL and remove
every object it created if a later write fails.

## SQLite profile

| Property | Requirement |
| --- | --- |
| Quoting | Double-quote identifiers; escape an embedded quote by doubling it. |
| Identifier limit | SQLite has no practical fixed identifier limit; the adapter MUST still impose and publish a deterministic application limit. |
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
| Identifier limit | 63 bytes by default. The adapter MUST preflight encoded identifier length after quoting policy is applied. |
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
| Identifier limit | 64 characters. The adapter MUST preflight generated names against the active server character set. |
| Maximum columns | 1,017 InnoDB columns, including `__case_ordinal`; the active engine may impose a lower limit. |
| Numeric | `DOUBLE`. |
| Text | `TEXT NOT NULL` where its row and index constraints are acceptable; a profile MAY use a lossless `VARCHAR(n)` only after preflighting every declared source width. |
| Primary key | `__case_ordinal BIGINT NOT NULL PRIMARY KEY`. |
| Row/value boundary | InnoDB row-size and LOB limits; the adapter MUST publish and preflight its effective boundary. |
| Atomicity | InnoDB DDL may cause implicit commits. Complete all preflight first and provide compensating cleanup for every created catalog/table object on failure. |

The profile applies only when all OpenStatSpec catalog and data tables use an
engine with the declared behavior. An adapter MUST reject a non-transactional
or incompatible storage configuration rather than claiming atomic import.

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
5. its catalog transaction/cleanup procedure for MySQL and MariaDB.
