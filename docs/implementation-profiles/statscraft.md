# Statscraft independent implementation record

## Status

This is an informative record of an independent implementation. It is not a
reference adapter, it does not amend or relax any normative profile, and it
does not gate specification publication. Each profile named below keeps its
own requirements; this page only records which of them Statscraft declares and
which evidence was observed, at one exact Statscraft commit and one exact
specification pin.

[Statscraft](https://github.com/statscrafthq/statscraft) is an MIT-licensed
open-source statistics package written in Rust. Its crate
`crates/openstatspec` (Cargo package `statscraft-openstatspec`) is a separate,
bounded OpenStatSpec driver with its own lexer and parser. Statscraft's own
statistics engine does not run on OpenStatSpec plans.

| Item | Value |
| --- | --- |
| Statscraft commit | [`14c8fd577271ebf2dd61eff84423bfa33135cbcd`](https://github.com/statscrafthq/statscraft/commit/14c8fd577271ebf2dd61eff84423bfa33135cbcd) on `main` |
| Specification pin | `a7930784c70befcd0c348464e6f154e2ad0ed2bc` (`v0.5.1`), read from `crates/openstatspec/spec-commit` |
| Conformance artifacts | identical to `v0.5.0` at `864e84479f554b8ee250ffed44c4dfb963750d4a`; `v0.5.1` changed documentation only |
| Release status | development commit; no Statscraft release contains this CI wiring yet |

The latest Statscraft release, `v0.24.0`, predates this evidence. Until a
release is cut from a commit that carries the same pin and passes the same
runs, this record describes a development commit only. A release claim follows
Statscraft's next release and will name that release, its exact commit and its
runs.

## Declared scope

At the recorded commit Statscraft declares:

- SPSS Syntax Frontend 0.1, 0.2 and 0.3, selected by the exact request
  contracts `openstatspec-spss-syntax-frontend-v0.1`, `-v0.2` and `-v0.3`;
- Transformation Plan 0.1 and 0.2 validation, canonical JSON and plan and
  source hashes;
- In-Place Binding 0.1 and 0.2 (`openstatspec-in-place-transformation-v0.1`
  and `-v0.2`);
- SPSS SAV/ZSAV Profile 1.0 storage of a dataset as one wide table plus the
  catalog, with import, export and semantic round trip, on the SQLite,
  PostgreSQL, MySQL, MariaDB and Dolt profiles; and
- Database I/O Execution Policy v1 (`database_io_policy:
  openstatspec-database-io-v1`), selected in the capability declaration of the
  Dolt profile, where reads and exports write nothing.

The command-line entry points are `statscraft db export`, `statscraft db
import` and `statscraft db capabilities`, and `statscraft plan --apply`. In
Statscraft's command names, `db export` stores a SAV/ZSAV file in the database
and `db import` reads a dataset from the database back into a file;
`db capabilities` prints the machine-readable capability declaration.

## Declared refusals and Dolt policy

These are refusals Statscraft declares and tests; they are not new profile
requirements.

- SQLite: NaN and negative zero are refused in preflight, before any row is
  written, because SQLite `REAL` columns do not keep them. The failed attempt
  leaves no dataset and no data table; it records a failed operation and a
  fidelity event naming the variable.
- MySQL, MariaDB and Dolt: NaN, both infinities and negative zero are refused
  before writing.
- PostgreSQL: every binary64 value, including NaN payloads and negative zero,
  is stored and read back bit for bit.
- Dolt: Statscraft never commits, branches, merges or resets. Dolt commits
  stay with the caller. Writes need an exact tested product version, 2.2.2 or
  2.2.3; another 2.2.x version from 2.2.2 on is opened read-only.
  `plan --apply` on Dolt requires the expected branch and HEAD.

## Evidence

The conformance manifests are read in place from a checkout of this
repository at the pinned commit; nothing is copied into Statscraft. In CI a
missing checkout fails the run instead of skipping.

| Suite | Test | Cases at the pin |
| --- | --- | --- |
| Transformation Plan 0.1 and 0.2 | `conformance.rs`, `transformation_plan_manifests` | 4 and 26 |
| Syntax Frontend 0.1, 0.2 and 0.3 | `conformance.rs`, `syntax_frontend_manifests` | 13, 44 and 90 effective (35 declared in 0.3) |
| SAV/ZSAV 1.0 on SQLite | `sqlite_conformance.rs`, `sav_zsav_1_0_on_sqlite` | 8 manifest fixtures, including the generated preflight fixture |
| In-Place 0.1 and 0.2 on SQLite | `sqlite_conformance.rs`, `in_place_transformation_bindings_on_sqlite` | every case that applies to the profile |
| Server profiles | `servers.rs`, 24 tests | see below |

The frontend test asserts that Frontend 0.3 has exactly 90 effective cases and
fails on any case whose source hash, plan, plan hash or diagnostic code
differs. The case counts in the table are the manifest counts at the pin; the
CI log shows that each test passed, not the per-manifest counts.

`servers.rs` runs SAV/ZSAV 1.0, both in-place manifests, a round trip of every
fixture, preflight limits, refusals and the Dolt commit policy against real
servers. Each matrix leg runs all 24 tests against two Dolt servers (2.2.2 and
2.2.3) and a MariaDB 10.11 server that must be refused as too old:

| Leg | PostgreSQL | MySQL | MariaDB |
| --- | --- | --- | --- |
| 1 | 17 | 8.4 | 11.4 |
| 2 | 18 | 9.7 | 11.8 |
| 3 | 18 | 9.7 | 12.3 |

Runs:

- [CI run 44953384355](https://github.com/statscrafthq/statscraft/actions/runs/44953384355)
  (push to `main`, success): `cargo test` on Ubuntu and Windows, including
  `conformance.rs` and `sqlite_conformance.rs`.
- [Server tests run 44953471462](https://github.com/statscrafthq/statscraft/actions/runs/44953471462)
  (manual run on `main`, success): 24 of 24 tests passed in each of the three
  legs.

Both runs are at the recorded commit and checked out the specification at the
pin. Earlier runs on the pull-request branch at the same pin,
[CI 44951423175](https://github.com/statscrafthq/statscraft/actions/runs/44951423175)
and [server tests 44951421265](https://github.com/statscrafthq/statscraft/actions/runs/44951421265),
also succeeded.

## Claimed versus tested

- Tested: the suites and server matrix above, at the recorded commit and pin.
- Claimed but not exercised by these runs: TLS. The two TLS tests need
  certificates that the server workflow does not provide, so they pass without
  connecting over TLS.
- Claimed beyond the tested versions: the capability declaration claims
  SQLite `>=3.24.0,<4.0.0` but tests only the bundled SQLite library.
- Frontend 0.3 pin: the adapter claim gate in the Frontend 0.3 profile names
  the `v0.4.0` commit. Statscraft pins `v0.5.1` instead; between the two, the
  only change under `conformance/` is `conformance/README.md`, so every
  manifest and fixture it runs is identical to `v0.4.0`.
- Not yet aligned: at this commit the capability declaration printed by
  `statscraft db capabilities` still names specification commit
  `8594ee12ccf57526cf1142df4b216432c366da84` with status `release_candidate`,
  and lists fewer tested server versions than the matrix above. The
  conformance evidence uses the `spec-commit` pin. The declaration has to name
  the pinned commit and its release before a release claim.

## Differences from the reference adapters

Behavior on which Statscraft and the Python and PHP reference adapters differ
is tracked in
[OpenStatSpec/specification#27](https://github.com/OpenStatSpec/specification/issues/27)
for `v0.6.0`. This record does not repeat or decide those differences.
