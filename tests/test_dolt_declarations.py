from __future__ import annotations

import copy
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest

import openstatspec_specification.dolt as dolt_module
from openstatspec_specification.dolt import (
    DoltDeclarationError,
    DoltDeclarationSource,
    load_validated_dolt_declarations,
    select_dolt_declaration,
    validate_dolt_declaration,
    verify_evidence_artifact,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_REF = "sql/dolt-adapter-declarations/evidence/result.json"


class _SyntheticTraversable:
    def __init__(self, *, failure_at: str, error: OSError) -> None:
        self.failure_at = failure_at
        self.error = error
        self.name = "synthetic.json"

    def joinpath(self, *descendants: str) -> "_SyntheticTraversable":
        return self

    def is_file(self) -> bool:
        if self.failure_at == "is_file":
            raise self.error
        return True

    def read_bytes(self) -> bytes:
        if self.failure_at == "read_bytes":
            raise self.error
        return b"{}"

    def is_dir(self) -> bool:
        if self.failure_at == "is_dir":
            raise self.error
        return True

    def iterdir(self) -> tuple["_SyntheticTraversable", ...]:
        if self.failure_at == "iterdir":
            raise self.error
        return ()


def _assert_sanitized_io_error(callable_under_test: object) -> None:
    with pytest.raises(DoltDeclarationError) as caught:
        callable_under_test()
    assert caught.value.code == "resource_io_error"
    assert "confidential" not in str(caught.value)
    assert "/respondents" not in str(caught.value)


def _write_evidence(root: Path, payload: bytes = b"synthetic evidence\n") -> str:
    artifact = root / EVIDENCE_REF
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(
    ("boundary", "error"),
    [
        ("is_file", PermissionError("/respondents/confidential.sav")),
        ("read_bytes", OSError("/respondents/confidential.sav")),
    ],
)
def test_resource_file_io_failures_are_typed_and_sanitized(
    boundary: str, error: OSError,
) -> None:
    source = DoltDeclarationSource(
        root=_SyntheticTraversable(failure_at=boundary, error=error),
    )
    _assert_sanitized_io_error(
        lambda: source.read_bytes("sql/synthetic.json"),
    )


def test_evidence_directory_io_failures_are_typed_and_sanitized() -> None:
    source = DoltDeclarationSource(
        root=_SyntheticTraversable(
            failure_at="is_dir",
            error=PermissionError("/respondents/confidential-evidence"),
        ),
    )
    _assert_sanitized_io_error(
        lambda: source.is_directory("sql/dolt-adapter-declarations/evidence"),
    )


@pytest.mark.parametrize(
    ("boundary", "error"),
    [
        ("is_dir", PermissionError("/respondents/confidential")),
        ("iterdir", OSError("/respondents/confidential")),
    ],
)
def test_declaration_directory_io_failures_are_typed_and_sanitized(
    boundary: str, error: OSError,
) -> None:
    source = DoltDeclarationSource(
        root=_SyntheticTraversable(failure_at=boundary, error=error),
    )
    _assert_sanitized_io_error(source.declaration_resources)


def test_declaration_json_io_failures_are_typed_and_sanitized() -> None:
    resource = _SyntheticTraversable(
        failure_at="read_bytes",
        error=OSError("/respondents/confidential.json"),
    )
    _assert_sanitized_io_error(
        lambda: dolt_module._json_from_resource(resource, "Dolt declaration"),
    )


def test_directory_source_verifies_canonical_artifact_and_hash(tmp_path: Path) -> None:
    digest = _write_evidence(tmp_path)
    source = DoltDeclarationSource.from_directory(tmp_path)
    assert verify_evidence_artifact(
        source, artifact_ref=EVIDENCE_REF, artifact_sha256=digest,
    ) == b"synthetic evidence\n"


@pytest.mark.parametrize(
    "artifact_ref",
    ["../result.json", "/result.json", "sql//result.json", "sql\\result.json"],
)
def test_artifact_path_escape_and_noncanonical_forms_fail_closed(
    tmp_path: Path, artifact_ref: str,
) -> None:
    source = DoltDeclarationSource.from_directory(tmp_path)
    with pytest.raises(DoltDeclarationError, match="canonical"):
        verify_evidence_artifact(
            source, artifact_ref=artifact_ref, artifact_sha256="0" * 64,
        )


def test_directory_source_rejects_symlinked_evidence(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    artifact = tmp_path / EVIDENCE_REF
    artifact.parent.mkdir(parents=True)
    artifact.symlink_to(outside)
    source = DoltDeclarationSource.from_directory(tmp_path)
    with pytest.raises(DoltDeclarationError, match="symlink"):
        verify_evidence_artifact(
            source,
            artifact_ref=EVIDENCE_REF,
            artifact_sha256=hashlib.sha256(b"outside").hexdigest(),
        )


def test_artifact_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    _write_evidence(tmp_path)
    source = DoltDeclarationSource.from_directory(tmp_path)
    with pytest.raises(DoltDeclarationError, match="does not match"):
        verify_evidence_artifact(
            source, artifact_ref=EVIDENCE_REF, artifact_sha256="0" * 64,
        )


def test_packaged_source_reads_authoritative_resources_from_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "specification.whl"
    with zipfile.ZipFile(archive, "w") as wheel:
        for resource in sorted((REPOSITORY_ROOT / "sql").rglob("*")):
            if resource.is_file():
                wheel.write(
                    resource,
                    "sql/" + resource.relative_to(
                        REPOSITORY_ROOT / "sql"
                    ).as_posix(),
                )
    zipped_root = zipfile.Path(archive)
    monkeypatch.setattr(dolt_module.resources, "files", lambda package: zipped_root)
    source = DoltDeclarationSource.packaged()
    assert load_validated_dolt_declarations(source) == ()


def test_repository_baseline_must_remain_symbolic(tmp_path: Path) -> None:
    shutil.copytree(REPOSITORY_ROOT / "sql", tmp_path / "sql")
    baseline_path = tmp_path / "sql/dialect-profile-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["profiles"]["dolt"]["declaration_kind"] = "concrete_adapter"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(DoltDeclarationError, match="symbolic template"):
        load_validated_dolt_declarations(
            DoltDeclarationSource.from_directory(tmp_path),
        )


def test_directory_root_loads_authoritative_empty_declaration_set() -> None:
    source = DoltDeclarationSource.from_directory(REPOSITORY_ROOT)
    assert load_validated_dolt_declarations(source) == ()


def test_malformed_fault_conformance_is_typed() -> None:
    baseline = json.loads(
        (REPOSITORY_ROOT / "sql/dialect-profile-baseline.json").read_text(
            encoding="utf-8"
        )
    )["profiles"]["dolt"]
    declaration = copy.deepcopy(baseline)
    declaration["boundary_conformance"]["fault_conformance"] = None
    with pytest.raises(DoltDeclarationError, match="fault-conformance"):
        validate_dolt_declaration(
            declaration,
            "synthetic malformed fault declaration",
            source=DoltDeclarationSource.from_directory(REPOSITORY_ROOT),
        )


@pytest.mark.parametrize("malformed_kind", [[], {}])
def test_malformed_declaration_kind_is_typed(malformed_kind: object) -> None:
    baseline = json.loads(
        (REPOSITORY_ROOT / "sql/dialect-profile-baseline.json").read_text(
            encoding="utf-8"
        )
    )["profiles"]["dolt"]
    declaration = copy.deepcopy(baseline)
    declaration["declaration_kind"] = malformed_kind
    with pytest.raises(DoltDeclarationError, match="declaration kind"):
        validate_dolt_declaration(
            declaration,
            "synthetic malformed kind declaration",
            source=DoltDeclarationSource.from_directory(REPOSITORY_ROOT),
        )

@pytest.mark.parametrize("malformed_kind", [[], {}])
def test_malformed_evidence_kind_is_typed(malformed_kind: object) -> None:
    baseline = json.loads(
        (REPOSITORY_ROOT / "sql/dialect-profile-baseline.json").read_text(
            encoding="utf-8"
        )
    )["profiles"]["dolt"]
    declaration = copy.deepcopy(baseline)
    declaration["evidence_records"] = [{
        "evidence_id": "synthetic",
        "kind": malformed_kind,
        "exact_versions": [],
        "artifact_ref": "template",
        "artifact_sha256": "0" * 64,
        "measurement": "template",
        "observed": "template",
    }]
    with pytest.raises(DoltDeclarationError, match="kind must be a string"):
        validate_dolt_declaration(
            declaration,
            "synthetic malformed evidence kind declaration",
            source=DoltDeclarationSource.from_directory(REPOSITORY_ROOT),
        )


def test_malformed_boundary_conformance_is_typed() -> None:
    baseline = json.loads(
        (REPOSITORY_ROOT / "sql/dialect-profile-baseline.json").read_text(
            encoding="utf-8"
        )
    )["profiles"]["dolt"]
    declaration = copy.deepcopy(baseline)
    declaration["boundary_conformance"] = None
    with pytest.raises(DoltDeclarationError, match="boundary-conformance"):
        validate_dolt_declaration(
            declaration,
            "synthetic malformed declaration",
            source=DoltDeclarationSource.from_directory(REPOSITORY_ROOT),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("declaration_id", None),
        ("adapter_implementation_id", "Template_adapter"),
        ("adapter_version", "0.1"),
        ("specification_commit", "A" * 40),
        ("conformance_run_id", "contains whitespace"),
    ],
)
def test_concrete_binding_fields_are_mandatory_and_canonical(
    field: str, value: object,
) -> None:
    baseline = json.loads(
        (REPOSITORY_ROOT / "sql/dialect-profile-baseline.json").read_text(
            encoding="utf-8"
        )
    )["profiles"]["dolt"]
    declaration = copy.deepcopy(baseline)
    declaration.update({
        "declaration_kind": "concrete_adapter",
        "declaration_id": "adapter-dolt-2.2.2",
        "adapter_implementation_id": "openstatspec-python",
        "adapter_version": "0.1.0",
        "specification_commit": "a" * 40,
        "conformance_run_id": "run-2026-07-30",
    })
    declaration[field] = value
    with pytest.raises(DoltDeclarationError, match=field):
        validate_dolt_declaration(
            declaration,
            "synthetic concrete declaration",
            source=DoltDeclarationSource.from_directory(REPOSITORY_ROOT),
        )


def test_exact_selection_rejects_zero_and_multiple_matches() -> None:
    binding = {
        "active_product_version": "2.2.2",
        "adapter_implementation_id": "openstatspec-python",
        "adapter_version": "0.1.0",
        "specification_commit": "a" * 40,
    }
    with pytest.raises(DoltDeclarationError) as missing:
        select_dolt_declaration((), **binding)
    assert missing.value.code == "dolt_declaration_missing"

    duplicate = {**binding, "declaration_id": "one"}
    with pytest.raises(DoltDeclarationError) as ambiguous:
        select_dolt_declaration(
            (duplicate, {**duplicate, "declaration_id": "two"}), **binding,
        )
    assert ambiguous.value.code == "dolt_declaration_ambiguous"

def test_resource_path_inspection_failures_are_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path.resolve()
    source = DoltDeclarationSource(root=root, filesystem_root=root)
    def fail_is_symlink(path: Path) -> bool:
        raise PermissionError("/respondents/confidential")

    monkeypatch.setattr(Path, "is_symlink", fail_is_symlink)
    _assert_sanitized_io_error(lambda: source.resource("sql/dialect-profile-baseline.json"))

def test_source_root_inspection_failures_are_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_exists(path: Path) -> bool:
        raise PermissionError("/respondents/confidential-root")

    monkeypatch.setattr(Path, "exists", fail_exists)
    _assert_sanitized_io_error(lambda: DoltDeclarationSource.from_directory(tmp_path))
