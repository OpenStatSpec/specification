# Architecture

## Purpose

OpenStatSpec defines a narrow relational representation of a source statistical package dataset. The representation preserves the package's native rectangular shape rather than creating a new analysis model.

This draft defines the architectural contract for the SPSS profile. Other packages may later receive separate profiles, but do not broaden this contract.

## Normative data shape

For every imported source dataset, an implementation creates exactly one dedicated physical SQL table.

1. Every source case maps to one row.
2. Every source variable maps to one physical column.
3. Source case order and source variable order are normative.
4. The table begins with `__case_ordinal BIGINT NOT NULL PRIMARY KEY`, populated from one through the number of source cases. This column is OpenStatSpec technical state, not a source variable, and is omitted on export.
5. No natural key is inferred.

The source variable name is authoritative metadata. The physical SQL identifier may differ only where required by the SQL dialect, and the catalog must provide a total, deterministic, lossless mapping between them. Identifiers beginning with __ are reserved for standard technical use and must not be generated for source variables.

## Metadata catalog

Catalog tables exist solely to preserve source semantics needed to interpret and export the data table. They do not replace source values or define a second data model.

| Catalog relation | Purpose |
| --- | --- |
| `dataset` | Dataset identity, physical table location, source provenance, encoding, labels, documents, and import state. |
| `variable` | Ordered source-to-column mapping plus variable storage, format, label, display, role, and measurement metadata. |
| `value_label_set` / `value_label` | Typed stored codes and their labels, in deterministic order. |
| `variable_value_label_set` | Links a variable to a value-label set. |
| `missing_rule` | User-missing discrete values and inclusive numeric ranges. |
| `dataset_attribute` / `variable_attribute` | Source custom attributes, including ordered arrays. |
| `document` | Source document text, in source order. |
| `variable_set` / `variable_set_member` | Named variable sets and ordered memberships. |
| `multiple_response_set` / `multiple_response_member` | SPSS multiple-response metadata and ordered members. |
| `fidelity_event` | Mandatory machine-readable import/export warnings and capability failures. |

There are no core relations for cells, questions, responses, instruments, studies, waves, or harmonized variables.

## Values and missingness

The dedicated data table stores the source values. Value labels are metadata and never substitute for stored values. SPSS numeric system-missing becomes SQL `NULL`. SPSS user-missing values remain ordinary stored raw values, including values covered by an inclusive range. SPSS string variables have no system-missing state; blank strings remain blank strings and string columns must therefore be `NOT NULL`.

SPSS date, time, and currency values are numeric values with format metadata. Implementations must not reinterpret them as SQL temporal or decimal types.

## Capability boundary

The one-table contract is deliberate. A database profile declares its identifier, maximum physical-variable, row/value-size, binary64, and text capabilities. Before creating any objects, an importer must check the source against those capabilities.

If faithful creation is impossible, the import must fail atomically and emit an `fidelity_event` with code `target_capability_exceeded`. It must not split tables, use EAV/JSON, reshape, truncate, drop columns, or coerce values.

## Fidelity

The draft aims for semantic round-trip equivalence: cases, values, order, and supported SPSS dictionary metadata are preserved. It does not promise byte-identical SAV or ZSAV output. Original artifacts may be retained for audit but are not a replacement for the relational representation.
