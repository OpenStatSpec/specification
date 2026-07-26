# Python / pyreadstat implementation profile 0.1

## Status

This is a versioned implementation capability declaration for the
`OpenStatSpec/python` adapter when it uses `pyreadstat` as its SPSS engine. It
does not amend or relax the normative requirements of
[SPSS SAV/ZSAV Profile 1.0](../spss-sav-zsav-profile-1.0.md).

The adapter supports the strict one-dataset/one-wide-table relational contract
and its declared SQLite, PostgreSQL, MySQL, and MariaDB dialect profiles. Its
capability boundary is engine-specific: a caller must use this declaration,
not a generic claim of “SPSS support”, to determine whether an operation can
produce a full semantic round trip.

## Declared directions

| Direction | Declared status |
| --- | --- |
| `sav_read` | supported, subject to source features exposed by the engine |
| `sav_write` | supported with the write exclusions below |
| `zsav_read` | supported, subject to source features exposed by the engine |
| `zsav_write` | supported with the write exclusions below |

The adapter MUST record the exact installed `pyreadstat` and underlying
ReadStat versions in its machine-readable capability declaration and operation
records. A version change does not silently expand this profile: newly claimed
capabilities require the corresponding conformance fixtures.

## Writer exclusions

The current `pyreadstat` writer cannot reproduce the following required SPSS
dictionary semantics from the relational catalog:

- variable display alignment;
- variable roles;
- custom dataset attributes and custom variable attributes, including arrays;
- variable sets and their ordered members;
- multiple-response sets and their ordered members or MD/MC-specific fields;
- a write format distinct from a print format; and
- the original source encoding.

The implementation declaration MUST mark each of these as an unsupported
**write** capability. It MUST NOT claim full SAV/ZSAV Profile 1.0 semantic
round-trip conformance for a dataset containing any of them.

## Required loss handling

Before export, the adapter MUST inspect the catalog for every unsupported
writer semantic above. If one is present, it MUST fail before creating an
output artifact unless the caller supplies operation-scoped `allow_loss` for
the reported loss. The adapter MUST emit a machine-readable `fidelity_event`
for every rejected or accepted loss, with at least:

- `direction: export`;
- a stable event code for the exact semantic (for example,
  `writer_cannot_preserve_variable_role`);
- the affected dataset, variable, set, or attribute where applicable;
- the selected engine and version; and
- a description of the omitted or changed value.

For source encoding, the event details MUST include both `source_encoding` and
the encoding emitted by the writer. An accepted `allow_loss` event records a
user-authorised lossy export only. It does not alter this capability declaration
and does not make the resulting exporter conformant for that semantic.

## Reader boundary

If the engine does not expose a known source semantic on import, the adapter
MUST NOT silently discard it. It MUST either fail the import before creating a
dataset, or retain the original value in a namespaced extension payload and
write a fidelity event. In the latter case the import result is explicitly
capability-limited and is not a full profile-conformance result.

## Conformance claim

This profile permits the Python adapter to claim conformance only for the
directions, source features, database profile, and fixtures it actually
declares and passes. A complete SPSS SAV/ZSAV Profile 1.0 claim requires a
writer capable of every normative dictionary semantic; `allow_loss` cannot be
used to make that broader claim.
