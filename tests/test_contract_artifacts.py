from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from openstatspec_specification.artifacts import ArtifactValidationError
from openstatspec_specification.artifacts import validate_release_metadata
from openstatspec_specification.artifacts import validate_contract_artifacts


ROOT = Path(__file__).resolve().parents[1]


def test_released_contract_artifact_inventory_is_valid() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.plan_cases == {"0.1": 4, "0.2": 26}
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44, "0.3": 14}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44, "0.3": 69}
    assert inventory.binding_cases == {"0.1": 6, "0.2": 11}


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


def test_frontend_03_inherits_released_cases_under_new_request_contract() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 14
    assert inventory.frontend_effective_cases["0.3"] == 69


def test_frontend_03_comment_and_varlist_case_inventory() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.frontend_declared_cases["0.3"] == 14
    assert inventory.frontend_effective_cases["0.3"] == 69


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
