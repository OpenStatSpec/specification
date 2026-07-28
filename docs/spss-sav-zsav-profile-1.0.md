# SPSS SAV/ZSAV Profile 1.0

## Status and conformance language

This is a versioned normative profile for unencrypted IBM SPSS Statistics system files: SAV and ZSAV. Terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

An implementation conforms to this profile only for the directions and database profiles it declares. It MUST publish a machine-readable capability declaration and MUST run the fixture expectations in `conformance/spss-sav-zsav-1.0.json` for every claimed direction. Encrypted files and portable (`.por`) files are outside this profile.

## Source-faithful relational contract

For one imported SPSS dataset, an importer MUST create exactly one dedicated physical wide SQL data table. Every source case MUST map to one row, every source variable MUST map to one physical column, and no source variable may be transposed, split, stored in EAV/JSON, dropped, or coerced into a different logical shape.

The table MUST have `__case_ordinal BIGINT NOT NULL PRIMARY KEY`, populated as 1 through the source case count in source order. It is technical state, not an SPSS variable, and an exporter MUST omit it. No respondent or natural key may be inferred.

The singular catalog relations in `sql/schema-outline.sql` are the normative source of truth for import and export. An implementation MAY retain a legacy or framework-specific compatibility catalog, but changing only that compatibility catalog MUST NOT change conformant export output. If duplicate metadata is retained during migration, the implementation MUST verify its equality with the normative catalog.

The catalog MUST retain the source-to-physical mapping and the dictionary metadata. `dataset.physical_table_schema` and `dataset.physical_table_name` identify the target data table. A source variable name is authoritative. If a SQL profile cannot use it safely, it MUST create a deterministic unique physical name and retain the exact mapping in `variable`. Names beginning with `__` are reserved and MUST NOT be generated for source variables.

## Atomic preflight and diagnostics

Before creating a data table or `dataset` row, an importer MUST preflight source variable count, physical identifiers, binary64 support, text/value and row limits, and all profile-declared limits. A failure MUST be atomic: no partial data table or dataset catalog row may remain.

Every import and export MUST have an `operation` record. A preflight failure MUST be represented by a failed import operation and at least one `fidelity_event` with a NULL `dataset_id`. Events MUST include direction, severity, stable event code, affected source item where applicable, and machine-readable details. Implementations MUST use `target_capability_exceeded` for a target limit failure and MUST NOT silently truncate, split, reshape, or substitute another storage model.

## Values, types, and ordering

Numeric variables MUST use a profile type capable of SPSS binary64 values. Numeric system-missing MUST map to SQL NULL. User-missing codes and ranges MUST remain ordinary stored values. String variables MUST use lossless variable-length text and MUST be NOT NULL; blank string is a value, not system-missing.

Dates, times, datetimes, and currencies MUST remain numeric stored values plus SPSS print/write format metadata. Implementations MUST NOT reinterpret them as SQL temporal or decimal values. Exporters MUST read rows by `__case_ordinal` and variables by `source_ordinal`.

## Required dictionary preservation

For every supported SAV/ZSAV import/export, the following dictionary semantics MUST round-trip:

- dataset file label, ordered document lines, source encoding, and source format;
- the optional case-weight variable reference;
- variable name, numeric/string storage kind, declared string width, label, print/write format family, width and decimals;
- measurement level, role, display width, and display alignment;
- typed numeric and string value labels in deterministic order;
- system-missing, discrete user-missing values, inclusive numeric ranges, LOWEST/HIGHEST endpoints, and the SPSS range-plus-discrete combination;
- ordered dataset and variable attributes, including attribute arrays;
- variable sets and their ordered members;
- multiple-response sets, including name, label, MD/MC kind, ordered members, numeric or string MD counted value, category-label behavior, and label source; and
- long UTF-8 string values, their declared widths, labels, and supported missing metadata without truncation.

A reader or writer that cannot preserve one of these items MUST declare the capability absent. An importer MAY retain unknown source extensions in a namespaced extension payload, but it MUST report a fidelity event rather than claim full profile fidelity.

## SAV and ZSAV

A claimed SAV reader/writer MUST process SAV data and dictionary records. A claimed ZSAV reader/writer MUST perform actual compressed-data decoding/encoding; recognising the ZSAV header alone is not ZSAV support. An implementation MUST declare SAV and ZSAV independently when only one is supported.

## Semantic round-trip

A semantic round-trip is `source SAV/ZSAV -> relational representation -> SAV/ZSAV -> reread`. The reread dataset MUST have the same case order, variable order, raw values, system-missing states, and all required dictionary semantics. File bytes, compression details, timestamps, product information, and physical binary record layout are not required to match.

If an export is attempted with known information that the selected writer cannot reproduce, the implementation MUST fail before creating an output artifact unless the caller explicitly opts in to the identified loss. That opt-in MUST be recorded as an export fidelity event.

## Explicit exclusions

This profile does not define a statistics engine, analysis language, survey platform, questionnaire model, study lifecycle model, long-form data view, EAV model, table chunking, pivoting, automatic harmonisation, or automatic concatenation of study waves.
