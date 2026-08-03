# Dolt adapter declarations

This directory accepts concrete, evidence-backed adapter declarations. Each
declaration binds one exact adapter version, specification commit, conformance
run and active Dolt version to the authoritative exact-tested Dolt profile in
`sql/dialect-profile-baseline.json`.

Evidence belongs below `evidence/`. Every declaration records canonical paths
and SHA-256 hashes. No declaration is shipped until its evidence is available;
the empty declaration set is valid.
