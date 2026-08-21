# SPSS Frontend 0.3 Specification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a complete specification candidate for SPSS Syntax Frontend 0.3 that adds bounded syntax depth while emitting only immutable Transformation Plan 0.1/0.2 objects.

**Architecture:** First add repository-owned validation for every Plan, Frontend, and In-Place artifact and repair release-status bookkeeping. Then add an exact Frontend 0.3 request schema, normative profile, inherited-case manifest, and independently authored golden cases. Frontend 0.3 changes accepted source syntax only; it adds no Plan operation, SQL binding, audit schema, or executor behavior.

**Tech Stack:** Python 3.11+, pytest 8, jsonschema Draft 2020-12, JSON Schema, restricted RFC 8785 canonical JSON, SHA-256, Markdown, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-21-spss-frontend-expansion-design.md`

## Global Constraints

- Published Plan 0.1/0.2 schemas, operations, canonical bytes, hashes, and diagnostics are immutable.
- Published Frontend 0.1/0.2 request schemas and manifest cases are immutable.
- Contract identifiers select exact behavior; Frontend 0.3 uses `openstatspec-spss-syntax-frontend-v0.3`.
- Frontend 0.3 emits only `openstatspec-transformation-plan-v0.1` or `openstatspec-transformation-plan-v0.2`.
- A program inside the Plan 0.1 operation subset emits the exact Plan 0.1 object, even when its request contract is Frontend 0.3.
- Comments remain material to `source_hash` but emit no operation.
- Every undefined command, expression, coercion, comment form, or variable-list form fails closed.
- No task adds arithmetic, functions, missing predicates, string expressions, schema operations, case deletion/order, aggregation, joins, persistent copies, or rollback state.
- Specification publication precedes adapter claims; PHP and Python implementation work is planned separately after this contract is reviewed and published.
- Dolt remains caller-owned history; this frontend-only release does not change branch, HEAD, working-set, commit, or pre-provisioning rules.

## File Structure

- `src/openstatspec_specification/artifacts.py`: repository artifact loader, JSON Schema validation, canonical hashing, manifest reference validation, inherited-case expansion, and inventory reporting.
- `tests/test_contract_artifacts.py`: positive inventory checks and mutation-based fail-closed tests for schemas, hashes, IDs, references, inheritance, and release status.
- `tools/validate_repository.py`: invokes the artifact validator in addition to existing Dolt and repository controls.
- `pyproject.toml`: declares `jsonschema` and the pytest development dependency.
- `.github/workflows/ci.yml`: installs the package and runs pytest before repository validation.
- `transformation/spss-syntax-frontend-0.3.schema.json`: exact Frontend 0.3 request envelope; structurally identical to 0.2 except contract identity and schema metadata.
- `docs/spss-syntax-frontend-profile-0.3.md`: normative lexical, grammar, lowering, diagnostics, compatibility, and hashing rules.
- `conformance/spss-syntax-frontend-0.3.json`: inherited 0.1/0.2 cases, explicit supersession records, and 35 new independent golden cases.
- `examples/spss-syntax-transformation-0.3.md`: one readable program showing comments, `TO`, grouped format, `NOT`/not-equal, open recode ranges, and additive labels.
- `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `docs/spss-frontend-roadmap.md`: artifact index, release notes, milestone status, and adapter handoff gates.
- `docs/transformation-plan-profile-0.2.md`, `docs/spss-syntax-frontend-profile-0.2.md`, `docs/transformation-plan-sql-binding-0.2.md`: correct published `v0.3.0` status wording only; no normative edits.

---

### Task 1: Add the contract artifact validation foundation

**Files:**
- Create: `src/openstatspec_specification/artifacts.py`
- Create: `tests/test_contract_artifacts.py`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: `ArtifactValidationError`, `ArtifactInventory`, `canonical_json_bytes(value: object) -> bytes`, `source_hash(source_text: str) -> str`, and `validate_contract_artifacts(root: Path) -> ArtifactInventory`.
- Consumes: existing files below `transformation/`, `conformance/`, `sql/`, and `docs/`; no adapter code.

- [ ] **Step 1: Add a failing inventory test.**

Create `tests/test_contract_artifacts.py` with the existing released inventory as the first executable requirement:

```python
from __future__ import annotations

from pathlib import Path

from openstatspec_specification.artifacts import validate_contract_artifacts


ROOT = Path(__file__).resolve().parents[1]


def test_released_contract_artifact_inventory_is_valid() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.plan_cases == {"0.1": 4, "0.2": 26}
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44}
    assert inventory.binding_cases == {"0.1": 6, "0.2": 11}
```

- [ ] **Step 2: Run the focused test and confirm the missing-module failure.**

Run: `python3 -m pytest tests/test_contract_artifacts.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'openstatspec_specification.artifacts'`.

- [ ] **Step 3: Declare exact validation dependencies and CI setup.**

Change `pyproject.toml` to include:

```toml
dependencies = ["jsonschema>=4.23,<5"]

[project.optional-dependencies]
dev = ["pytest>=8,<9"]
```

In `.github/workflows/ci.yml`, insert these commands after `actions/setup-python` and before repository validation:

```yaml
      - run: python -m pip install --disable-pip-version-check -e ".[dev]"
      - run: python -m pytest
      - run: python tools/validate_repository.py
```

Remove the old duplicate standalone `python tools/validate_repository.py` step.

- [ ] **Step 4: Implement the loader, schema checks, top-level contracts, and unique IDs.**

Create `src/openstatspec_specification/artifacts.py` with these public types and constants:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


PLAN_MANIFESTS = {
    "0.1": "conformance/transformation-plan-0.1.json",
    "0.2": "conformance/transformation-plan-0.2.json",
}
FRONTEND_MANIFESTS = {
    "0.1": "conformance/spss-syntax-frontend-0.1.json",
    "0.2": "conformance/spss-syntax-frontend-0.2.json",
}
BINDING_MANIFESTS = {
    "0.1": "conformance/in-place-transformation-0.1.json",
    "0.2": "conformance/in-place-transformation-0.2.json",
}


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactInventory:
    plan_cases: Mapping[str, int]
    frontend_declared_cases: Mapping[str, int]
    frontend_effective_cases: Mapping[str, int]
    binding_cases: Mapping[str, int]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def source_hash(source_text: str) -> str:
    normalized = source_text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

Implement private helpers with these exact responsibilities:

```python
def _load_json(root: Path, relative: str) -> object:
    parts = relative.split("/")
    _require(
        not relative.startswith("/")
        and "\\" not in relative
        and all(part not in {"", ".", ".."} for part in parts),
        f"noncanonical artifact path: {relative}",
    )
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        _require(not current.is_symlink(), f"artifact path traverses symlink: {relative}")
    _require(candidate.is_file(), f"artifact is missing: {relative}")
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ArtifactValidationError(
            f"artifact cannot be decoded: {relative} ({type(error).__name__})"
        ) from None

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactValidationError(message)

def _resolve_manifest_reference(manifest_relative: str, reference: str) -> str:
    _require(
        isinstance(reference, str)
        and bool(reference)
        and not reference.startswith("/")
        and "\\" not in reference,
        f"noncanonical manifest reference: {reference!r}",
    )
    resolved: list[str] = []
    candidate = PurePosixPath(manifest_relative).parent / reference
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            _require(bool(resolved), f"manifest reference escapes repository root: {reference}")
            resolved.pop()
            continue
        resolved.append(part)
    _require(bool(resolved), f"manifest reference resolves to repository root: {reference}")
    return "/".join(resolved)

def _require_unique_case_ids(manifest: Mapping[str, object], context: str) -> None:
    cases = manifest.get("cases")
    _require(isinstance(cases, list), f"{context}: cases must be a list")
    seen: set[str] = set()
    for case in cases:
        _require(isinstance(case, dict), f"{context}: each case must be an object")
        case_id = case.get("id")
        _require(isinstance(case_id, str) and bool(case_id), f"{context}: case id must be a non-empty string")
        _require(case_id not in seen, f"{context}: duplicate case id: {case_id}")
        seen.add(case_id)

def _schema(root: Path, relative: str) -> Mapping[str, object]:
    value = _load_json(root, relative)
    _require(isinstance(value, dict), f"{relative}: schema must be an object")
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError as error:
        raise ArtifactValidationError(f"{relative}: invalid JSON Schema: {error.message}") from None
    return value
```

`validate_contract_artifacts()` must load all six existing manifests, require their exact `manifest_version`, `contract`, and relative schema fields, meta-validate all four referenced Plan/Frontend schemas, require unique case IDs, and return the released counts shown in Step 1. Convert `OSError`, `UnicodeError`, `JSONDecodeError`, `SchemaError`, and `ValidationError` into `ArtifactValidationError` without leaking unrelated filesystem data.

Resolve every manifest-owned schema or audit reference through
`_resolve_manifest_reference(manifest_relative, reference)` before passing the
result to `_load_json()`. Direct repository-relative loader calls continue to
reject `..`; only the resolver may consume and normalize manifest-relative
parent segments, and it must never permit escape above repository root.

- [ ] **Step 5: Add fail-closed tests for malformed schemas and duplicate IDs.**

Add this copy helper and tests:

```python
import json
import shutil

import pytest

from openstatspec_specification.artifacts import ArtifactValidationError


def copied_artifacts(tmp_path: Path) -> Path:
    for directory in ("conformance", "transformation", "sql", "docs"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    shutil.copy2(ROOT / "CHANGELOG.md", tmp_path / "CHANGELOG.md")
    shutil.copy2(ROOT / "ROADMAP.md", tmp_path / "ROADMAP.md")
    return tmp_path


def test_duplicate_manifest_case_id_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/transformation-plan-0.1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["cases"].append(manifest["cases"][0])
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="duplicate case id"):
        validate_contract_artifacts(root)


def test_invalid_json_schema_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "transformation/plan-0.1.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["type"] = "not-a-json-schema-type"
    path.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="invalid JSON Schema"):
        validate_contract_artifacts(root)
```

- [ ] **Step 6: Run the focused and full tests.**

Run:

```bash
python3 -m pip install --disable-pip-version-check -e ".[dev]"
python3 -m pytest tests/test_contract_artifacts.py -q
python3 -m pytest -q
```

Expected: all tests pass; inventory remains Plan `4/26`, Frontend `13/44`, Binding `6/11`.

- [ ] **Step 7: Commit the validation foundation.**

```bash
git add pyproject.toml .github/workflows/ci.yml src/openstatspec_specification/artifacts.py tests/test_contract_artifacts.py
git commit -m "test: validate contract artifact inventory"
```

### Task 2: Validate canonical hashes and cross-manifest references

**Files:**
- Modify: `src/openstatspec_specification/artifacts.py`
- Modify: `tests/test_contract_artifacts.py`
- Modify: `tools/validate_repository.py`

**Interfaces:**
- Consumes: Task 1 `validate_contract_artifacts()`, `canonical_json_bytes()`, and `source_hash()`.
- Produces: exact validation of plan hashes, frontend source hashes, referenced plans, binding references, canonical audit JSON, and failure-case shape.

- [ ] **Step 1: Add failing mutation tests for plan hash, source hash, and references.**

```python
@pytest.mark.parametrize(
    ("manifest_name", "field"),
    [
        ("transformation-plan-0.2.json", "expected_plan_hash"),
        ("spss-syntax-frontend-0.2.json", "expected_source_hash"),
    ],
)
def test_hash_mismatch_fails_closed(
    tmp_path: Path, manifest_name: str, field: str,
) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance" / manifest_name
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["cases"][0][field] = "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="hash mismatch"):
        validate_contract_artifacts(root)


def test_missing_frontend_plan_reference_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.2.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["cases"][0]["expected_plan_case"] = "absent-plan"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="unknown plan case"):
        validate_contract_artifacts(root)


def test_binding_plan_and_frontend_references_must_agree(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/in-place-transformation-0.2.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["cases"][0]["applied_plan_case"] = "strict-greater-than"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="binding reference mismatch"):
        validate_contract_artifacts(root)
```

- [ ] **Step 2: Run the focused tests and confirm all three mutations are accepted incorrectly.**

Run: `python3 -m pytest tests/test_contract_artifacts.py -q`

Expected: the three new tests fail because Task 1 does not inspect hashes or references.

- [ ] **Step 3: Implement Plan manifest validation.**

For every Plan manifest:

1. Index cases by ID.
2. Require `expected_error` to be either `null` or a non-empty string.
3. For successful cases, require a `plan` object, validate it against the manifest's schema, calculate `sha256(canonical_json_bytes(plan))`, and require exact lowercase `expected_plan_hash` equality.
4. For failing cases, require `expected_plan_hash` to be absent or `null`; retain the invalid plan as declarative negative input and do not require it to satisfy the plan schema.
5. Require the plan's `contract` to match the manifest contract for successful cases.

Add private helpers with these signatures:

```python
def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def _validate_plan_manifests(
    root: Path,
    manifests: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    """Return version -> case-id -> successful canonical plan case."""
```

- [ ] **Step 4: Implement Frontend request, source hash, and plan-reference validation.**

For each Frontend case:

1. Compute `source_hash(request["source_text"])` for every structurally readable request and require exact `expected_source_hash`.
2. Validate successful requests against `request_schema`.
3. For `plan_schema_invalid` failures, require request schema validation to fail; for other failures, require the request schema to pass.
4. Resolve successful expected plans from exactly one of `expected_plan`, `expected_plan_0_1`, `expected_plan_case`, or `expected_plan_case_0_1`.
5. Resolve `expected_plan_case` against the declared Plan manifest and `expected_plan_case_0_1` against Frontend 0.1's resolved expected plans.
6. Validate the resolved plan against the schema selected by its exact `contract`, recompute its canonical hash, and require equality with `expected_plan_hash`.
7. Require failing cases to omit expected plan objects, references, and hashes.

Use this exact resolver signature:

```python
def _resolve_frontend_plans(
    root: Path,
    manifests: Mapping[str, Mapping[str, object]],
    plan_cases: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Mapping[str, Mapping[str, object]]]:
    """Return version -> case-id -> resolved canonical plan for successes."""
```

- [ ] **Step 5: Implement In-Place reference and audit identity validation.**

For In-Place 0.2 cases containing `applied_plan_case` and
`applied_frontend_case`, require both references to exist, require the frontend
case to resolve to that exact plan case, and verify these audit fields when
present:

```python
expected_audit["plan_hash"] == plan_case["expected_plan_hash"]
expected_audit["source_hash"] == frontend_case["expected_source_hash"]
expected_audit["canonical_plan_json"].encode("utf-8") == canonical_json_bytes(plan_case["plan"])
expected_audit["operation_count"] == len(plan_case["plan"]["operations"])
```

Require every In-Place manifest case to have a unique ID and exact manifest
contract. Require every failing binding case to contain a non-empty
`expected_error` and `mutation_started: false`.

- [ ] **Step 6: Wire artifact validation into the repository command.**

In `tools/validate_repository.py`, import and call the validator after the
existing reusable Dolt validator and before phrase controls:

```python
from openstatspec_specification.artifacts import (  # noqa: E402
    ArtifactValidationError,
    validate_contract_artifacts,
)


if __name__ == "__main__":
    try:
        main()
        inventory = validate_contract_artifacts(ROOT)
        validate_repository_controls()
        print(
            "Validated contract artifacts: "
            f"Plan {dict(inventory.plan_cases)}, "
            f"Frontend {dict(inventory.frontend_effective_cases)}, "
            f"Binding {dict(inventory.binding_cases)}."
        )
    except (DoltDeclarationError, ArtifactValidationError) as error:
        raise SystemExit(str(error)) from error
```

- [ ] **Step 7: Run mutation tests and the complete repository gate.**

Run:

```bash
python3 -m pytest tests/test_contract_artifacts.py -q
python3 -m pytest -q
python3 tools/validate_repository.py
```

Expected: all tests pass; the repository command prints all six released inventory counts and exits zero.

- [ ] **Step 8: Commit canonical artifact validation.**

```bash
git add src/openstatspec_specification/artifacts.py tests/test_contract_artifacts.py tools/validate_repository.py
git commit -m "test: verify transformation artifact identity"
```

### Task 3: Repair release status and lock command classification

**Files:**
- Modify: `src/openstatspec_specification/artifacts.py`
- Modify: `tests/test_contract_artifacts.py`
- Modify: `docs/transformation-plan-profile-0.2.md`
- Modify: `docs/spss-syntax-frontend-profile-0.2.md`
- Modify: `docs/transformation-plan-sql-binding-0.2.md`
- Modify: `CHANGELOG.md`
- Modify: `ROADMAP.md`
- Verify: `docs/spss-frontend-roadmap.md`

**Interfaces:**
- Consumes: published `v0.3.0` tag target `cd8f198c68b849eb8ed018a894670a0904c2181d` and the command-classification table already in `docs/spss-frontend-roadmap.md`.
- Produces: `validate_release_metadata(root: Path) -> None` and consistent released status for all 0.2 profiles.

- [ ] **Step 1: Add a failing release-status consistency test.**

```python
from openstatspec_specification.artifacts import validate_release_metadata


def test_v030_profile_status_is_consistently_released() -> None:
    validate_release_metadata(ROOT)


def test_release_candidate_wording_fails_for_published_profile(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "docs/spss-syntax-frontend-profile-0.2.md"
    text = path.read_text(encoding="utf-8").replace(
        "Status: released in OpenStatSpec `v0.3.0`",
        "Status: release candidate for OpenStatSpec `v0.3.0`",
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="release status"):
        validate_release_metadata(root)
```

- [ ] **Step 2: Run the test and confirm current release-candidate wording fails.**

Run: `python3 -m pytest tests/test_contract_artifacts.py -q`

Expected: `test_v030_profile_status_is_consistently_released` fails because three published 0.2 documents still say release candidate.

- [ ] **Step 3: Implement exact release metadata validation.**

Add:

```python
V030_COMMIT = "cd8f198c68b849eb8ed018a894670a0904c2181d"
V030_PROFILE_DOCUMENTS = (
    "docs/transformation-plan-profile-0.2.md",
    "docs/spss-syntax-frontend-profile-0.2.md",
    "docs/transformation-plan-sql-binding-0.2.md",
)


def validate_release_metadata(root: Path) -> None:
    for relative in V030_PROFILE_DOCUMENTS:
        text = (root / relative).read_text(encoding="utf-8")
        _require(
            "Status: released in OpenStatSpec `v0.3.0`" in text,
            f"{relative}: release status is inconsistent with v0.3.0",
        )
        _require(
            "release candidate for the planned OpenStatSpec `v0.3.0`" not in text,
            f"{relative}: stale release status remains",
        )
    roadmap = (root / "ROADMAP.md").read_text(encoding="utf-8")
    _require("`v0.3.0` is the" in roadmap, "ROADMAP release tag mismatch")
    _require("current public specification release and is immutable" in roadmap, "ROADMAP release status mismatch")
    _require(V030_COMMIT in roadmap, "ROADMAP v0.3.0 commit mismatch")
```

Extend the `tools/validate_repository.py` artifact import with
`validate_release_metadata`, then call `validate_release_metadata(ROOT)` from
`validate_repository_controls()`.

- [ ] **Step 4: Correct only release bookkeeping text.**

Replace each 0.2 profile's status paragraph with:

```markdown
Status: released in OpenStatSpec `v0.3.0` at immutable specification commit
`cd8f198c68b849eb8ed018a894670a0904c2181d`.
```

In `CHANGELOG.md`, replace the conditional release-preparation paragraph under
`v0.3.0` with a factual released statement naming the same tag and commit. Do
not edit any normative command, plan, binding, or diagnostic text.

- [ ] **Step 5: Record completed PHP downstream evidence without changing specification gates.**

In `ROADMAP.md` section 9, mark the PHP item complete and cite:

```markdown
5. [x] PHP pinned specification `v0.3.0` commit
   `cd8f198c68b849eb8ed018a894670a0904c2181d`, passed its complete PHP
   8.4/8.5 and PostgreSQL/MySQL/MariaDB/Dolt matrix, and published adapter
   [v0.6.0](https://github.com/OpenStatSpec/php/releases/tag/v0.6.0).
```

Leave Python status unchanged unless its own exact release evidence is independently verified in that task.

- [ ] **Step 6: Verify the public command-classification table is complete.**

Require `docs/spss-frontend-roadmap.md` to contain all four boundary phrases:

```python
classification = (root / "docs/spss-frontend-roadmap.md").read_text(encoding="utf-8")
for phrase in (
    "Frontend 0.3, Plan 0.1/0.2",
    "New Plan/Frontend/Binding generation",
    "Separate case-transformation profile",
    "Explicit non-goal",
):
    _require(phrase in classification, f"SPSS classification is missing {phrase}")
```

- [ ] **Step 7: Run all gates and commit bookkeeping.**

Run:

```bash
python3 -m pytest -q
python3 tools/validate_repository.py
git diff --check
```

Then commit:

```bash
git add src/openstatspec_specification/artifacts.py tests/test_contract_artifacts.py docs/transformation-plan-profile-0.2.md docs/spss-syntax-frontend-profile-0.2.md docs/transformation-plan-sql-binding-0.2.md CHANGELOG.md ROADMAP.md
git commit -m "docs: align v0.3.0 release status"
```

### Task 4: Define the Frontend 0.3 request contract and normative grammar

**Files:**
- Create: `transformation/spss-syntax-frontend-0.3.schema.json`
- Create: `docs/spss-syntax-frontend-profile-0.3.md`
- Modify: `src/openstatspec_specification/artifacts.py`
- Modify: `tests/test_contract_artifacts.py`

**Interfaces:**
- Produces: request contract `openstatspec-spss-syntax-frontend-v0.3` and its exact Draft 2020-12 schema.
- Consumes: unchanged Frontend 0.2 input-schema fields and unchanged Plan 0.1/0.2 contracts.

- [ ] **Step 1: Add failing schema inventory tests.**

```python
def test_frontend_03_request_schema_is_registered() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert "0.3" in inventory.frontend_declared_cases


def test_frontend_03_schema_changes_only_contract_identity() -> None:
    old = json.loads((ROOT / "transformation/spss-syntax-frontend-0.2.schema.json").read_text())
    new = json.loads((ROOT / "transformation/spss-syntax-frontend-0.3.schema.json").read_text())
    assert new["$id"].endswith("spss-syntax-frontend-0.3.schema.json")
    assert new["title"] == "OpenStatSpec SPSS-like Syntax Frontend Request 0.3"
    assert new["properties"]["contract"]["const"] == "openstatspec-spss-syntax-frontend-v0.3"
    for document in (old, new):
        document.pop("$id")
        document.pop("title")
        document["properties"]["contract"].pop("const")
    assert new == old
```

- [ ] **Step 2: Run the test and confirm the 0.3 schema/manifest is absent.**

Run: `python3 -m pytest tests/test_contract_artifacts.py -q`

Expected: failure because no Frontend 0.3 schema or registered manifest exists.

- [ ] **Step 3: Create the exact Frontend 0.3 request schema.**

Copy Frontend 0.2 structurally and change only:

```json
{
  "$id": "https://openstatspec.org/schemas/spss-syntax-frontend-0.3.schema.json",
  "title": "OpenStatSpec SPSS-like Syntax Frontend Request 0.3",
  "properties": {
    "contract": {"const": "openstatspec-spss-syntax-frontend-v0.3"}
  }
}
```

Retain all 0.2 input fields and `$defs`, including ordered variables, storage
kind, variable/value labels, format family/width/decimals, and measurement
level. Do not add missing rules or physical identifiers in 0.3.

- [ ] **Step 4: Write the normative 0.3 profile with exact grammar boundaries.**

Create `docs/spss-syntax-frontend-profile-0.3.md` with these sections and rules:

```text
Status and boundary
Compatibility and output-plan selection
Comments and source identity
Existing-variable lists
Predicate aliases and NOT lowering
Open-ended RECODE ranges
ADD VALUE LABELS
Failure contract
Conformance
```

Include this bounded grammar:

```text
existing-variable-list := existing-variable
                          ((existing-variable | TO existing-variable))*
comparison-operator    := "=" | "<" | "<=" | ">" | ">="
                          | "NE" | "<>" | "~="
predicate              := comparison | "(" predicate ")"
                          | NOT predicate
                          | predicate AND predicate
                          | predicate OR predicate
open-range             := LOWEST THRU finite-number
                          | finite-number THRU HIGHEST
                          | LOWEST THRU HIGHEST
```

Normatively require:

- leading-star comments only when `*` is the first non-whitespace token at a command boundary, ending at the next command period;
- `COMMENT` command comments ending at their command period;
- non-nested `/* ... */` comments wherever whitespace is legal; unterminated or nested forms return `spss_syntax_error`;
- raw comments remain in LF-normalized source hashing and emit no operation;
- a comment-only program returns `spss_syntax_error` because plans cannot have zero operations;
- `TO` expands inclusively by current ordered input-schema state, not by variable spelling or numeric suffix;
- reverse ranges return `invalid_variable_range`; absent endpoints return `unknown_variable`; `TO` is forbidden for generated `INTO` target sequences;
- `NE`, `<>`, and `~=` lower to ordered `< OR >` comparisons;
- `NOT` is accepted only over the existing comparison/boolean grammar and lowers recursively with comparison complements and De Morgan's laws, preserving SQL three-valued truth and canonical same-operator flattening;
- open ranges use `ffefffffffffffff` for negative maximum finite binary64 and `7fefffffffffffff` for positive maximum finite binary64; SQL NULL/system missing is not included;
- `ADD VALUE LABELS` updates an existing typed value at its current ordinal and appends new values in source order, then emits one complete `replace_value_labels` operation per variable;
- comments, `TO`, grouped syntax, open ranges, and additive labels remain in the Plan 0.1 output subset; predicate aliases/`NOT` require existing Plan 0.2 `conditional_assign` syntax.

- [ ] **Step 5: Register Frontend 0.3 in the validator with an empty draft manifest.**

Add `"0.3": "conformance/spss-syntax-frontend-0.3.json"` to
`FRONTEND_MANIFESTS`. Create the manifest in Task 5; for this task, keep the
schema/profile changes staged but do not commit until Task 5 supplies a valid
manifest and the repository is green.

### Task 5: Define inherited compatibility and supersession

**Files:**
- Create: `conformance/spss-syntax-frontend-0.3.json`
- Modify: `src/openstatspec_specification/artifacts.py`
- Modify: `tests/test_contract_artifacts.py`
- Test: `conformance/spss-syntax-frontend-0.1.json`
- Test: `conformance/spss-syntax-frontend-0.2.json`

**Interfaces:**
- Consumes: Task 4 request schema and profile.
- Produces: `inherited_manifests` semantics and effective-case expansion for Frontend 0.3.

- [ ] **Step 1: Add failing inheritance tests.**

```python
def test_frontend_03_inherits_released_cases_under_new_request_contract() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 2
    assert inventory.frontend_effective_cases["0.3"] == 57


def test_inherited_manifest_path_escape_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.3.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["inherited_manifests"][0]["manifest"] = "../outside.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="inherited manifest"):
        validate_contract_artifacts(root)
```

- [ ] **Step 2: Create the initial Frontend 0.3 manifest.**

Use this exact top-level shape:

```json
{
  "manifest_version": "0.3",
  "profile": "OpenStatSpec SPSS-like Syntax Frontend 0.3",
  "contract": "openstatspec-spss-syntax-frontend-v0.3",
  "plan_contracts": [
    "openstatspec-transformation-plan-v0.1",
    "openstatspec-transformation-plan-v0.2"
  ],
  "request_schema": "../transformation/spss-syntax-frontend-0.3.schema.json",
  "plan_schemas": {
    "openstatspec-transformation-plan-v0.1": "../transformation/plan-0.1.schema.json",
    "openstatspec-transformation-plan-v0.2": "../transformation/plan-0.2.schema.json"
  },
  "inherited_manifests": [
    {
      "manifest": "spss-syntax-frontend-0.1.json",
      "request_contract_override": "openstatspec-spss-syntax-frontend-v0.3",
      "superseded_cases": {
        "reject-comment-command": "reject-comment-only-program",
        "reject-inline-comment": "inline-block-comment-is-ignored"
      }
    },
    {
      "manifest": "spss-syntax-frontend-0.2.json",
      "request_contract_override": "openstatspec-spss-syntax-frontend-v0.3",
      "superseded_cases": {}
    }
  ],
  "cases": [
    {
      "id": "reject-comment-only-program",
      "request": {
        "contract": "openstatspec-spss-syntax-frontend-v0.3",
        "input_alias": "parent",
        "input_schema": {"variables": [{"name": "q1", "storage_kind": "numeric"}]},
        "source_text": "* comment."
      },
      "expected_source_hash": "8bfac9af8d0884b68cebc65a42360871592dd6e4e9cbead0bdf7029b6b64f4fc",
      "expected_error": "spss_syntax_error"
    },
    {
      "id": "inline-block-comment-is-ignored",
      "request": {
        "contract": "openstatspec-spss-syntax-frontend-v0.3",
        "input_alias": "parent",
        "input_schema": {"variables": [{"name": "q1", "storage_kind": "numeric"}]},
        "source_text": "RECODE q1 (1 = 0) /* comment */."
      },
      "expected_plan_contract": "openstatspec-transformation-plan-v0.1",
      "expected_plan_case_0_1": "in-place-recode-default-copy",
      "expected_plan_hash": "091a2daeb490deb3369cba83b5197d1c43767432c9a04cbf3e55bd69296b67a8",
      "expected_source_hash": "3c4ef459e9a2021100ef166ef0038c5f920b126d916db4c7273537d21b256f65",
      "expected_error": null
    }
  ]
}
```

The initial effective count is 57: 11 unchanged Frontend 0.1 cases, all 44
Frontend 0.2 cases, and two declared replacements. Expanded IDs are namespaced
as `0.1/<case-id>` and `0.2/<case-id>` so repeated IDs across manifests remain
distinct.

- [ ] **Step 3: Implement inherited-case expansion and validation.**

Add:

```python
def _expand_frontend_cases(
    root: Path,
    version: str,
    manifest: Mapping[str, object],
    manifests: Mapping[str, Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    """Return inherited cases with contract override followed by declared cases."""
```

Require inherited paths to be canonical filenames in `conformance/`, target
older registered Frontend manifests only, and use the current manifest's exact
contract as `request_contract_override`. Deep-copy each inherited case and
replace only `request.contract`; source text, expected source hash, plan,
expected plan hash, and expected diagnostic remain unchanged.

`superseded_cases` maps an inherited case ID to a declared 0.3 replacement case
ID. Require every old ID to exist, every replacement ID to exist in declared
cases, and every replacement to use the same `source_text`. Exclude superseded
old cases from the effective set. Reject inheritance cycles and duplicate
expanded IDs.

- [ ] **Step 4: Run the focused tests and complete Task 4/5 commit.**

Run:

```bash
python3 -m pytest tests/test_contract_artifacts.py -q
python3 tools/validate_repository.py
```

Expected: Frontend declared counts are `13/44/2`; Frontend effective counts are `13/44/57`.

Commit:

```bash
git add transformation/spss-syntax-frontend-0.3.schema.json docs/spss-syntax-frontend-profile-0.3.md conformance/spss-syntax-frontend-0.3.json src/openstatspec_specification/artifacts.py tests/test_contract_artifacts.py
git commit -m "spec: define SPSS frontend 0.3 contract"
```

### Task 6: Add comments, variable lists, and grouped forms

**Files:**
- Modify: `conformance/spss-syntax-frontend-0.3.json`
- Modify: `tests/test_contract_artifacts.py`

**Interfaces:**
- Consumes: Task 5 inheritance and supersession format.
- Produces: 14 declared cases covering comments and schema-ordered variable-list expansion.

- [ ] **Step 1: Add a failing exact-count and supersession test.**

```python
def test_frontend_03_comment_and_varlist_case_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 14
    assert inventory.frontend_effective_cases["0.3"] == 69
```

The effective count is `13 + 44 - 2 superseded + 14 = 69`.

- [ ] **Step 2: Add the four remaining exact comment cases.**

Add these case IDs and outcomes:

```text
comment-command-before-recode                 success, exact Plan 0.1 recode
leading-star-comment-before-recode            success, same Plan 0.1 recode
comments-change-source-hash-not-plan-hash      success, same plan with a distinct source hash
reject-unterminated-inline-comment             spss_syntax_error
```

For each success, embed or reference an exact existing Plan 0.1 case and include
an independently calculated lowercase source hash. A representative case is:

```json
{
  "id": "leading-star-comment-before-recode",
  "request": {
    "contract": "openstatspec-spss-syntax-frontend-v0.3",
    "input_alias": "parent",
    "input_schema": {"variables": [{"name": "q1", "storage_kind": "numeric"}]},
    "source_text": "* recode one to zero.\nRECODE q1 (1 = 0)."
  },
  "expected_plan_contract": "openstatspec-transformation-plan-v0.1",
  "expected_plan_case_0_1": "in-place-recode-default-copy",
  "expected_plan_hash": "091a2daeb490deb3369cba83b5197d1c43767432c9a04cbf3e55bd69296b67a8",
  "expected_source_hash": "dddbaf0dd69f364ccc895d0d3b65daa63208edfd9b4e8e2112f915f1e73e5d70",
  "expected_error": null
}
```

Calculate each source hash with:

```bash
python3 -c 'from openstatspec_specification.artifacts import source_hash; print(source_hash("* recode one to zero.\nRECODE q1 (1 = 0)."))'
```

Write the printed lowercase digest into the manifest; do not calculate hashes at adapter runtime.

- [ ] **Step 3: Verify the two released comment failures remain explicitly superseded.**

Confirm Frontend 0.1 inheritance metadata remains:

```json
"superseded_cases": {
  "reject-comment-command": "reject-comment-only-program",
  "reject-inline-comment": "inline-block-comment-is-ignored"
}
```

The replacement cases use the exact old source text. The first remains a
failure but changes from unsupported command to empty-program syntax error; the
second becomes a success. Do not edit the released 0.1 manifest.

- [ ] **Step 4: Add eight variable-list/group cases.**

Add these exact IDs:

```text
recode-to-expands-dictionary-order
value-labels-to-expands-dictionary-order
formats-grouped-to-expands-source-order
variable-level-to-expands-source-order
to-sees-variable-created-by-preceding-command
reject-reversed-to-range
reject-unknown-to-endpoint
reject-to-generated-into-targets
```

Use input order `a, middle, c, outside` and prove `a TO c` expands to exactly
`a, middle, c`, regardless of spelling. `FORMATS a TO c (F8.2)` emits three
ordered `set_format` operations. `VARIABLE LEVEL a TO c (NOMINAL)` emits three
ordered `set_measurement_level` operations. `COMPUTE appended = a.` followed by
`FORMATS c TO appended (F8.2).` proves current command-order schema state.

Use stable errors:

```text
reversed existing-variable range -> invalid_variable_range
absent endpoint                  -> unknown_variable
TO in generated INTO targets    -> spss_syntax_error
```

- [ ] **Step 5: Validate all explicit source and plan hashes.**

Run:

```bash
python3 -m pytest tests/test_contract_artifacts.py -q
python3 tools/validate_repository.py
```

Expected: Frontend 0.3 declared/effective counts are `14/69`; no Plan manifest count or hash changes.

- [ ] **Step 6: Commit comments and variable-list fixtures.**

```bash
git add conformance/spss-syntax-frontend-0.3.json tests/test_contract_artifacts.py
git commit -m "spec: add frontend comments and variable lists"
```

### Task 7: Add predicate aliases and open recode ranges

**Files:**
- Modify: `conformance/spss-syntax-frontend-0.3.json`
- Modify: `tests/test_contract_artifacts.py`
- Modify: `docs/spss-syntax-frontend-profile-0.3.md`

**Interfaces:**
- Consumes: unchanged Plan 0.1 range nodes and Plan 0.2 comparison/boolean nodes.
- Produces: 14 declared cases for not-equal/NOT lowering and finite open-range lowering.

- [ ] **Step 1: Add a failing exact-count test.**

```python
def test_frontend_03_predicate_and_open_range_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 28
    assert inventory.frontend_effective_cases["0.3"] == 83
```

- [ ] **Step 2: Add eight exact predicate cases.**

```text
ne-keyword-lowers-to-less-or-greater
angle-not-equal-lowers-to-less-or-greater
tilde-not-equal-lowers-to-less-or-greater
not-equality-lowers-to-less-or-greater
not-nested-and-lowers-by-de-morgan
double-not-retains-canonical-comparison
reject-not-numeric-truthiness
reject-chained-comparison
```

Use this exact canonical lowering table in profile and cases:

```text
NOT (left = right)  -> (left < right OR left > right)
NOT (left < right)  -> left >= right
NOT (left <= right) -> left > right
NOT (left > right)  -> left <= right
NOT (left >= right) -> left < right
NOT (a AND b)       -> NOT a OR NOT b
NOT (a OR b)        -> NOT a AND NOT b
```

`NE`, `<>`, and `~=` all emit the same ordered n-ary `or` node containing `<`
then `>`. Apply existing maximal same-operator flattening after recursive
lowering. Do not constant-fold or reorder. Fail numeric truthiness such as
`IF (NOT source_a) ...` with `expression_type_unsupported`; fail
`a < b < c` with `spss_syntax_error`.

- [ ] **Step 3: Add six exact open-range cases.**

```text
recode-lowest-thru-upper
recode-lower-thru-highest
recode-lowest-thru-highest
reject-string-open-range
reject-highest-as-lower-endpoint
reject-lowest-as-upper-endpoint
```

Expected finite endpoints are exact typed values:

```json
{"type": "binary64", "bits": "ffefffffffffffff"}
{"type": "binary64", "bits": "7fefffffffffffff"}
```

String open ranges fail `type_mismatch`. `HIGHEST THRU 1` and
`1 THRU LOWEST` fail `spss_syntax_error`. System missing remains unmatched
unless another explicit rule handles `SYSMIS`.

- [ ] **Step 4: Run exact identity gates.**

Run:

```bash
python3 -m pytest tests/test_contract_artifacts.py -q
python3 tools/validate_repository.py
```

Expected: Frontend 0.3 declared/effective counts are `28/83`; all Plan 0.1/0.2 hashes remain unchanged.

- [ ] **Step 5: Commit predicate and range fixtures.**

```bash
git add conformance/spss-syntax-frontend-0.3.json tests/test_contract_artifacts.py docs/spss-syntax-frontend-profile-0.3.md
git commit -m "spec: add frontend predicates and open ranges"
```

### Task 8: Add additive value-label semantics

**Files:**
- Modify: `conformance/spss-syntax-frontend-0.3.json`
- Modify: `tests/test_contract_artifacts.py`
- Modify: `docs/spss-syntax-frontend-profile-0.3.md`

**Interfaces:**
- Consumes: Frontend request `input_schema.variables[].value_labels` and existing Plan `replace_value_labels`.
- Produces: seven declared cases and deterministic ordered merge semantics.

- [ ] **Step 1: Add the final failing inventory test.**

```python
def test_frontend_03_final_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44, "0.3": 35}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44, "0.3": 90}
```

- [ ] **Step 2: Add seven exact additive-label cases.**

```text
add-value-labels-preserves-existing-and-appends
add-value-labels-replaces-existing-label-in-place
value-labels-then-add-value-labels-uses-ordered-state
add-value-labels-multiple-variable-group
add-string-value-labels
reject-add-value-labels-duplicate-source-value
reject-add-value-labels-type-mismatch
```

Use this normative merge algorithm:

```python
def merge_labels(existing, additions):
    result = list(existing)
    index = {canonical_typed_value(item["value"]): position for position, item in enumerate(result)}
    seen_additions = set()
    for addition in additions:
        key = canonical_typed_value(addition["value"])
        if key in seen_additions:
            raise duplicate_value_label
        seen_additions.add(key)
        if key in index:
            result[index[key]] = addition
        else:
            index[key] = len(result)
            result.append(addition)
    return result
```

This is specification pseudocode, not an implementation API. Typed values use
their exact canonical identity; numeric positive zero canonicalization and
string exactness remain inherited. Emit one complete `replace_value_labels`
operation per variable in group/source order. A preceding `VALUE LABELS`
replaces state; a following `ADD VALUE LABELS` merges against that replacement,
not against the original request.

- [ ] **Step 3: Prove Plan 0.1 output selection.**

At least four successful additive-label cases contain no Plan 0.2 operation and
must declare:

```json
"expected_plan_contract": "openstatspec-transformation-plan-v0.1"
```

Their expected plans contain only complete ordered `replace_value_labels`
operations and validate against `plan-0.1.schema.json`.

- [ ] **Step 4: Run the final manifest inventory and identity checks.**

Run:

```bash
python3 -m pytest tests/test_contract_artifacts.py -q
python3 -m pytest -q
python3 tools/validate_repository.py
```

Expected: Plan `4/26`, Frontend declared `13/44/35`, Frontend effective
`13/44/90`, Binding `6/11`; all hashes and references validate.

- [ ] **Step 5: Commit additive-label fixtures.**

```bash
git add conformance/spss-syntax-frontend-0.3.json tests/test_contract_artifacts.py docs/spss-syntax-frontend-profile-0.3.md
git commit -m "spec: define additive value label syntax"
```

### Task 9: Complete examples, release notes, and adapter handoff

**Files:**
- Create: `examples/spss-syntax-transformation-0.3.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `ROADMAP.md`
- Modify: `docs/spss-frontend-roadmap.md`
- Modify: `docs/spss-syntax-frontend-profile-0.3.md`
- Modify: `src/openstatspec_specification/artifacts.py`
- Modify: `tests/test_contract_artifacts.py`

**Interfaces:**
- Consumes: complete 0.3 schema/profile/manifest and validated counts.
- Produces: specification release-candidate documentation and exact downstream adapter claim gates.

- [ ] **Step 1: Add failing documentation presence checks.**

```python
def test_frontend_03_release_candidate_documentation_is_complete() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    example = (ROOT / "examples/spss-syntax-transformation-0.3.md").read_text(encoding="utf-8")
    assert "spss-syntax-frontend-0.3.schema.json" in readme
    assert "SPSS Syntax Frontend 0.3" in changelog
    assert "Frontend 0.3" in roadmap
    assert "ADD VALUE LABELS" in example
    assert "Plan 0.1/0.2" in example
```

- [ ] **Step 2: Write one complete 0.3 example.**

Use one exact program whose corresponding manifest cases already prove each
production independently:

```spss
* Normalize the selected score block.
RECODE score_a TO score_c (LOWEST THRU 0 = 0) (1 THRU HIGHEST = 1).
ADD VALUE LABELS score_a TO score_c 0 'Non-positive' 1 'Positive'.
FORMATS score_a TO score_c (F1.0).
IF (NOT (score_a = score_b)) mismatch = 1.
EXECUTE.
```

The example must state that `mismatch` is an existing numeric target, explain
dictionary-order `TO`, finite open-range lowering, complete additive-label
replacement, `< OR >` lowering, source hashing with comments, Plan 0.1/0.2
selection, and unchanged SQL/Dolt binding policy.

- [ ] **Step 3: Update the artifact index and Unreleased changelog.**

In `README.md`, list the 0.3 profile, schema, and conformance manifest beside
0.1/0.2. In `CHANGELOG.md` under Unreleased record:

- Frontend 0.3 is a release candidate, not a published stable claim.
- It adds comments, existing-variable `TO`, grouped forms, predicate aliases and
  bounded `NOT`, open recode ranges, and additive value labels.
- It emits only immutable Plan 0.1/0.2 and adds no SQL binding operation.
- Repository validation now covers all Plan/Frontend/Binding schemas,
  manifests, references, and hashes.

- [ ] **Step 4: Mark only completed roadmap milestones.**

In `ROADMAP.md` section 7, mark the Frontend 0.3 specification item complete
only after schema, profile, 35 declared cases, inherited compatibility, and
repository validation are all present. Leave adapter implementation and all
later expression/schema/case/group milestones unchecked.

In `docs/spss-frontend-roadmap.md`, mark Milestone 0 and Milestone 1 as
specification-complete while stating that adapter claims remain pending and
separately gated.

- [ ] **Step 5: Add exact adapter handoff gates to the 0.3 profile.**

Require an adapter claim to:

1. pin the exact future specification release commit;
2. accept only the exact Frontend 0.3 request contract for this suite;
3. run all 90 effective Frontend 0.3 cases;
4. preserve every inherited Plan 0.1/0.2 object and hash;
5. pass all 35 declared cases with exact source/plan hashes and diagnostics;
6. continue running existing Plan 0.1/0.2 and In-Place 0.1/0.2 suites;
7. keep MySQL/MariaDB/Dolt pre-provisioning and Dolt caller-owned commit policy unchanged.

State explicitly that adapter evidence does not block specification publication.

- [ ] **Step 6: Promote the 0.3 profile from draft to release candidate.**

Only after every prior task is green, change its status line to:

```markdown
Status: release candidate for the next OpenStatSpec minor release. This profile
is not published stable until a protected or signed specification tag targets
its exact reviewed commit and tag-context CI passes.
```

Do not choose the final specification release number in this implementation
task; release maintainers select it from the complete set of included normative
changes.

- [ ] **Step 7: Run final specification verification.**

Run:

```bash
python3 -m pytest -q
python3 tools/validate_repository.py
git diff --check
git status --short
```

Expected: all pytest tests pass, validator reports Plan `4/26`, Frontend
declared `13/44/35`, Frontend effective `13/44/90`, Binding `6/11`, diff check
is clean, and status lists only intended release-candidate documentation.

- [ ] **Step 8: Commit release-candidate documentation.**

```bash
git add examples/spss-syntax-transformation-0.3.md README.md CHANGELOG.md ROADMAP.md docs/spss-frontend-roadmap.md docs/spss-syntax-frontend-profile-0.3.md src/openstatspec_specification/artifacts.py tests/test_contract_artifacts.py
git commit -m "docs: prepare SPSS frontend 0.3 candidate"
```

### Task 10: Review and publish the specification branch

**Files:**
- Verify: all files changed by Tasks 1-9

**Interfaces:**
- Consumes: complete specification candidate and green repository checks.
- Produces: reviewable branch/PR; no specification tag and no adapter claim.

- [ ] **Step 1: Review the complete contract diff.**

Run:

```bash
git status --short --branch
git diff origin/main...HEAD --stat
git diff origin/main...HEAD -- transformation docs conformance src tests tools README.md CHANGELOG.md ROADMAP.md pyproject.toml .github/workflows/ci.yml
git log --oneline origin/main..HEAD
```

Confirm no published 0.1/0.2 schema or manifest changed by running:

```bash
git diff --exit-code origin/main...HEAD -- \
  transformation/plan-0.1.schema.json \
  transformation/plan-0.2.schema.json \
  transformation/spss-syntax-frontend-0.1.schema.json \
  transformation/spss-syntax-frontend-0.2.schema.json \
  conformance/transformation-plan-0.1.json \
  conformance/transformation-plan-0.2.json \
  conformance/spss-syntax-frontend-0.1.json \
  conformance/spss-syntax-frontend-0.2.json \
  conformance/in-place-transformation-0.1.json \
  conformance/in-place-transformation-0.2.json
```

Expected: exit zero and no diff for every published artifact.

- [ ] **Step 2: Run the final clean-checkout gate.**

Create an isolated clean checkout of `HEAD`, install `.[dev]`, and run:

```bash
python3 -m pytest -q
python3 tools/validate_repository.py
```

Expected: all checks pass without depending on sibling adapter repositories.

- [ ] **Step 3: Push and create a specification PR.**

```bash
git push -u origin agent/spss-frontend-03
gh pr create --repo OpenStatSpec/specification \
  --base main \
  --head agent/spss-frontend-03 \
  --title "Define SPSS syntax frontend 0.3" \
  --body $'Defines the bounded SPSS Syntax Frontend 0.3 contract.\n\n- Emits only immutable Plan 0.1/0.2 objects.\n- Adds 35 declared and 90 effective frontend cases.\n- Preserves all published 0.1/0.2 artifacts and hashes.\n- Adds repository-owned schema, reference, and hash validation.\n\nVerification: `python3 -m pytest -q` and `python3 tools/validate_repository.py`.'
```

The PR body must list contract boundaries, exact declared/effective case counts,
immutable older-artifact verification, validator/test commands, and downstream
adapter gates. Do not create a specification tag or GitHub release in this task.
