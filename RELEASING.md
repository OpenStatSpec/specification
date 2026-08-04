# Releasing OpenStatSpec

This checklist governs releases of this specification repository. It does not
publish an implementation package and does not substitute for implementation
or adapter conformance evidence.

The repository release maintainer with repository-admin authority is responsible
for completing this checklist and preserving the release controls it requires.

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
- For a release that claims adapter, dialect, transformation, or syntax-front
  end support, collect the required adapter conformance and service-matrix
  evidence for that same specification commit. Do not convert a
  `release_candidate` claim into `released` before those gates pass.
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
- Record any remaining future-release gates in the roadmap. Publishing a
  specification release never completes pending adapter or service-matrix
  evidence by itself.
