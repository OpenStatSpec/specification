"""Validate concrete adapter declarations against the authoritative Dolt profile."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Mapping


FIELDS = (
    "active_product_version", "adapter_implementation_id", "adapter_version",
    "conformance_run_id", "conformance_status", "declaration_id",
    "declaration_schema_id", "evidence_records", "import_enabled", "profile",
    "specification_commit",
)
EXACT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
CANONICAL_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
ADAPTER_VERSION = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+"
    r"(?:(?:a|b|rc)[0-9]+|\.post[0-9]+|\.dev[0-9]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


class DoltDeclarationError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_dolt_declaration") -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DoltDeclarationError(message)


@dataclass(frozen=True)
class DoltDeclarationSource:
    root: Traversable
    filesystem_root: Path | None = None

    @classmethod
    def packaged(cls) -> "DoltDeclarationSource":
        root = resources.files("openstatspec_specification")
        return cls(root=root, filesystem_root=root if isinstance(root, Path) else None)

    @classmethod
    def from_directory(cls, root: str | Path) -> "DoltDeclarationSource":
        path = Path(root)
        if not path.is_dir():
            raise DoltDeclarationError("Declaration source directory is missing.", code="source_directory_missing")
        if path.is_symlink():
            raise DoltDeclarationError("Declaration source root must not be a symlink.", code="source_root_symlink")
        path = path.resolve()
        return cls(root=path, filesystem_root=path)

    @staticmethod
    def _parts(relative_path: str) -> tuple[str, ...]:
        _require(isinstance(relative_path, str) and bool(relative_path) and "\\" not in relative_path and not relative_path.startswith("/"), "Resource path must be canonical and relative.")
        parts = tuple(relative_path.split("/"))
        _require(all(part not in {"", ".", ".."} for part in parts), "Resource path must be canonical and relative.")
        return parts

    def resource(self, relative_path: str) -> Traversable:
        parts = self._parts(relative_path)
        current: Traversable = self.root
        if self.filesystem_root is not None:
            candidate = self.filesystem_root
            for part in parts:
                candidate = candidate / part
                _require(not candidate.is_symlink(), "Resource path traverses a symlink.")
            try:
                candidate.resolve().relative_to(self.filesystem_root)
            except ValueError as error:
                raise DoltDeclarationError("Resource path escapes its source root.") from error
        for part in parts:
            current = current.joinpath(part)
        return current

    def read_bytes(self, relative_path: str) -> bytes:
        resource = self.resource(relative_path)
        try:
            _require(resource.is_file(), "Required declaration resource is missing.")
            return resource.read_bytes()
        except OSError:
            raise DoltDeclarationError("Declaration resource I/O failed.", code="resource_io_error") from None

    def read_json(self, relative_path: str) -> Any:
        try:
            return json.loads(self.read_bytes(relative_path).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DoltDeclarationError("Declaration resource is not valid UTF-8 JSON.") from error

    def declaration_resources(self) -> tuple[Traversable, ...]:
        directory = self.resource("sql/dolt-adapter-declarations")
        try:
            _require(directory.is_dir(), "Dolt declaration directory is missing.")
            entries = tuple(sorted((item for item in directory.iterdir() if item.name.endswith(".json")), key=lambda item: item.name))
        except OSError:
            raise DoltDeclarationError("Declaration directory I/O failed.", code="resource_io_error") from None
        for entry in entries:
            _require(entry.is_file(), "A declaration JSON is not a regular file.")
            if isinstance(entry, Path):
                _require(not entry.is_symlink(), "A declaration must not be a symlink.")
        return entries


def _string(value: object, message: str) -> str:
    _require(isinstance(value, str) and value == value.strip() and bool(value), message)
    return value


def verify_evidence_artifact(source: DoltDeclarationSource, *, artifact_ref: str, artifact_sha256: str) -> bytes:
    parts = DoltDeclarationSource._parts(artifact_ref)
    _require(parts[:3] == ("sql", "dolt-adapter-declarations", "evidence") and len(parts) > 3, "Evidence artifact is outside its directory.")
    _require(re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is not None, "Evidence SHA-256 is invalid.")
    payload = source.read_bytes(artifact_ref)
    _require(hashlib.sha256(payload).hexdigest() == artifact_sha256, "Evidence hash differs.")
    return payload


def validate_dolt_declaration(declaration: object, *, authoritative_profile: Mapping[str, Any], source: DoltDeclarationSource) -> Mapping[str, Any]:
    _require(isinstance(declaration, dict), "Dolt declaration must be an object.")
    _require(set(declaration) == set(FIELDS), "Dolt declaration fields are incomplete.")
    _require(declaration["declaration_schema_id"] == "openstatspec-dolt-adapter-declaration-v1", "Unexpected declaration schema.")
    for field in ("declaration_id", "adapter_implementation_id", "conformance_run_id"):
        value = _string(declaration[field], "Invalid " + field + ".")
        _require(CANONICAL_ID.fullmatch(value) is not None, "Noncanonical " + field + ".")
    adapter_version = _string(declaration["adapter_version"], "Invalid adapter version.")
    _require(ADAPTER_VERSION.fullmatch(adapter_version) is not None, "Adapter version is not exact.")
    specification_commit = _string(declaration["specification_commit"], "Invalid specification commit.")
    _require(re.fullmatch(r"[0-9a-f]{40}", specification_commit) is not None, "Specification commit is not exact.")
    active_version = _string(declaration["active_product_version"], "Invalid active Dolt version.")
    _require(EXACT_VERSION.fullmatch(active_version) is not None, "Active Dolt version is not exact.")
    _require(declaration["conformance_status"] == "tested" and declaration["import_enabled"] is True, "Declaration is not active and tested.")
    _require(declaration["profile"] == authoritative_profile, "Declared profile differs from the authoritative profile.")
    tested = authoritative_profile.get("exact_ci_tested_versions")
    _require(isinstance(tested, list) and active_version in tested, "Active Dolt version is not CI-tested.")
    evidence = declaration["evidence_records"]
    _require(isinstance(evidence, list) and bool(evidence), "Declaration evidence is required.")
    covered = False
    seen: set[str] = set()
    for record in evidence:
        _require(isinstance(record, dict) and set(record) == {"artifact_ref", "artifact_sha256", "evidence_id", "exact_versions"}, "Evidence fields are incomplete.")
        evidence_id = _string(record["evidence_id"], "Invalid evidence ID.")
        _require(CANONICAL_ID.fullmatch(evidence_id) is not None and evidence_id not in seen, "Evidence ID is invalid or duplicated.")
        seen.add(evidence_id)
        versions = record["exact_versions"]
        versions_are_exact = (
            isinstance(versions, list)
            and bool(versions)
            and all(
                isinstance(item, str) and EXACT_VERSION.fullmatch(item)
                for item in versions
            )
        )
        _require(
            versions_are_exact and len(versions) == len(set(versions)),
            "Evidence versions are not unique exact versions.",
        )
        _require(set(versions) <= set(tested), "Evidence includes an untested Dolt version.")
        covered = covered or active_version in versions
        verify_evidence_artifact(source, artifact_ref=_string(record["artifact_ref"], "Invalid evidence path."), artifact_sha256=_string(record["artifact_sha256"], "Invalid evidence hash."))
    _require(covered, "Evidence does not cover the active Dolt version.")
    return declaration


def load_validated_dolt_declarations(source: DoltDeclarationSource | None = None) -> tuple[Mapping[str, Any], ...]:
    source = source or DoltDeclarationSource.packaged()
    baseline = source.read_json("sql/dialect-profile-baseline.json")
    profile = baseline.get("profiles", {}).get("dolt") if isinstance(baseline, dict) else None
    _require(isinstance(profile, dict), "Authoritative Dolt profile is missing.")
    expected_schema = {
        "artifact_glob": "sql/dolt-adapter-declarations/*.json",
        "declaration_schema_id": "openstatspec-dolt-adapter-declaration-v1",
        "evidence_artifact_root": "sql/dolt-adapter-declarations/evidence",
        "required_declaration_fields": list(FIELDS),
        "required_profile_fields": sorted(profile),
        "schema_version": 1,
        "validator_entrypoint": "openstatspec_specification.dolt::validate_dolt_declaration",
    }
    _require(source.read_json("sql/dolt-adapter-declaration-schema.json") == expected_schema, "Dolt adapter declaration schema is incomplete.")
    declarations: list[Mapping[str, Any]] = []
    declaration_ids: set[object] = set()
    conformance_run_ids: set[object] = set()
    for resource in source.declaration_resources():
        try:
            item = json.loads(resource.read_bytes().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DoltDeclarationError("Dolt declaration is unreadable.") from error
        item = validate_dolt_declaration(item, authoritative_profile=profile, source=source)
        declaration_id = item["declaration_id"]
        conformance_run_id = item["conformance_run_id"]
        _require(
            declaration_id not in declaration_ids
            and conformance_run_id not in conformance_run_ids,
            "Duplicate declaration or conformance run ID.",
        )
        declaration_ids.add(declaration_id)
        conformance_run_ids.add(conformance_run_id)
        declarations.append(item)
    return tuple(declarations)


def select_dolt_declaration(declarations: tuple[Mapping[str, Any], ...], *, active_product_version: str, adapter_implementation_id: str, adapter_version: str, specification_commit: str) -> Mapping[str, Any]:
    matches = tuple(item for item in declarations if item["active_product_version"] == active_product_version and item["adapter_implementation_id"] == adapter_implementation_id and item["adapter_version"] == adapter_version and item["specification_commit"] == specification_commit)
    if len(matches) != 1:
        raise DoltDeclarationError("Expected exactly one matching Dolt declaration.", code="dolt_declaration_missing" if not matches else "dolt_declaration_ambiguous")
    return matches[0]
