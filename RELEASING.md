# Releasing OpenStatSpec

This checklist governs releases of this specification repository. It does not
publish an implementation package and does not substitute for implementation
or adapter conformance evidence.

The repository release maintainer with repository-admin authority is responsible
for completing this checklist and preserving the release controls it requires.

The Python companion distribution is released separately from the specification.
Package tags use the `package-vX.Y.Z` convention; specification tags use
`vX.Y.Z`. A specification tag MUST NOT publish the package, and a package tag
MUST match the version declared in `pyproject.toml`.

## Prepared v0.5.0 scope

This release prepares the normative optional
[Database I/O Execution Policy v1](docs/database-io-policy-v1.md). It is not
published until the gates below complete. Release notes MUST identify explicit
`database_io_policy` selection, database-read-only export with returned loss
diagnostics, and packaged exact tested Dolt 2.2.2/2.2.3 write policy with optional
external evidence. Existing unselected-profile requirements, SAV 1.0 semantics
and fixtures, schemas, and canonical Plan/Frontend/Binding artifacts are unchanged.
This is a pre-1.0 minor optional addition under [VERSIONING](VERSIONING.md).

Run `python -m pytest` and `python tools/validate_repository.py` at the selected
commit. Adapter package release CI supplies real exact-version write and
read-only/failure-path evidence under the new policy; neither fabricated
repository declarations nor user-supplied evidence files are release substitutes.
Python `v0.8.0` and PHP `v0.7.0` are downstream adapter release targets, not
conformance claims made by this specification. Their pins and publication are
managed separately. The companion `openstatspec-specification` distribution
remains `0.1.0`: no package API, schema or validator contract change requires a
package release for this documentation policy addition.

## Before preparing a release

- Choose an exact reviewed commit on the appropriate branch and record its
  full commit ID. Stable tags use the convention `vX.Y.Z`.
- Keep maintenance releases on their maintained release branch. Merge the
  equivalent corrective change to `main` separately when it is also needed by
  the next minor release; do not make a maintenance tag point at unrelated
  unreleased `main` work.
- Run the repository validation at that exact commit and confirm the required
  CI run for that commit is successful. A green run for a nearby commit is not
  sufficient.
- Gate a specification release on its normative artifacts, review, versioning,
  repository validation, and exact-commit CI. Adapter conformance and
  service-matrix evidence are downstream: they gate only an implementation's
  support or conformance claims and package releases against the exact
  specification commit and, once published, its release identifier. They do not
  gate specification publication.
- Confirm the changelog, versioning impact, and release notes describe only
  the included specification changes.

## Tag and release

- Create and push `vX.Y.Z` only after the exact release commit has passed
  CI. Use the selected signed annotated-tag path where signing is available,
  or the selected protected-tag path restricted to release maintainers. Do not
  move or reuse a published tag.
- Wait for the CI run in that exact tag context to succeed before creating or
  publishing the immutable GitHub release; a branch-commit CI result is not a
  substitute for the tag-context result.
- Create the GitHub release as a draft from that exact tag and verify the tag
  target, title, notes, links, and any release assets before publication.
- Before publishing, verify the repository immutable-releases setting is
  enabled. If that setting or the selected signed-or-protected tag path is
  unavailable, stop and restore the missing selected control before publishing.
- Publish the release only after those checks are confirmed.

## After publication

- Verify GitHub reports immutable true for the published release and its tag as
  the intended full commit ID.
- Verify the tag-triggered CI run is successful and that the release notes are
  visible from the repository release page.
- Track implementation conformance and service-matrix work separately from
  specification release gates. Publishing a specification does not assert
  implementation conformance, and incomplete implementation evidence does not
  block specification publication.
