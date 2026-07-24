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

## Repository layout

- `docs/architecture.md` — model boundary and catalog outline.
- `docs/spss-profile.md` — SPSS source-faithful mapping rules.
- `sql/` — dialect-neutral schema outline and profile notes.
- `examples/` — small illustrative mapping fixtures.

## Conformance principle

Implementations must preflight target capabilities before import. If the target cannot faithfully create one wide table because of column, identifier, string, or row limits, import must fail atomically with a machine-readable capability diagnostic. It must never silently truncate, drop, split, transpose, pivot, or transform source data.
