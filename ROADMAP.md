# Roadmap

This is a working to-do list for OpenStatSpec. Items below describe intended work, not promises of a release date or expanded scope.

## 1. Core SPSS relational specification

- [x] Complete the SPSS `.sav` and `.zsav` mapping rules for values, dictionary metadata, ordering, missing values, formats, attributes, documents, variable sets, and multiple-response sets.
- [x] Review the source-faithful wide-table contract for clarity and implementability.
- [x] Define the machine-readable fidelity-event and target-capability diagnostic fields.
- [ ] Review terminology and examples with statistical-data practitioners and adapter implementers.

## 2. Canonical fixtures and conformance tests

- [x] Create small lawful SPSS fixtures covering ordinary values and dictionary metadata.
- [x] Add edge-case fixtures for system-missing, user-missing values and ranges, strings, labels, formats, long names, and identifier collisions.
- [x] Define expected relational outcomes and semantic round-trip checks.
- [x] Publish conformance-test guidance for dialect profiles and adapters.

## 3. Reference adapters

Prerequisite: the core mapping and canonical fixtures are stable enough to test against.

- [x] Establish a Python reference-adapter repository that imports and exports the SPSS profile, reports fidelity events, and runs the canonical fixtures.
- [x] Establish a PHP reference-adapter repository with the same profile boundary and fixture expectations.
- [x] Document supported source features and declared database capabilities for each adapter.

## 4. CI, releases, and documentation

- [x] Add continuous specification-repository checks for links, schema examples,
  and fixtures.
- [x] Define adapter conformance guidance; each adapter repository owns its runtime CI and evidence.
- [x] Define versioning and compatibility guidance for the specification and profiles.
- [x] Publish release notes and tagged specification releases; `v0.2.1` is the
  current public specification release and is immutable.
- [ ] Expand implementation, dialect-profile, and adoption documentation from real adapter experience.

## 5. Future adapters

Prerequisite: the SPSS profile, fixtures, and reference-adapter lessons are mature.

- [ ] Assess separate source-faithful profiles and adapters for SAS, Stata, and other statistical packages.
- [ ] Do not begin a future adapter by broadening the relational contract; each profile must preserve the source package's native rectangular data model and declare its own fidelity boundary.

## 6. Optional SQL transformation workflow

- [x] Define an independent catalog for immutable SQL-derived datasets.
- [x] Define parameter binding, lineage, hashes, audit, metadata and weight
  propagation, dialect boundaries, and atomic publication.
- [x] Add machine-readable positive and failure conformance cases.
- [ ] Publish profile 1.0 after its normative contract, declarative cases, and
  specification-repository checks are complete.
- [ ] Require each implementation to pass the relevant cases before claiming
  profile 1.0 conformance.

## 7. Canonical transformation plans and syntax frontends

- [x] Define a language-neutral canonical plan for ordered recodes and variable
  and value-label metadata operations.
- [x] Define a bounded SPSS-syntax frontend with stable diagnostics and
  machine-readable conformance cases.
- [x] Define the in-place binding that preserves dataset/table identity on
  supported SQL profiles and never creates an OpenStatSpec undo/copy layer.
- [ ] Require each implementation to run the in-place apply service matrix
  against every claimed SQL profile before publishing its execution claims;
  this does not block specification publication.
- [ ] Evaluate additional language frontends as separate adapters that lower to
  the same canonical plan.

## 8. Microsoft SQL Server dialect

Microsoft SQL Server is not currently supported. The
[MSSQL dialect roadmap](docs/mssql-dialect-roadmap.md) defines the future
scope without creating a capability claim.

- [ ] Select and pin Python and PHP driver stacks after fidelity and security evaluation.
- [ ] Define T-SQL types, quoting, catalog binding, identity probes and effective-limit preflight.
- [ ] Add exact cumulative-update CI services and complete conformance/fault-injection evidence.
- [ ] Publish an independent dialect profile after its normative T-SQL contract,
  declarative cases, and specification-repository checks are complete.
- [ ] Require each reference adapter to pass the relevant evidence gate before
  claiming Microsoft SQL Server support.
- [ ] Evaluate Azure SQL identities separately; do not inherit a SQL Server claim implicitly.

## 9. Next release dependency order

The specification release and implementation claims have separate gates. The
specification defines and publishes the contract first; implementation evidence
follows and does not block specification publication.

1. [x] Merged Transformation Plan and SPSS Frontend profile 0.2 as
   unreleased, release-candidate work for the planned specification `v0.3.0`.
2. [ ] Complete and review the normative `v0.3.0` documents, schemas,
   declarative fixtures, and hashes; select the exact release commit and pass
   this repository's validation and CI on that commit.
3. [ ] After confirming release-tag signing or protection, create a signed or
   protected `v0.3.0` tag on that commit, require its exact tag-context CI run
   to pass, and follow the [release checklist](RELEASING.md) draft and control
   verification before publishing the immutable release.
   Until then claims use `release_candidate`, a null release identifier, and
   the exact tested commit.
4. [ ] Have Python pin the exact specification commit and, once published,
   record its `v0.3.0` release identifier; rebase conditional transformations
   on the lifecycle implementation and pass the combined service and
   conformance gates before making an adapter claim or package release.
5. [ ] Have PHP pin the exact specification commit and, once published, record
   its `v0.3.0` release identifier; migrate to the canonical transformation plan
   and pass the relevant conformance cases before making an adapter claim or
   package release.

The pending in-place service matrix and adapter conformance work in sections 6
and 7 are downstream implementation gates. They do not block the `v0.3.0`
specification release, and publishing the specification does not complete those
implementation evidence gates.

## Maintainer setup

These are maintainer actions, not implementation tasks for the specification repository itself.

- [x] Publish the OpenStatSpec Python distribution and establish its public PyPI
  project. Published package releases establish the public project; they do not
  by themselves re-verify owner security or the Trusted Publishing workflow.
- [ ] Re-verify secure PyPI/TestPyPI ownership and Trusted Publishing before the
  next Python release workflow is relied on.
- [x] Register and publish the OpenStatSpec PHP package through Packagist. The
  public package establishes the registry setup; repository update ownership
  still needs release-process verification.
- [x] Define the specification release tag convention and maintainer checklist in
  [RELEASING.md](RELEASING.md); the repository release maintainer with repository-admin responsibility owns release-process controls.
- [x] Protect the default branch and release tags. main requires pull requests,
  successful specification CI, and resolved conversations; force pushes and
  deletion are disabled, and these controls apply to administrators. The active
  v* tag ruleset permits bypass only to repository administrators. GitHub
  Actions use full-SHA, GitHub-owned actions, and merged head branches are
  automatically deleted.
