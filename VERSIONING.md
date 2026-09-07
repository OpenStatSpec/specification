# Versioning and compatibility

OpenStatSpec uses semantic versioning for tagged specification releases.

- A major release may change normative relational semantics, required catalogue fields, conformance expectations, or the meaning of an existing requirement.
- A minor release may add backward-compatible optional metadata, a new independent source or SQL profile, or new fixtures that do not invalidate an implementation's existing declared conformance scope.
- A patch release may clarify wording, correct examples, or fix fixture and schema defects without changing normative meaning. A schema-defect correction may be backported to a published release series only when it restores the already-stated normative contract; it must not introduce new required behavior, broaden the accepted contract, or silently revise canonical artifacts.

The optional [Database I/O Execution Policy v1](docs/database-io-policy-v1.md)
is an independent execution contract selected by `database_io_policy`, not a
revision of SAV 1.0 or any canonical plan, frontend, binding or catalog schema.
Its explicitly scoped overrides apply only when selected; otherwise existing
requirements remain unchanged. Adding it in pre-1.0 `v0.5.0` is a minor optional
addition, not a patch clarification. No blanket profile freeze or version bump
is required. Future incompatible changes to this policy require a new policy
identifier; they MUST NOT silently change v1 selection.

Optional workflow profiles are versioned and claimed independently from the
core source profile. Adding or revising an optional profile does not authorize
changes to core datasets. A breaking workflow-profile change increments that
profile's major version even when the core version is unchanged.

Transformation Plan and frontend contracts are selected by their exact
contract identifiers. An implementation may support multiple versions
simultaneously. It MUST preserve the canonical bytes and hashes of accepted
older plans and MUST NOT silently reinterpret or rewrite an older plan under a
newer schema. A frontend that accepts a newer request contract but receives a
program entirely inside the 0.1 command subset emits the exact 0.1 plan
contract. Explicit recompilation to a newer plan is a new identified operation,
not migration of the old plan or audit row.

The SPSS SAV/ZSAV profile is versioned independently in its document and manifest. A conforming implementation must publish the exact profile version, immutable specification commit, specification status, supported directions, supported SQL profiles, and engine capability declaration it tested.

The immutable commit is mandatory for both release candidates and stable releases. `specification_release` is additive provenance, not an alternative to the commit:

- for untagged work on `main`, `specification_status` is `release_candidate` and `specification_release` is NULL;
- for a published tagged release candidate, `specification_status` remains `release_candidate` and `specification_release` is the exact prerelease identifier whose target is the declared commit; and
- for a published stable release, `specification_status` is `released` and `specification_release` is the exact release identifier whose target is the declared commit.

Development work on `main` is not a released standard. Release candidates may be used for interoperability testing but must be identified as such. A stable specification release is created only by a signed or protected tag after this repository's normative-artifact, review, versioning, validation, and exact-commit CI gates pass. Reference-adapter conformance is downstream evidence for implementation claims and does not gate specification publication.

A release-candidate tag is optional. An immutable commit is sufficient for CI and interoperability review. If maintainers publish a named release candidate, its protected or signed tag is recorded as `specification_release`, while the commit remains mandatory.

Adapter package versions are independent from specification versions. An adapter update that changes its declared conformance scope or fidelity behavior must document that change even when the specification version is unchanged.
