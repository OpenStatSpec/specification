# SPSS SAV/ZSAV fixture generation

Run `generate-fixtures.sps` in IBM SPSS Statistics. It creates the synthetic
fixtures named in `../spss-sav-zsav-1.0.json` under
`C:\Users\admin\Downloads\`.

The script is self-contained. It creates both SPSS multiple-response sets and
ordinary Variable Sets. `weight-and-string-mr.sav` is the explicit oracle for
a case-weight reference and a string-valued MD counted value; these semantics
must not be inferred from the more general set fixture.

Since IBM SPSS exposes no command for defining ordinary Variable Sets, the script
uses bundled `BEGIN PROGRAM Python3` code to materialize
a tiny synthetic dictionary template and then imports only its `VARSETS` with
`APPLY DICTIONARY`. The temporary template is removed automatically.

The generated data is synthetic and is dedicated to CC0 under
[`LICENSE.md`](LICENSE.md). Do not replace it with an externally sourced survey
file: a fixture must exercise a defined semantic feature, not merely be a valid
SAV file.

The preflight fixture is profile-specific: the conformance runner must generate
it with one more variable than the target profile permits.
