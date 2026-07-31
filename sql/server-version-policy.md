# SQL Server Version Policy

This document is normative for version claims made by the OpenStatSpec
reference adapters. The physical dialect requirements remain in
[Initial SQL Dialect Profiles](dialect-profiles.md). This policy was reviewed
against upstream primary sources on 2026-07-31.

## Claim and evidence model

A claimed release series is a conservative compatibility policy, not a claim
that every patch was exercised. A reference adapter MAY claim a listed series
only while its runtime preflight rejects every other series before catalog or
dataset mutation. CI evidence is narrower: the adapter MUST pin and publish the
exact patch version exercised by each service job. A floating major, minor or
`latest` container tag is not exact-version evidence.

When upstream publishes a later patch in a claimed series, the claim remains
valid under that vendor's patch-compatibility and maintenance policy, but the
adapter MUST continue to report the last exact patch it tested. Moving CI to a
new patch requires a new successful service run and an updated capability
declaration. Adding a release series requires specification review, runtime
preflight coverage and live conformance evidence.

## Reference-adapter matrix

| Engine | Claimed release series | Exact CI target on 2026-07-31 | Latest stable covered |
| --- | --- | --- | --- |
| MySQL | 8.4.x, 9.7.x | 8.4.11, 9.7.2 | 9.7.2 |
| MariaDB | 11.4.x, 11.8.x, 12.3.x | 11.4.12, 11.8.8, 12.3.2 | 12.3.2 |
| PostgreSQL | 17.x, 18.x | 17.10, 18.4 | 18.4 |

The retained older rows provide an actively exercised migration and
compatibility baseline. The newest row for each engine covers the latest GA or
stable release available on the review date. MySQL 26.7 is excluded because
upstream labels it Early Access rather than production GA.

The primary sources are the MySQL [8.4.11 release notes](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-11.html),
[9.7.2 release notes](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html)
and [release model](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html);
the MariaDB Foundation [release list](https://mariadb.org/mariadb/all-releases/)
and [maintenance policy](https://mariadb.org/about/#maintenance-policy); and
the PostgreSQL [current releases and versioning policy](https://www.postgresql.org/support/versioning/).
Exact container tags are independently resolved from the Docker Official
Images library definitions for [MySQL](https://github.com/docker-library/official-images/blob/master/library/mysql),
[MariaDB](https://github.com/docker-library/official-images/blob/master/library/mariadb)
and [PostgreSQL](https://github.com/docker-library/official-images/blob/master/library/postgres).

## Dolt and SQLite are unchanged

Dolt remains an independent, essential profile with an exact claim and exact
CI target of 2.2.2. Its MySQL-compatible transport does not place it in the
MySQL release-series policy, and none of its identity, evidence or cleanup
gates are weakened by this matrix.

SQLite is not a server-service row. The core adapter policy remains
`>=3.24.0,<4.0.0`. The Python-only optional SQL Transformation Workflow has a
separate `>=3.35.0,<4.0.0` requirement because it uses later SQLite features.
That narrower optional workflow does not change core SQLite conformance and
does not conflict with this server matrix.

## Unsupported engines

An engine absent from the matrix is unsupported unless it has its own
independent profile and evidence gate. In particular, Microsoft SQL Server is
roadmap-only; see the [MSSQL dialect roadmap](../docs/mssql-dialect-roadmap.md).
