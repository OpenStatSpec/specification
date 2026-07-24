# SPSS Profile Draft

## Scope

This profile defines a source-faithful mapping for unencrypted SPSS `.sav` and `.zsav` datasets. It does not specify the SAV binary format and excludes encrypted files and portable (`.por`) files.

## Import mapping

| SPSS concept | OpenStatSpec representation |
| --- | --- |
| File / dataset | One `dataset` row and one dedicated physical wide data table. |
| Case | One data-table row; source order stored in `__case_ordinal`. |
| Variable | One physical data-table column and one ordered `variable` row. |
| Numeric value | A binary64-capable profile type; system-missing is SQL `NULL`. |
| String value | A lossless variable-length text profile type; `NOT NULL`; blank is a value. |
| Date/time/currency | Numeric stored value plus print/write format metadata. |
| Variable label / value label | Metadata; never substituted into data values. |
| User-missing values or ranges | `missing_rule`; raw values remain in the data table. |
| Variable/dataset attributes | Ordered metadata attributes. |
| Documents, variable sets, MR sets | Dedicated metadata relations, preserving order where present. |

## Physical identifiers

An implementation must retain an exact source variable name in `variable.source_name`. A dialect profile may use that name as the physical column identifier only when it is safe. Otherwise it generates a deterministic unique identifier and records it in `variable.physical_name`.

This is not a loss of fidelity: source identity is represented by the recorded total mapping, not by coincidental identifier equality. Profiles must detect SQL reserved words, case-folding, collisions, identifier-length limits, and the reserved __ technical prefix during preflight.

## Required preflight

Before writing a target table, importers must verify:

1. Source variable count plus the technical ordinal fits the profile's column capacity.
2. Every source variable has a deterministic unique physical identifier within the profile identifier limit.
3. Every source string and possible row satisfies declared text and row/value-size limits.
4. The profile can represent binary64 numeric values and lossless text according to its published capability declaration.

Failure must be atomic. The importer must create no partial dataset representation and must report a machine-readable `target_capability_exceeded` event with the violated limit and affected source item.

## Export mapping

Export reads the dedicated data table in `__case_ordinal` order. It recreates source variables in `variable.source_ordinal` order, using source names and metadata from the catalog. `__case_ordinal` is omitted. SQL `NULL` in a numeric variable becomes SPSS system-missing. The exporter must report any unsupported source metadata or target-writer limitation as a machine-readable fidelity event; it must not silently omit or change it.

## Explicit exclusions

This profile does not add long-form views, EAV tables, chunked tables, JSON value storage, pivoting, transposition, automatic wave concatenation, automatic harmonization, inferred keys, or question/instrument/study semantics.
