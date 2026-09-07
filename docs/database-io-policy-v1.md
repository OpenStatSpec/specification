# Optional Database I/O Execution Policy v1

Status: normative optional addition prepared for OpenStatSpec `v0.5.0`;
publication remains subject to [RELEASING](../RELEASING.md).
Terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Explicit selection and precedence

An adapter selects this policy by publishing this exact field in its
machine-readable capability declaration for the declared execution scope:

```json
{"database_io_policy": "openstatspec-database-io-v1"}
```

Support alone is not selection. The declaration MUST identify the selected
policy, supported directions and SQL profiles, exact adapter version, and
immutable specification commit, status and release provenance under
[VERSIONING](../VERSIONING.md). An absent or null field selects no override;
an unknown identifier MUST NOT be treated as this policy. Adapters not selecting this policy retain every existing requirement.

Only two execution requirements are overridden when selected:

1. Database-read-only operations, including export, return diagnostics instead
   of persisting operation or fidelity records, even where
   [SAV/ZSAV 1.0](spss-sav-zsav-profile-1.0.md) or an implementation profile
   requires export records or persistence of loss opt-in.
2. Dolt writes use an exact-version tested policy shipped with the adapter
   package by default, instead of requiring a runtime external declaration
   matching the adapter/specification bindings in the
   [Dolt profile](../sql/dialect-profiles.md#dolt-profile).

This is not a reinterpretation of SAV/ZSAV 1.0 or a new source, plan, frontend,
SQL binding, or catalog schema version. All other requirements remain in force.
The source/data/metadata schema, catalog identity, one-dataset/one-wide-table
mapping, dictionary preservation, case/variable order, values and missingness
are unchanged. Existing Plan/Frontend/Binding identifiers, canonical bytes and
hashes MUST NOT be rewritten or supplemented with this capability field.
The [SAV 1.0 fixtures](../conformance/spss-sav-zsav-1.0.json) retain their
semantic expectations, including the import-only failed-preflight audit case.
Claims MUST name both the source profile and this policy rather than imply
unmodified SAV 1.0 export-record behavior.

## Database-read-only operations

All read, inspection, standalone validation and export operations, including
all their setup, validation, error and cleanup paths, MUST NOT issue database writes.
This prohibition includes data or metadata updates, operation/fidelity audit
inserts, catalog initialization, identity bootstrapping, installation or
migration, adapter-created temporary tables, staging objects, and Dolt
working-set or history changes. A rolled-back write is still a prohibited write.
Reads MUST NOT create a missing database or SQLite file. Engine-internal query
execution state is not adapter-created database mutation.

The adapter MUST retain positive server identity and version checks, supported
driver/transport checks, exclusive catalog binding, catalog identity and schema
validation, source-to-physical mapping validation, and data/type/order checks.
MySQL wire compatibility MUST NOT establish Dolt or InnoDB identity. Missing,
foreign, ambiguous or unsupported catalogs and invalid data fail without
repair or migration; any installation or migration requires a separate explicit
write operation. Read-only access MUST NOT depend on passing an import/write
conformance declaration gate, but unsupported server identities, versions or
drivers still fail closed.

Exports MUST read the normative catalog and preserve all declared SAV/ZSAV
writer capability and fidelity checks. Known unsupported semantics MUST fail
before creating an output artifact unless the caller explicitly supplies
operation-scoped `allow_loss` for each identified loss. Rejected and accepted
losses MUST be returned as machine-readable diagnostics with direction,
severity, stable event code, affected source item where applicable, explanatory
details and relevant engine identity. Accepted diagnostics MUST identify the
explicit opt-in. Success and failure diagnostics travel in the operation result
or error, not database persistence; existing database audit rows MUST NOT be
altered. `allow_loss` never grants future consent or full fidelity for a lost
semantic.

Database-read-only does not mean filesystem-read-only. Export MUST preserve
safe file publication: validate before output creation, write only to an
operation-owned temporary file, and publish the completed file atomically
only after successful writing and required checks. Failure MUST leave any
pre-existing destination unchanged and remove operation-owned partial output.
Destination authorization, overwrite rules, path safety and writer errors
MUST NOT be bypassed.

## Packaged Dolt write policy

The default policy permits only exact Dolt product versions 2.2.2 and 2.2.3
that the installed adapter release actually tested. An adapter MAY ship a
narrower tested subset; it MUST NOT infer support for other 2.2.x patches from
a range or from MySQL compatibility. Unknown or untested versions MUST fail before mutation.
On the same connection, the adapter MUST trim and case-fold `@@version_comment`
and require `Dolt`, obtain a non-empty `DOLT_VERSION()`, and match that exact
product version to its selected tested policy.

The package MUST ship its exact supported/tested version list, effective limit
policy and atomicity/cleanup behavior. Its published capabilities MUST identify
the exact adapter release and specification commit and distinguish theoretical,
observed and adapter-policy limits with units and sources. Successful release CI
for that exact adapter release and specification commit is the evidence: it
MUST exercise each supported exact product version with reproducible service
identity and the applicable Dolt product-identity, limit/boundary, binary64/text,
DDL-atomicity and fault/cleanup cases from the existing dialect profile.
Publishing this specification does not assert those downstream tests passed.

Default writes MUST NOT require user-supplied declaration or evidence files,
or invoke the external-file validator as a prerequisite. Packaged policy need
not use the external JSON schema or evidence-file layout; release CI supplies
the real evidence instead. It is not a fabricated concrete declaration: the
symbolic baseline remains pending and MUST NOT be relabelled tested or used as
measured limits.

An adapter MAY offer an explicitly selected external declaration as an advanced
override. If offered, it MUST use the unchanged
[external schema and validator contract](../sql/dolt-adapter-declarations/README.md),
including exactly one matching adapter/version/specification/product binding,
real resolving evidence and path/digest validation. Invalid, ambiguous or
untested overrides fail closed, never silently fall back to the package.
An override does not bypass the [server family policy](../sql/server-version-policy.md)
or any safety gate. The external format remains optional evidence, not a
runtime requirement for default package users; evidence MUST NOT be manufactured.

Only declaration delivery/selection and evidence format change for writes.
Effective limit preflight, driver/security checks, verified database/catalog
ownership, atomicity and audit-safe cleanup remain mandatory. Import audits
remain required under SAV 1.0. Transformation writes retain their selected
[Binding 0.1](transformation-plan-sql-binding-0.1.md) or
[Binding 0.2](transformation-plan-sql-binding-0.2.md) contract, including actor,
expected branch and HEAD, clean working-set preflight and completion checks,
same dataset/table identity, compact audit and native transaction boundary.
Non-atomic create-target apply remains rejected. No automatic Dolt commit,
branch switch, merge, reset, tag or persistent recovery/copy artifact is allowed.

## Adapter verification

In addition to the unchanged source fixtures and write conformance cases,
release CI for each claimed SQL profile MUST demonstrate successful export,
rejected and accepted loss, invalid identity/catalog/data, and writer/publication
failure with zero attempted database writes (including temporary DDL), unchanged
data/metadata/audit and, for Dolt, unchanged branch, HEAD, status and diff.
Read-only database credentials or engine read-only mode SHOULD be used where
available, alongside checks that catch attempted writes hidden by rollback.
Tests MUST verify destination preservation and temporary-file cleanup on failure.
Dolt package tests MUST cover supported exact versions without external files,
unknown-version rejection before mutation, and strict validation of an external
override if that optional path is offered.
