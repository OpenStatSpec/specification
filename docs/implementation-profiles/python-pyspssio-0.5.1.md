# Python / pinned pyspssio implementation profile

## Status

This is a versioned implementation capability declaration for the OpenStatSpec/python
adapter when it uses the TonisOrmisson/pyspssio fork pinned at commit 0b3f879
as its sole SPSS engine. It does not amend or relax the normative requirements of
[SPSS SAV/ZSAV Profile 1.0](../spss-sav-zsav-profile-1.0.md).

The adapter implements the strict one-dataset/one-wide-table relational
contract and its declared SQLite, PostgreSQL, MySQL, and MariaDB dialect
profiles. Its capability boundary is engine-specific: a caller must use this
declaration, not a generic claim of “SPSS support”, to determine whether an
operation can produce a full semantic round trip.

## Declared directions and preserved semantics

The pinned pyspssio fork is the required, sole engine for unencrypted SAV and ZSAV.
The adapter declares `sav_read`, `sav_write`, `zsav_read`, and `zsav_write`.
Within those directions, the following semantics are supported by the current
engine integration and its conformance coverage:

- one source case per ordered wide-table row and one source variable per
  ordered physical column, with raw values and system-missing states;
- variable labels, typed value labels, and user-missing rules;
- measurement level, variable role, display alignment, and display width;
- file attributes and variable attributes, including scalar values and
  ordered arrays represented as IBM SPSS Name[1], Name[2], … members;
- dataset file label;
- independent print and write format tuples;
- variable sets and their ordered members;
- case-weight-variable metadata;
- multiple-response-set metadata exposed by the engine; and
- UTF-8 source encoding, variable names, and storage widths.

The implementation MUST record the exact pinned pyspssio source commit, installed
package version, and underlying IBM I/O Module version when available in its machine-readable
capability declaration and operation records. A version change does not
silently expand this profile: newly claimed capabilities require the
corresponding conformance fixtures.

## Fail-closed writer boundary

The pinned fork API has these known limits. The adapter
MUST treat them as absent or capability-limited writer semantics and MUST NOT
claim full SAV/ZSAV Profile 1.0 semantic-round-trip conformance for an
operation affected by any of them.

| Semantic | Required diagnostic code or codes | Consequence |
| --- | --- | --- |
| Ordered document text | documents-unobservable | The engine can copy documents only between existing files; it cannot read or create document text for a faithful round trip. |
| Legacy compatible variable names | compatible-variable-name-not-exportable | The reader exposes a source short name, but the writer cannot set or guarantee a chosen short-name mapping. |
| Non-UTF-8 source encoding | `source-encoding-not-preserved` | The writer has no preservation contract for a legacy source code page. |

Before export, the adapter MUST inspect its catalog and recorded engine events
for these conditions. It MUST fail before creating an output artifact unless
the caller supplies operation-scoped `allow_loss` for every reported code. It
MUST record a machine-readable `fidelity_event` for each rejected or accepted
loss, including direction, event code, affected source item when known, engine
version, and explanatory details. The encoding event MUST include both
`source_encoding` and emitted encoding when known.

An accepted `allow_loss` records a user-authorised lossy export only. It does
not alter this declaration, cannot make an affected export conformant for the
lost semantic, and cannot authorise a later operation implicitly.

## Reader boundary and conformance claim

If the engine does not expose a known source semantic on import, the adapter
MUST NOT silently discard it. It MUST either reject the import before creating
a dataset or retain the original value in a namespaced extension payload and
record a fidelity event. In the latter case the result is capability-limited and
is not a full profile-conformance result.

This declaration permits the Python adapter to claim conformance only for the
directions, source features, database profile, and fixtures it actually
declares and passes. A complete SPSS SAV/ZSAV Profile 1.0 claim requires an
engine capable of every normative dictionary semantic; `allow_loss` cannot be
used to make that broader claim.
