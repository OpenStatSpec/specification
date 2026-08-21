# Changelog

## Unreleased

Future changes will be listed here.

## v0.4.1 - 2026-08-21

OpenStatSpec `v0.4.1` is a documentation and release-bookkeeping patch for
the stable `v0.4.0` specification. It changes no normative contract or
conformance artifact.

- Aligned the SPSS frontend roadmap with the published Frontend 0.3 profile.
- Corrected release metadata fixtures and validation coverage for the public
  README and current release status.

## v0.4.0 - 2026-08-21

OpenStatSpec `v0.4.0` publishes SPSS Syntax Frontend 0.3 as a stable optional
profile. The release tag is the immutable specification identity for this
release.

- Added comments, existing-variable `TO`, grouped supported forms, predicate
  aliases and bounded `NOT`, open recode ranges, and additive value labels.
- Frontend 0.3 emits only immutable Plan 0.1/0.2 objects and adds no SQL
  binding operation.
- Repository validation now covers all Plan/Frontend/Binding schemas,
  manifests, references, inherited cases, and canonical hashes.
- Adapter claims remain downstream and separately gated; this release does not
  assert PHP or Python implementation conformance.

## v0.3.0 - 2026-08-12

OpenStatSpec `v0.3.0` is the stable public specification release at immutable
specification commit `cd8f198c68b849eb8ed018a894670a0904c2181d`.

- Added backward-compatible Transformation Plan and SPSS Syntax Frontend 0.2
  contracts for sequential numeric `COMPUTE` and conditional `IF`, bounded
  comparison/`AND`/`OR` expressions, `FORMATS`, `VARIABLE LEVEL`, and
  `EXECUTE`.
- Defined exact SQL three-valued missing semantics and deterministic complete
  plan JSON hashing while preserving every 0.1 contract, fixture, and hash.
- Kept create-target apply fail-closed on MySQL, MariaDB, and Dolt; these
  profiles require a separately versioned physical-and-catalog provisioning
  action followed by an existing-target apply with no automatic Dolt commit.
- Added independent synthetic golden fixtures, hashes, examples, and repository
  validation gates for the new contracts.

- Packaged the repository's Dolt declaration validator and authoritative SQL
  resources as the `openstatspec-specification` companion distribution.
- Bound every concrete Dolt declaration to a declaration ID, adapter
  implementation and exact version, exact specification commit, and conformance
  run ID; exact single-match selection is required before mutation.

- Added a pending symbolic Dolt profile template and a separate concrete adapter
  declaration schema/path and contract for tested active-version identity,
  numeric limits, DDL atomicity, audit-safe cleanup failure, and machine-linked
  boundary/fault evidence.

## v0.2.1 - 2026-08-04

- Corrected the SPSS Syntax Frontend 0.1 schema's `$defs` and `$ref`
  keywords so typed value-label values are constrained as the existing
  contract states. This maintenance release contains no Transformation Plan or
  SPSS Syntax Frontend 0.2 work.

## v0.2.0 - 2026-07-31

- Added canonical Transformation Plan and SPSS Syntax Frontend profiles for a
  bounded `RECODE`, `VARIABLE LABELS`, and `VALUE LABELS` subset.
- Added plan/frontend JSON Schemas, canonical-hash conformance cases, examples,
  and repository validation gates.
- Added a product-neutral in-place binding for supported SQL profiles: direct
  same-table data/metadata mutation, compact operation audit, no automatic
  commit, and no derived/copy/snapshot/rollback history layer. Dolt adds a
  controlled branch/HEAD/working-set context.

## v0.1.0 - 2026-07-31

- Defined conservative maintained release-series claims and exact CI targets
  for MySQL 8.4.11/9.7.2, MariaDB 11.4.12/11.8.8/12.3.2 and PostgreSQL
  17.10/18.4.
- Expanded the independent Dolt claim from exact 2.2.2 to the conservative
  `>=2.2.2,<2.3.0` portion of 2.2.x and added exact 2.2.3 CI
  evidence alongside retained 2.2.2 evidence.
- Clarified the non-conflicting SQLite core/optional-workflow policies.
- Added an explicitly unsupported Microsoft SQL Server dialect roadmap.
- Prepared the initial specification release as `v0.1.0`.

- Defined the strict one-source-dataset to one-wide-table relational contract.
- Added the normative operation and fidelity-event model.
- Added SQLite, PostgreSQL, and MySQL/MariaDB dialect capability profiles.
- Added generated CC0 SAV/ZSAV conformance fixtures and a machine-readable manifest.
- Added Python and PHP reference-adapter conformance coverage.
- Made the singular normative catalog the required source of truth for export.
- Added case-weight, typed multiple-response counted values, label-source, and explicit LOWEST/HIGHEST coverage.
- Required immutable specification identity, theoretical/effective SQL limits, tested server versions, and concrete canonical fixture expectations in capability declarations and conformance runs.
- Clarified prerelease identity, dimensioned identifier limits, and exclusive catalog namespace ownership.
- Added an independent, fail-closed Dolt 2.2.2 SQL profile with a dedicated-database binding, evidence-labelled adapter limits, and complete compensating cleanup for non-atomic DDL.
- Added optional SQL Transformation Workflow Profile 0.1 without changing the immutable source-faithful core contract.
