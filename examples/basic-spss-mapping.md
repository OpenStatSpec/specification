# Basic SPSS Mapping Example

Source SPSS dataset, in source variable order:

| case | age | sex | satisfaction |
| ---: | ---: | ---: | ---: |
| 1 | 32 | 1 | 8 |
| 2 | 47 | 2 | system-missing |

The corresponding dedicated SQL table has the same rectangular shape plus the technical ordering column:

| `__case_ordinal` | `age` | `sex` | `satisfaction` |
| ---: | ---: | ---: | ---: |
| 1 | 32 | 1 | 8 |
| 2 | 47 | 2 | `NULL` |

`NULL` represents SPSS numeric system-missing only. A user-missing code such as `9` remains stored as `9` and is described by an `missing_rule` record. Likewise, `sex` labels such as `1 = "Male"` and `2 = "Female"` are held in value-label metadata; the SQL table continues to store `1` and `2`.

On export, rows are read by `__case_ordinal`, variables are emitted in metadata source order, and the technical ordinal column is omitted.
