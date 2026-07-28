# Dialect Profile Capabilities

See [Initial SQL dialect profiles](dialect-profiles.md) for the SQLite,
PostgreSQL and MySQL/MariaDB starting profiles.

A database dialect profile must publish enough capabilities for an importer to decide whether a dataset can be represented faithfully in one physical wide table.

Required declarations:

- immutable specification commit, release-candidate/released status, and the
  published release identifier or NULL;
- maximum number of physical columns, including `__case_ordinal`;
- maximum identifier length as { value, unit, source, repertoire }, where
  unit is bytes or characters, plus identifier folding/quoting behavior;
- reserved-word policy, reserved __ technical prefix, and deterministic physical-name algorithm;
- exclusive catalog binding mode, namespace or prefix, logical-to-physical
  relation mapping, and `catalog_identity` ownership check;
- binary64-capable numeric type and any exceptional-value constraints;
- lossless variable-length text type, encoding behavior, and text/value limit;
- maximum row size or any related wide-table limit.
- selected database engine and server-version range;
- whether DDL and catalog writes are atomic, or the compensating-cleanup
  procedure used after a failed write;
- the exact name of the physical data table and the catalog mapping that
  associates it with the dataset.

The importer checks these capabilities before object creation. If a source is outside the profile boundary, it fails atomically and records a machine-readable `target_capability_exceeded` diagnostic. A conforming implementation may support only the subset of SPSS datasets within its declared engine limits.
