# Microsoft SQL Server Dialect Roadmap

## Status and boundary

Microsoft SQL Server (MSSQL) is a future independent dialect. It is not a
supported OpenStatSpec target, has no capability declaration, and MUST continue
to fail as an unsupported driver. Azure SQL Database and Azure SQL Managed
Instance are separate deployment identities and are not implicitly covered by
a future SQL Server claim.

The first milestone is strict-wide core import, validation and export. The
optional SQL Transformation Workflow remains out of scope until it has its own
dialect-aware parser, authorizer and conformance evidence.

## Driver candidates

- Python must evaluate Microsoft's `mssql-python` DB-API driver and
  `pyodbc` with Microsoft ODBC Driver 18. SQLAlchemy integration, parameter
  binding, binary64/text fidelity, transaction semantics and supported Python
  platforms must be proven before one candidate is selected.
- PHP should use Microsoft's `PDO_SQLSRV` extension so the adapter retains its
  PDO boundary. The selected PHP driver and ODBC dependency must be pinned and
  included in the CI capability evidence.

Primary driver references are Microsoft's
[`mssql-python` documentation](https://learn.microsoft.com/en-us/sql/connect/python/mssql-python/python-sql-driver-mssql-python),
[`PDO_SQLSRV` reference](https://learn.microsoft.com/en-us/sql/connect/php/pdo-sqlsrv-driver-reference)
and [PHP driver installation requirements](https://learn.microsoft.com/en-us/sql/connect/php/step-1-configure-development-environment-for-php-development).

## Dialect work

The profile must define and test bracket or quoted identifier escaping,
case/collation behavior, schema-qualified exclusive catalog binding,
`BIGINT` ordinals, IEEE-754-compatible `FLOAT(53)`, lossless Unicode text such
as `NVARCHAR(MAX)`, parameter markers, generated-key behavior and every catalog
DDL difference. Limits must be discovered or conservatively preflighted rather
than copied from another profile. Candidate envelopes include identifier,
physical-column, row, value and statement limits from Microsoft's
[capacity specification](https://learn.microsoft.com/en-us/sql/sql-server/maximum-capacity-specifications-for-sql-server),
but they become claims only after exact-version boundary tests.

## Capability and runtime preflight

Before any mutation, an adapter must positively identify the product with
`SERVERPROPERTY` values including `ProductVersion`, `ProductLevel`, `Edition`
and `EngineEdition`; normalize the exact server version; distinguish SQL Server
from Azure variants; match a published release-series claim; and reject
unknown, conflicting or unclaimed identities. The capability declaration must
publish the driver and transport, raw and normalized identity results,
claimed series, exact CI-tested versions, catalog binding, effective limits,
collation/encoding inputs and atomicity policy.

## CI and conformance strategy

CI should run a dedicated Linux service from
`mcr.microsoft.com/mssql/server`, pinned to an exact cumulative-update tag and
immutable digest rather than `latest`. The job must use Developer edition,
accept the image EULA explicitly, wait on a real SQL query, create a
least-privilege test login/database and never expose the service outside the
runner. Microsoft's [container guidance](https://learn.microsoft.com/en-us/sql/linux/install-upgrade/quickstart-install-docker)
is the source for image and startup requirements.

Both adapters must run the complete official fixture manifest, strict
dictionary round trips, catalog migration/ownership checks, boundary preflight
failures and fault injection. A version enters the claim only after both
adapters have exact-version evidence or the specification records an explicit
adapter-specific boundary.

## Security and atomicity gates

- All values use driver parameters; identifiers use one audited quoting path.
  Connection strings, passwords, tokens and server error details must not leak
  into capability JSON, fidelity events or CI logs.
- Encryption and certificate validation are secure by default. CI exceptions,
  if unavoidable for an isolated container, must be explicit and must never
  become production defaults.
- Catalog ownership is an exclusive schema plus a verified singleton
  `catalog_identity`; pre-existing foreign objects fail without modification.
- Transaction behavior must be proven with `SET XACT_ABORT ON`, `TRY...CATCH`
  and `XACT_STATE()`-aware rollback tests. Microsoft's
  [`TRY...CATCH` transaction guidance](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/try-catch-transact-sql)
  is a starting point, not evidence by itself.
- Tests must cover DDL failure, deadlock/timeout, connection loss, poisoned or
  uncommittable transactions, cleanup idempotence and retry safety. Success is
  forbidden while any partial catalog, dataset or staging object remains.
