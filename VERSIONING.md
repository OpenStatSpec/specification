# Versioning and compatibility

OpenStatSpec uses semantic versioning for tagged specification releases.

- A major release may change normative relational semantics, required catalogue fields, conformance expectations, or the meaning of an existing requirement.
- A minor release may add backward-compatible optional metadata, a new independent source or SQL profile, or new fixtures that do not invalidate an implementation's existing declared conformance scope.
- A patch release may clarify wording, correct examples, or fix fixture and schema defects without changing normative meaning.

The SPSS SAV/ZSAV profile is versioned independently in its document and manifest. A conforming implementation must publish the exact profile version, specification commit or release tag, supported directions, supported SQL profiles, and engine capability declaration it tested.

Development work on `main` is not a released standard. Release candidates may be used for interoperability testing but must be identified as such. A stable release is created only by a signed or protected tag after the repository validation and reference-adapter conformance gates pass.

Adapter package versions are independent from specification versions. An adapter update that changes its declared conformance scope or fidelity behavior must document that change even when the specification version is unchanged.
