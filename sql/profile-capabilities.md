# Dialect Profile Capabilities

See [Initial SQL dialect profiles](dialect-profiles.md) for the SQLite,
PostgreSQL, MySQL/MariaDB and independent Dolt starting profiles.

A database dialect profile must publish enough capabilities for an importer to decide whether a dataset can be represented faithfully in one physical wide table.

Required declarations:

- immutable specification commit, release-candidate/released status, and the
  published release identifier or NULL;
- selected profile and database engine separately from transport and driver;
- raw and normalized server versions, the claimed server-version range, and a
  separate list of exact CI-tested server versions;
- positive product-identity probes and their normalized results; missing,
  conflicting, unknown or unclaimed identity must fail before any catalog
  creation, migration, audit write or dataset mutation;
- maximum number of physical columns, including `__case_ordinal`;
- maximum number of source variables, derived independently from the physical
  column envelope;
- maximum identifier length as { value, unit, source, repertoire }, where
  unit is bytes or characters, plus identifier folding/quoting behavior;
- reserved-word policy, reserved __ technical prefix, and deterministic physical-name algorithm;
- exclusive catalog binding mode, namespace or prefix, logical-to-physical
  relation mapping, and `catalog_identity` ownership check;
- binary64-capable numeric type and any exceptional-value constraints;
- lossless variable-length text type, encoding behavior, and text/value limit;
- maximum value, row-size and per-statement limits, each with value, unit,
  source and a basis of theoretical engine limit, exact-version observation,
  proposed adapter envelope or active effective limit;
- whether DDL and catalog writes are atomic, or the compensating-cleanup
  procedure used after a failed write;
- the exact name of the physical data table and the catalog mapping that
  associates it with the dataset.

The importer checks these capabilities before object creation. If a source is outside the profile boundary, it fails atomically and records a machine-readable `target_capability_exceeded` diagnostic. A conforming implementation may support only the subset of SPSS datasets within its declared engine limits.

For MySQL-compatible transports, transport selection is not product identity.
In particular, a MySQL URL or driver does not authorize a
`mysql_mariadb_innodb` or `dolt` engine claim. Each profile's positive
identity requirements decide the product. Ambiguity fails closed before any
catalog or dataset mutation and leaves zero database mutation.
