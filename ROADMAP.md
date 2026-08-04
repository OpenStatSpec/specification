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

- [x] Add continuous checks for specification links, schema examples, fixtures, and adapter conformance once the relevant repositories exist.
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
- [ ] Run all cases in reference adapters before publishing profile 1.0.

## 7. Canonical transformation plans and syntax frontends

- [x] Define a language-neutral canonical plan for ordered recodes and variable
  and value-label metadata operations.
- [x] Define a bounded SPSS-syntax frontend with stable diagnostics and
  machine-readable conformance cases.
- [x] Define the in-place binding that preserves dataset/table identity on
  supported SQL profiles and never creates an OpenStatSpec undo/copy layer.
- [ ] Run the in-place apply service matrix against every claimed SQL profile
  before publishing execution claims.
- [ ] Evaluate additional language frontends as separate adapters that lower to
  the same canonical plan.

## 8. Microsoft SQL Server dialect

Microsoft SQL Server is not currently supported. The
[MSSQL dialect roadmap](docs/mssql-dialect-roadmap.md) defines the future
scope without creating a capability claim.

- [ ] Select and pin Python and PHP driver stacks after fidelity and security evaluation.
- [ ] Define T-SQL types, quoting, catalog binding, identity probes and effective-limit preflight.
- [ ] Add exact cumulative-update CI services and complete conformance/fault-injection evidence.
- [ ] Publish an independent dialect profile only after both reference adapters pass the evidence gate.
- [ ] Evaluate Azure SQL identities separately; do not inherit a SQL Server claim implicitly.

## 9. Next release dependency order

The next release work must proceed in this order. Completion of an earlier
artifact is a dependency, not evidence that later adapter or service-matrix
work has passed.

1. [x] Merged Transformation Plan and SPSS Frontend profile 0.2 as
   unreleased, release-candidate work for the planned specification `v0.3.0`.
2. [ ] Rebase Python `0.5.0` conditional transformations on the lifecycle
   implementation, pin the final profile commit, and pass the combined service
   and conformance gates before making an adapter claim.
3. [ ] Migrate PHP to the canonical transformation plan and pass the same
   relevant conformance cases before it claims conditional profile 0.2 support.
4. [ ] Select the exact intended `v0.3.0` commit and require that
   same commit to pass repository validation and all required reference-adapter
   gates. Only after those gates pass and release-tag signing or protection is
   configured, create a signed or protected `v0.3.0` tag on that commit.
   Until then claims use `release_candidate`, a null release identifier, and
   the exact tested commit.

The pending in-place service matrix and adapter conformance work in sections 6
and 7 remains required; implementation package publication does not complete
either evidence gate.

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
  [RELEASING.md](RELEASING.md); release ownership remains an operational control.
- [ ] Protect the default branches and ensure release tags are created only by the agreed release workflow; `main` is currently unprotected.
