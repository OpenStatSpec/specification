# SPSS SAV/ZSAV fixture generation

`generate-fixtures.sps` creates the synthetic fixtures named in
`../spss-sav-zsav-1.0.json`. Before running it in IBM SPSS Statistics, change
the `!OUT` macro to an existing output directory.

The generated data is intentionally synthetic and is dedicated to CC0 under
[`LICENSE.md`](LICENSE.md). Do not replace it with an externally sourced survey
file: a fixture must exercise a defined semantic feature, not merely be a valid
SAV file.

SPSS does not expose persisted **Variable Sets** dictionary records through
ordinary command syntax. When the script reaches `sets.sav`, use **Utilities →
Define Variable Sets** and create these two sets before running the displayed
`SAVE` command:

- `demographics`: `respondent_id age gender`
- `contact_channels`: `channel_email channel_sms channel_web preferred_contact_1 preferred_contact_2`

The preflight fixture is profile-specific: the conformance runner must generate
