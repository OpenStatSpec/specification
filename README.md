# OpenStatSpec

OpenStatSpec is an open, SQL-oriented specification for representing a statistical data file and its dictionary metadata in a relational database without changing the source package's rectangular data model.

The first profile targets IBM SPSS Statistics system files. It maps one source dataset to one dedicated wide SQL table: each source case becomes one row and each source variable becomes one physical column. Supporting catalog tables retain only the metadata needed to interpret and export that SPSS dataset faithfully.

## Conformance scope

The [SPSS SAV/ZSAV profile](docs/spss-sav-zsav-profile-1.0.md) defines normative conformance language, a canonical relational schema, generated fixtures, and reference-adapter coverage. The SQL layer includes independent SQLite, PostgreSQL, MySQL/MariaDB/InnoDB, and Dolt profiles. Implementations must pin the exact specification commit they test against. Release identifiers and immutable provenance belong in tagged releases and capability declarations rather than in this README.

The [server-version policy](sql/server-version-policy.md) covers the maintained
MySQL 8.4.x/9.7.x, MariaDB 11.4.x/11.8.x/12.3.x and PostgreSQL 17.x/18.x
series while requiring exact patch-version CI evidence. Microsoft SQL Server
remains an explicitly unsupported [future dialect](docs/mssql-dialect-roadmap.md).

## Core contract

- One source dataset maps to exactly one dedicated SQL data table.
- One SPSS case maps to exactly one row, in source order.
- One SPSS variable maps to exactly one physical SQL column, in source order.
- The table contains a reserved technical ordinal column, `__case_ordinal`, used only to preserve case order. It is never exported as an SPSS variable.
- Numeric system-missing values map to SQL `NULL`; SPSS user-missing codes remain their original stored values and are described in metadata.
- Dates, times, and currencies remain SPSS numeric values plus SPSS format metadata.
- String blanks remain values, not missing values.

OpenStatSpec does not define long-form cells, EAV storage, table splitting, reshaping, automatic harmonization, or questionnaire/study entities. It does not infer respondent keys or combine datasets. All conformant database-object identifiers are generic; the double-underscore prefix is reserved for standard technical identifiers.

[Versioning](VERSIONING.md) defines compatibility and release rules. [Releasing](RELEASING.md) defines the maintainer release checklist. [Roadmap](ROADMAP.md) tracks remaining project work and maintainer setup.

## Optional SQL transformation workflow

The [SQL Transformation Workflow Profile 0.1](docs/sql-transformation-workflow-profile-0.1.md)
adds versioned, parameterized and auditable SQL-derived datasets beside the core.
It never reclassifies derived output as a source-faithful core dataset and never
permits a transformation to mutate a core import.

That separate derived-data profile is not used by the SPSS-like in-place
frontend below.

The release-candidate [Transformation Plan Profile 0.2](docs/transformation-plan-profile-0.2.md)
adds sequential bounded numeric assignment and conditional assignment to the
unchanged 0.1 operations. The
[SPSS Syntax Frontend Profile 0.2](docs/spss-syntax-frontend-profile-0.2.md)
lowers `COMPUTE`, `IF`, `FORMATS`, `VARIABLE LEVEL`, and `EXECUTE`
alongside the 0.1 `RECODE`, `VARIABLE LABELS`, and `VALUE LABELS` subset.
Programs using only the 0.1 subset retain exact 0.1 plan identity and hash. The
[in-place binding](docs/transformation-plan-sql-binding-0.2.md) applies the plan
to the same dataset and same physical wide table on supported SQL profiles. It
creates no derived dataset, data copy, or OpenStatSpec undo layer; Dolt-specific
history and commits remain Dolt's. MySQL, MariaDB, and Dolt require a new target
to be provisioned separately before an in-place transformation apply.

## Repository layout

- `sql/server-version-policy.md` — server release-series claims and exact reference-CI targets.
- `docs/mssql-dialect-roadmap.md` — unsupported future SQL Server dialect plan.

- `docs/architecture.md` — model boundary and catalog outline.
- `docs/spss-profile.md` — SPSS source-faithful mapping rules.
- [Python / pinned pyspssio implementation profile](docs/implementation-profiles/python-pyspssio-0.5.1.md) — Python adapter pyspssio capability boundary; it does not relax the normative SAV/ZSAV profile.
- `sql/dialect-profiles.md` — initial SQLite, PostgreSQL, MySQL/MariaDB and Dolt physical profiles.
- `sql/` — dialect-neutral schema outline and profile notes.
- `sql/transformation-workflow-profile-schema.sql` - optional derived-data
  catalog outline, separate from the immutable core catalog.
- `transformation/plan-0.1.schema.json` — canonical transformation-plan schema.
- `sql/transformation-plan-profile-schema.sql` — compact in-place apply audit;
  it is not a dataset-version catalog.
- `conformance/transformation-plan-0.2.json` and
  `conformance/spss-syntax-frontend-0.2.json` — additive plan and frontend
  conformance cases with independent golden hashes; `conformance/in-place-transformation-0.2.json`
  fixes the same-dataset/same-table execution invariants and the additional
  controlled Dolt context. The 0.1 schemas and fixtures remain unchanged.
- `examples/` — small illustrative mapping fixtures.

## Conformance principle

Implementations must preflight target capabilities before import. If the target cannot faithfully create one wide table because of column, identifier, string, or row limits, import must fail atomically with a machine-readable capability diagnostic. It must never silently truncate, drop, split, transpose, pivot, or transform source data.

This specification repository publishes normative Transformation Plan and SPSS syntax frontend schemas, documentation, declarative fixtures, and its own structural/hash/fixture validation in tools/validate_repository.py. It does not contain executable implementation or behavioral conformance code: parser, SQL-engine, transaction, and adapter behavior belong in each implementation or adapter repository.

## Who it is for

OpenStatSpec is for people and projects that need to move statistical datasets between SPSS and relational databases without turning the data into a different model. It is especially relevant to:

- implementers building SPSS import/export adapters or language libraries;
- data managers and statistical-data practitioners preserving SPSS dictionaries in SQL-backed workflows;
- database maintainers preparing a dialect profile with clear capability boundaries; and
- users who need an inspectable, source-faithful relational target for SPSS data.

## Trying the profile

Read the [SPSS profile](docs/spss-profile.md) and the [schema outline](sql/schema-outline.sql), then map a small unencrypted `.sav` or `.zsav` file to one dedicated wide table plus the catalog metadata. Preserve source case and variable order, retain raw values, and use the metadata tables to retain labels, missing-value rules, formats, and other dictionary semantics.

An implementation must publish its database dialect capabilities and reject any source dataset it cannot represent faithfully in one table. The [basic example](examples/basic-spss-mapping.md) illustrates the intended shape.

## Contribute and adopt

This profile welcomes real-world review. Implementers, statistical-data practitioners, and database maintainers are invited to test it against actual SPSS datasets and contribute findings, fixtures, dialect profiles, adapter support, or documentation improvements. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

The standard remains deliberately narrow: it defines a source-faithful relational representation, not a statistics engine, survey platform, harmonization system, or general data warehouse model.
