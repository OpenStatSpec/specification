# Dialect Profile Capabilities

A database dialect profile must publish enough capabilities for an importer to decide whether a dataset can be represented faithfully in one physical wide table.

Required declarations:

- maximum number of physical columns, including `_oss_case_ordinal`;
- maximum identifier length and identifier folding/quoting behavior;
- reserved-word policy and deterministic physical-name algorithm;
- binary64-capable numeric type and any exceptional-value constraints;
- lossless variable-length text type, encoding behavior, and text/value limit;
- maximum row size or any related wide-table limit.

The importer checks these capabilities before object creation. If a source is outside the profile boundary, it fails atomically and records a machine-readable `target_capability_exceeded` diagnostic. A conforming implementation may support only the subset of SPSS datasets within its declared engine limits.
