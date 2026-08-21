from __future__ import annotations

import json
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
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44}
    assert inventory.binding_cases == {"0.1": 6, "0.2": 11}


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
