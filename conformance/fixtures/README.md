# SPSS SAV/ZSAV fixture generation

`generate-fixtures.sps` creates the synthetic fixtures named in
`../spss-sav-zsav-1.0.json`. Before running it in IBM SPSS Statistics, create
the folder `C:\OpenStatSpec-fixtures\`, or replace that path in every `GET FILE`
and `SAVE OUTFILE` command in the script. The script deliberately uses no SPSS
macro.

The generated data is synthetic and is dedicated to CC0 under
[`LICENSE.md`](LICENSE.md). Do not replace it with an externally sourced survey
file: a fixture must exercise a defined semantic feature, not merely be a valid
SAV file.

SPSS does not expose persisted **Variable Sets** dictionary records through
ordinary command syntax. The script therefore writes `sets-source.sav` for
this fixture. After the script finishes:

1. Open `sets-source.sav` in SPSS.
2. Use **Utilities → Define Variable Sets** and create:

   - `demographics`: `respondent_id age gender`
   - `contact_channels`: `channel_email channel_sms channel_web preferred_contact_1 preferred_contact_2`

3. Save the file as `sets.sav` in the same fixture directory.

The preflight fixture is profile-specific: the conformance runner must generate
it with one more variable than the target profile permits.
