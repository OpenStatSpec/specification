# Roadmap

This is a working to-do list for OpenStatSpec. Items below describe intended work, not promises of a release date or expanded scope.

## 1. Core SPSS relational specification

- [ ] Complete the SPSS `.sav` and `.zsav` mapping rules for values, dictionary metadata, ordering, missing values, formats, attributes, documents, variable sets, and multiple-response sets.
- [ ] Review the source-faithful wide-table contract for clarity and implementability.
- [ ] Define the machine-readable fidelity-event and target-capability diagnostic fields.
- [ ] Review terminology and examples with statistical-data practitioners and adapter implementers.

## 2. Canonical fixtures and conformance tests

- [ ] Create small lawful SPSS fixtures covering ordinary values and dictionary metadata.
- [ ] Add edge-case fixtures for system-missing, user-missing values and ranges, strings, labels, formats, long names, and identifier collisions.
- [ ] Define expected relational outcomes and semantic round-trip checks.
- [ ] Publish conformance-test guidance for dialect profiles and adapters.

## 3. Reference adapters

Prerequisite: the core mapping and canonical fixtures are stable enough to test against.

- [ ] Establish a Python reference-adapter repository that imports and exports the SPSS profile, reports fidelity events, and runs the canonical fixtures.
- [ ] Establish a PHP reference-adapter repository with the same profile boundary and fixture expectations.
- [ ] Document supported source features and declared database capabilities for each adapter.

## 4. CI, releases, and documentation

- [ ] Add continuous checks for specification links, schema examples, fixtures, and adapter conformance once the relevant repositories exist.
- [ ] Define versioning and compatibility guidance for the specification and profiles.
- [ ] Publish release notes and tagged specification releases.
- [ ] Expand implementation, dialect-profile, and adoption documentation from real adapter experience.

## 5. Future adapters

Prerequisite: the SPSS profile, fixtures, and reference-adapter lessons are mature.

- [ ] Assess separate source-faithful profiles and adapters for SAS, Stata, and other statistical packages.
- [ ] Do not begin a future adapter by broadening the relational contract; each profile must preserve the source package's native rectangular data model and declare its own fidelity boundary.

## Maintainer setup

These are maintainer actions, not implementation tasks for the specification repository itself.

- [ ] For the Python repository: create and secure PyPI and TestPyPI project ownership, then configure PyPI Trusted Publishing for the repository's release workflow before the first package release.
- [ ] For the PHP repository: register the package with Packagist and configure repository-based automatic updates before the first public release.
- [ ] Decide the release owner(s), tag naming convention, and release checklist for every repository.
- [ ] Protect the default branches and ensure release tags are created only by the agreed release workflow.
