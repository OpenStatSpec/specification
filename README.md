# OpenStatSpec

OpenStatSpec is an open, SQL-oriented specification for representing a statistical data file and its dictionary metadata in a relational database without changing the source package's rectangular data model.

The first profile targets IBM SPSS Statistics system files. It maps one source dataset to one dedicated wide SQL table: each source case becomes one row and each source variable becomes one physical column. Supporting catalog tables retain only the metadata needed to interpret and export that SPSS dataset faithfully.

## Status

This repository contains a working draft, not a released standard. It records the core design boundary before implementation libraries are created.

## Core contract

- One source dataset maps to exactly one dedicated SQL data table.
- One SPSS case maps to exactly one row, in source order.
- One SPSS variable maps to exactly one physical SQL column, in source order.
- The table contains a reserved technical ordinal column, `__case_ordinal`, used only to preserve case order. It is never exported as an SPSS variable.
- Numeric system-missing values map to SQL `NULL`; SPSS user-missing codes remain their original stored values and are described in metadata.
- Dates, times, and currencies remain SPSS numeric values plus SPSS format metadata.
- String blanks remain values, not missing values.

OpenStatSpec does not define long-form cells, EAV storage, table splitting, reshaping, automatic harmonization, or questionnaire/study entities. It does not infer respondent keys or combine datasets. All conformant database-object identifiers are generic; the double-underscore prefix is reserved for standard technical identifiers.

[Roadmap](ROADMAP.md) tracks remaining project work and maintainer setup.


## Repository layout

- `docs/architecture.md` — model boundary and catalog outline.
- `docs/spss-profile.md` — SPSS source-faithful mapping rules.
- [Python / pyspssio implementation profile 0.5.1](docs/implementation-profiles/python-pyspssio-0.5.1.md) — Python adapter pyspssio capability boundary; it does not relax the normative SAV/ZSAV profile.
- `sql/dialect-profiles.md` — initial SQLite, PostgreSQL, and MySQL/MariaDB physical profiles.
- `sql/` — dialect-neutral schema outline and profile notes.
- `examples/` — small illustrative mapping fixtures.

## Conformance principle

Implementations must preflight target capabilities before import. If the target cannot faithfully create one wide table because of column, identifier, string, or row limits, import must fail atomically with a machine-readable capability diagnostic. It must never silently truncate, drop, split, transpose, pivot, or transform source data.

## Who it is for

OpenStatSpec is for people and projects that need to move statistical datasets between SPSS and relational databases without turning the data into a different model. It is especially relevant to:

- implementers building SPSS import/export adapters or language libraries;
- data managers and statistical-data practitioners preserving SPSS dictionaries in SQL-backed workflows;
- database maintainers preparing a dialect profile with clear capability boundaries; and
- users who need an inspectable, source-faithful relational target for SPSS data.

## Trying the draft

Read the [SPSS profile](docs/spss-profile.md) and the [schema outline](sql/schema-outline.sql), then map a small unencrypted `.sav` or `.zsav` file to one dedicated wide table plus the catalog metadata. Preserve source case and variable order, retain raw values, and use the metadata tables to retain labels, missing-value rules, formats, and other dictionary semantics.

An implementation must publish its database dialect capabilities and reject any source dataset it cannot represent faithfully in one table. The [basic example](examples/basic-spss-mapping.md) illustrates the intended shape.

## Contribute and adopt

This draft needs real-world review. Implementers, statistical-data practitioners, and database maintainers are invited to test it against actual SPSS datasets and contribute findings, fixtures, dialect profiles, adapter support, or documentation improvements. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

The standard remains deliberately narrow: it defines a source-faithful relational representation, not a statistics engine, survey platform, harmonization system, or general data warehouse model.
