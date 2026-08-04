# Conditional SPSS-like transformation on an existing target

Transformation Plan and SPSS Syntax Frontend 0.2 support bounded sequential
numeric assignment. Assume `target` already exists as a nullable numeric
physical column and normative catalog variable:

```spss
COMPUTE target = 0.
IF (source_a = 1 AND source_b = 1) target = 1.
VARIABLE LABELS target 'Synthetic conjunction'.
VALUE LABELS target 0 'No' 1 'Yes'.
FORMATS target (F1.0).
VARIABLE LEVEL target (NOMINAL).
EXECUTE.
```

`COMPUTE` initializes every case. `IF` then changes only rows whose complete
predicate is TRUE. If either comparison is UNKNOWN because a source is numeric
system missing, the row retains zero. The remaining commands establish the
label, complete value-label map, F1.0 format, and nominal measurement level.

On SQLite or PostgreSQL an implementation may create `target` in the apply
only when its declared profile proves one native transaction covers schema,
data, catalogs, and audit. MySQL, MariaDB, and Dolt reject create mode with
`schema_change_not_atomic`.

For Dolt, provision the physical and catalog target together in a separate
caller-owned commit. Begin the transformation from that clean HEAD. The exact
syntax above then binds `COMPUTE` as replacement of the existing target,
leaves an inspectable working-set diff, and does not call `DOLT_COMMIT`.
