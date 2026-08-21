# Task 10 Fix Report

## Scope

Removed the completed PHP adapter v0.6.0 evidence claim from
`ROADMAP.md`. Restored section 9 item 5 as an unchecked downstream gate requiring
PHP to pin the exact specification commit and pass applicable conformance
evidence before changing adapter or package-release claims.

No Frontend 0.3 documentation, published 0.1/0.2 artifact, manifest count,
validator behavior, or runtime code was changed.

## Verification

- `/tmp/opencode/specification-test-venv/bin/python -m pytest -q`: `51 passed`.
- `/tmp/opencode/specification-test-venv/bin/python tools/validate_repository.py`:
  passed; reported Plan `4/26`, Frontend `13/44/90`, and Binding `6/11`.
- `git diff --exit-code --` for all published 0.1/0.2 schemas and manifests:
  passed with no output.
- `git diff --check`: passed; Git emitted only the existing LF-to-CRLF warning.

## Concerns

- None identified.
