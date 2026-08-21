from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from openstatspec_specification.artifacts import ArtifactValidationError
from openstatspec_specification.artifacts import canonical_json_bytes
from openstatspec_specification.artifacts import validate_release_metadata
from openstatspec_specification.artifacts import validate_contract_artifacts
from openstatspec_specification.artifacts import source_hash


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_03_final_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44, "0.3": 35}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44, "0.3": 90}


def test_released_contract_artifact_inventory_is_valid() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.plan_cases == {"0.1": 4, "0.2": 26}
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44, "0.3": 35}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44, "0.3": 90}
    assert inventory.binding_cases == {"0.1": 6, "0.2": 11}


def test_frontend_03_request_schema_is_registered() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert "0.3" in inventory.frontend_declared_cases


def test_frontend_03_predicate_and_open_range_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 35
    assert inventory.frontend_effective_cases["0.3"] == 90


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


def test_frontend_03_inherits_released_cases_under_new_request_contract() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 35
    assert inventory.frontend_effective_cases["0.3"] == 90


def test_frontend_03_comment_and_varlist_case_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 35
    assert inventory.frontend_effective_cases["0.3"] == 90


def test_value_labels_then_add_value_labels_keeps_both_ordered_replacements() -> None:
    manifest = json.loads(
        (ROOT / "conformance/spss-syntax-frontend-0.3.json").read_text(encoding="utf-8")
    )
    case = next(
        case
        for case in manifest["cases"]
        if case["id"] == "value-labels-then-add-value-labels-uses-ordered-state"
    )
    plan = case["expected_plan_0_1"]
    assert [operation["op"] for operation in plan["operations"]] == [
        "replace_value_labels",
        "replace_value_labels",
    ]
    assert plan["operations"][0]["labels"][0]["label"] == "Five"
    assert plan["operations"][1]["labels"][-1]["label"] == "Two"
    assert case["expected_source_hash"] == source_hash(case["request"]["source_text"])
    assert case["expected_plan_hash"] == hashlib.sha256(
        canonical_json_bytes(plan)
    ).hexdigest()


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


def test_inherited_manifest_path_escape_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.3.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["inherited_manifests"][0]["manifest"] = "../outside.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="inherited manifest"):
        validate_contract_artifacts(root)


@pytest.mark.parametrize("artifact_type", ["directory", "fifo", "symlink"])
def test_existing_frontend_03_manifest_artifact_type_fails_closed(
    tmp_path: Path, artifact_type: str,
) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.3.json"
    path.unlink()
    if artifact_type == "directory":
        path.mkdir()
    elif artifact_type == "fifo":
        os.mkfifo(path)
    else:
        path.symlink_to(root / "conformance")
    with pytest.raises(ArtifactValidationError, match="artifact"):
        validate_contract_artifacts(root)


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


def test_release_document_symlink_fails_closed(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "docs/spss-syntax-frontend-profile-0.2.md"
    path.unlink()
    path.symlink_to(root / "docs/transformation-plan-profile-0.2.md")
    with pytest.raises(ArtifactValidationError, match="artifact path traverses symlink"):
        validate_release_metadata(root)


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


def test_semantic_plan_failure_must_remain_schema_valid(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/transformation-plan-0.1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    case = next(case for case in manifest["cases"] if case["id"] == "reject-descending-range")
    case["plan"]["operations"][0]["unexpected"] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="semantic failure must have a schema-valid plan"):
        validate_contract_artifacts(root)


def test_plan_schema_invalid_failure_requires_invalid_plan(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/transformation-plan-0.1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    case = next(case for case in manifest["cases"] if case["id"] == "reject-descending-range")
    case["expected_error"] = "plan_schema_invalid"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="plan_schema_invalid requires a schema-invalid plan"):
        validate_contract_artifacts(root)


def test_frontend_plan_schema_invalid_case_requires_valid_request_and_invalid_plan(
    tmp_path: Path,
) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.3.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    case = next(case for case in manifest["cases"] if case["id"] == "formats-grouped-to-expands-source-order")
    case["expected_error"] = "plan_schema_invalid"
    case["expected_plan"]["operations"][0]["unexpected"] = True
    case.pop("expected_plan_contract")
    case.pop("expected_plan_hash")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    validate_contract_artifacts(root)


def test_superseded_replacement_must_keep_request_identity(tmp_path: Path) -> None:
    root = copied_artifacts(tmp_path)
    path = root / "conformance/spss-syntax-frontend-0.3.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    replacement = next(
        case for case in manifest["cases"] if case["id"] == "inline-block-comment-is-ignored"
    )
    replacement["request"]["input_alias"] = "other"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactValidationError, match="superseded case request mismatch"):
        validate_contract_artifacts(root)
