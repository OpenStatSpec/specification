from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from openstatspec_specification.artifacts import ArtifactValidationError
from openstatspec_specification.artifacts import validate_contract_artifacts


ROOT = Path(__file__).resolve().parents[1]


def test_released_contract_artifact_inventory_is_valid() -> None:
    inventory = validate_contract_artifacts(ROOT)
    assert inventory.plan_cases == {"0.1": 4, "0.2": 26}
    assert inventory.frontend_declared_cases == {"0.1": 13, "0.2": 44}
    assert inventory.frontend_effective_cases == {"0.1": 13, "0.2": 44}
    assert inventory.binding_cases == {"0.1": 6, "0.2": 11}


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
