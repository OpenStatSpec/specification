# Concrete Dolt adapter declarations

With explicit [Database I/O Execution Policy v1](../../docs/database-io-policy-v1.md)
selection, packaged tested policy is the default Dolt write gate and this
external format is an optional advanced override. Its schema, validator and
real-evidence requirements remain unchanged; the runtime declaration gate
below still applies to adapters not selecting that policy and to external
overrides selected under it.

This directory is the only repository path for concrete, import-capable Dolt
adapter declarations. Each `*.json` file MUST be a full Dolt profile object
conforming to `../dolt-adapter-declaration-schema.json`; it is not a partial
override of the symbolic baseline.

The symbolic declaration remains in `../dialect-profile-baseline.json` and MUST
remain pending, evidence-free, import-disabled, and unbound: its
`declaration_id`, `adapter_implementation_id`, `adapter_version`,
`specification_commit`, and `conformance_run_id` are all null. Do not copy
its template symbols or `template_*` evidence identifiers into a concrete
declaration.

Every concrete declaration MUST bind one canonical `declaration_id`, the
stable `adapter_implementation_id`, one exact canonical `adapter_version`,
the exact lowercase 40-hex `specification_commit` used for conformance, and
one canonical `conformance_run_id`. An adapter may write only after the
installed validator finds exactly one declaration matching the active
`DOLT_VERSION()`, adapter implementation and version, and specification
commit. Zero or multiple matches reject before mutation.

No concrete declaration is checked in until an exact Dolt product version has
real product-identity, limit, DDL-atomicity, boundary, structural, and fault
evidence. Evidence artifacts belong under this directory's `evidence/`
subdirectory. Every evidence record uses a canonical repository-relative path,
publishes the artifact's lowercase SHA-256 digest, and is rejected if the path
is missing, escapes through `..` or a symlink, or the digest differs.

The repository validator automatically loads every `*.json` declaration in
this directory and rejects declarations that do not satisfy the concrete
contract. This README intentionally contains no invented example measurements
or evidence references.
