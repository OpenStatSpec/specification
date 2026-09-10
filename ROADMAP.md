# Roadmap

This is a working to-do list for OpenStatSpec. Items below describe intended work, not promises of a release date or expanded scope.

## Current status (2026-09-10)

- Specification `v0.5.0` is published at immutable commit
  `864e84479f554b8ee250ffed44c4dfb963750d4a`; both reference adapters pin it.
- Python `0.8.1` is published on PyPI. PHP `0.7.2` preparation is merged
  ([PR #15](https://github.com/OpenStatSpec/php/pull/15)); tagging and Packagist
  publication remain separate. The last verified Packagist version is `0.7.1`.
- Both adapters select SPSS SAV/ZSAV 1.0 and Database I/O Execution Policy v1,
  with official Plan 0.1/0.2 and In-Place Binding 0.1/0.2 service evidence.
  This is not a claim to implement every optional profile in this release.
- Official SPSS Frontend 0.3 adapter conformance remains pending. Python's
  schema-change extension uses Plan/Frontend `0.3` identifiers, but those
  names alone do not establish conformance to the published syntax-only
  Frontend 0.3 contract over Plan 0.1/0.2.

### Immediate next work

- [ ] Finish the PHP `0.7.2` release: finalize release metadata, verify the
  exact release commit's CI, tag, and verify a clean Packagist install.
- [ ] Reconcile Python's schema-change contract identifiers with the published
  specification before expanding or claiming official Frontend 0.3 support.
- [ ] Implement and verify official Frontend 0.3 separately in each adapter,
  including its 35 declared cases and inherited compatibility cases.
- Further PHP catalog refactoring and optimization are not release gates;
  schedule them only against a concrete correctness or measured performance need.

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
- [x] Publish release notes and tagged specification releases; `v0.5.0` is the
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
- [x] Verify the Python 0.8.1 and PHP 0.7.2 preparation in-place apply service
  matrices for the claimed Plan/Binding 0.1/0.2 SQL profiles. Repeat this gate
  for each release or expanded claim; it does not block specification publication.
- [ ] Evaluate additional language frontends as separate adapters that lower to
  the same canonical plan.
- [ ] Expand the bounded SPSS frontend through the independently versioned
  milestones in the [SPSS frontend roadmap](docs/spss-frontend-roadmap.md),
  without creating a general SPSS compatibility claim.
- [x] Complete the Frontend 0.3 specification candidate as a syntax-only
   expansion over immutable Plan 0.1/0.2 after its schema, profile, 35 declared
   cases, inherited compatibility, and repository validation are complete:
   comments, dictionary-order variable lists, grouped supported forms, ordinary
   not-equal/NOT predicates, open recode ranges, and additive value labels.
- [ ] Define typed numeric expressions, deterministic numeric/date functions,
  missing-value predicates and metadata, additional numeric/date formats, and
  restricted conditional blocks in a new Plan/Frontend/In-Place Binding
  generation.
- [ ] Define string and physical-schema operations separately, with exact
  add/rename/drop-column atomicity and rollback evidence for every claimed SQL
  profile.
- [ ] Keep case-count/order and group/cross-dataset operations in separate
  profiles whose invariants do not weaken the current same-cases in-place
  binding.

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
   unreleased, release-candidate work for specification `v0.3.0`.
2. [x] Complete and review the normative `v0.3.0` documents, schemas,
   declarative fixtures, and hashes; select the exact release commit and pass
   this repository's validation and CI on that commit.
3. [x] The protected `v0.3.0` tag points to commit
   `cd8f198c68b849eb8ed018a894670a0904c2181d`; its exact tag-context
   [CI run](https://github.com/OpenStatSpec/specification/actions/runs/31588389841)
   passed, and the immutable [GitHub release](https://github.com/OpenStatSpec/specification/releases/tag/v0.3.0)
   was published using the [release checklist](RELEASING.md).
4. [x] Python adopted the released Plan/Binding 0.1/0.2 contracts and passed
   the combined service and conformance gates; its current pin is `v0.5.0`.
5. [x] PHP adopted the released Plan/Binding 0.1/0.2 contracts and passed
   applicable service and conformance gates; its current pin is `v0.5.0`.

6. [x] Merged and reviewed SPSS Syntax Frontend profile 0.3 as a
   backward-compatible optional profile over immutable Plan 0.1/0.2 contracts.
7. [x] Prepared specification `v0.4.0` release notes, stable profile status,
   exact artifact validation, and tag-context CI requirements; adapter claims
   remain downstream and are not implied by this release.
8. [x] Published documentation patch release `v0.4.1` to align the frontend
   roadmap with the stable Frontend 0.3 profile; no normative contract changed.
9. [x] Prepare the optional [Database I/O Execution Policy v1](docs/database-io-policy-v1.md)
   and `v0.5.0` release notes without changing existing source or plan contracts.
10. [x] Published `v0.5.0` at commit
    `864e84479f554b8ee250ffed44c4dfb963750d4a`. Both adapters adopted that
    exact pin and the Database I/O Execution Policy v1. Python `0.8.1` and
    PHP `0.7.1` are published; PHP `0.7.2` publication remains separate.

Optional workflow and Frontend 0.3 conformance remain downstream implementation
work. Existing Plan/Binding 0.1/0.2 service evidence does not establish those
additional claims. Specification publication and adapter publication retain
separate evidence gates.

## Maintainer setup

These are maintainer actions, not implementation tasks for the specification repository itself.

- [x] Publish the OpenStatSpec Python distribution and establish its public PyPI
  project. Published package releases establish the public project; they do not
  by themselves re-verify owner security or the Trusted Publishing workflow.
- [x] Verified production PyPI Trusted Publishing through Python `0.8.1`
  publication after correcting the workflow name to `release.yml`; the
  configured GitHub environment is `pypi`.
- [ ] Re-verify PyPI/TestPyPI ownership and applicable publishing controls before
  future releases; production publication is not evidence of TestPyPI setup.
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
