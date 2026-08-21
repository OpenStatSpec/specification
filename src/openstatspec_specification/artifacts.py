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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactValidationError(message)


def _canonical_parts(relative: str) -> list[str]:
    _require(
        isinstance(relative, str)
        and not relative.startswith("/")
        and "\\" not in relative,
        f"noncanonical artifact path: {relative}",
    )
    parts = relative.split("/")
    _require(
        all(part not in {"", ".", ".."} for part in parts),
        f"noncanonical artifact path: {relative}",
    )
    return parts


def _safe_candidate(root: Path, relative: str) -> Path:
    parts = _canonical_parts(relative)
    candidate = root.joinpath(*parts)
    current = root
    try:
        for part in parts:
            current = current / part
            _require(
                not current.is_symlink(),
                f"artifact path traverses symlink: {relative}",
            )
    except OSError as error:
        raise ArtifactValidationError(
            f"artifact path cannot be inspected: {relative} ({type(error).__name__})"
        ) from None
    return candidate


def _load_json(root: Path, relative: str) -> object:
    candidate = _safe_candidate(root, relative)
    try:
        _require(candidate.is_file(), f"artifact is missing: {relative}")
        return json.loads(candidate.read_text(encoding="utf-8"))
    except ArtifactValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ArtifactValidationError(
            f"artifact cannot be decoded: {relative} ({type(error).__name__})"
        ) from None


def _require_file(root: Path, relative: str) -> None:
    candidate = _safe_candidate(root, relative)
    try:
        _require(candidate.is_file(), f"artifact is missing: {relative}")
    except OSError as error:
        raise ArtifactValidationError(
            f"artifact cannot be inspected: {relative} ({type(error).__name__})"
        ) from None


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
        _require(
            isinstance(case_id, str) and bool(case_id),
            f"{context}: case id must be a non-empty string",
        )
        _require(case_id not in seen, f"{context}: duplicate case id: {case_id}")
        seen.add(case_id)


def _schema(root: Path, relative: str) -> Mapping[str, object]:
    value = _load_json(root, relative)
    _require(isinstance(value, dict), f"{relative}: schema must be an object")
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError as error:
        raise ArtifactValidationError(
            f"{relative}: invalid JSON Schema: {error.message}"
        ) from None
    return value


def _load_manifest(root: Path, relative: str, version: str, contract: str) -> dict[str, object]:
    value = _load_json(root, relative)
    _require(isinstance(value, dict), f"{relative}: manifest must be an object")
    _require(
        value.get("manifest_version") == version,
        f"{relative}: manifest_version must be {version}",
    )
    _require(
        value.get("contract") == contract,
        f"{relative}: contract must be {contract}",
    )
    _require_unique_case_ids(value, relative)
    return value


def _validate_cases(
    cases: object,
    schema: Mapping[str, object],
    field: str,
    context: str,
) -> None:
    _require(isinstance(cases, list), f"{context}: cases must be a list")
    validator = Draft202012Validator(schema)
    for index, case in enumerate(cases):
        _require(isinstance(case, dict), f"{context}: each case must be an object")
        value = case.get(field)
        try:
            validator.validate(value)
        except ValidationError as error:
            raise ArtifactValidationError(
                f"{context}.cases[{index}].{field}: schema validation failed: {error.message}"
            ) from None


def _validate_expected_plans(
    cases: object,
    schemas: Mapping[str, Mapping[str, object]],
    context: str,
) -> None:
    _require(isinstance(cases, list), f"{context}: cases must be a list")
    for index, case in enumerate(cases):
        _require(isinstance(case, dict), f"{context}: each case must be an object")
        for field in ("expected_plan", "expected_plan_0_1"):
            if field not in case:
                continue
            plan = case[field]
            _require(isinstance(plan, dict), f"{context}.cases[{index}].{field}: must be an object")
            contract = plan.get("contract")
            _require(
                isinstance(contract, str) and contract in schemas,
                f"{context}.cases[{index}].{field}: unsupported plan contract",
            )
            try:
                Draft202012Validator(schemas[contract]).validate(plan)
            except ValidationError as error:
                raise ArtifactValidationError(
                    f"{context}.cases[{index}].{field}: schema validation failed: {error.message}"
                ) from None


def _require_exact_field(value: object, expected: object, context: str) -> None:
    _require(value == expected, f"{context}: has an unexpected value")


def validate_contract_artifacts(root: Path) -> ArtifactInventory:
    plan_schemas: dict[str, Mapping[str, object]] = {}
    plan_manifests: dict[str, dict[str, object]] = {}
    plan_contracts = {
        "0.1": "openstatspec-transformation-plan-v0.1",
        "0.2": "openstatspec-transformation-plan-v0.2",
    }
    for version, manifest_relative in PLAN_MANIFESTS.items():
        manifest = _load_manifest(root, manifest_relative, version, plan_contracts[version])
        schema_reference = {
            "0.1": "../transformation/plan-0.1.schema.json",
            "0.2": "../transformation/plan-0.2.schema.json",
        }[version]
        _require_exact_field(
            manifest.get("schema"),
            schema_reference,
            f"{manifest_relative}: schema",
        )
        schema_relative = _resolve_manifest_reference(manifest_relative, schema_reference)
        plan_schemas[version] = _schema(root, schema_relative)
        _validate_cases(manifest.get("cases"), plan_schemas[version], "plan", manifest_relative)
        plan_manifests[version] = manifest

    frontend_schemas: dict[str, Mapping[str, object]] = {}
    frontend_manifests: dict[str, dict[str, object]] = {}
    frontend_contracts = {
        "0.1": "openstatspec-spss-syntax-frontend-v0.1",
        "0.2": "openstatspec-spss-syntax-frontend-v0.2",
    }
    for version, manifest_relative in FRONTEND_MANIFESTS.items():
        manifest = _load_manifest(root, manifest_relative, version, frontend_contracts[version])
        request_reference = {
            "0.1": "../transformation/spss-syntax-frontend-0.1.schema.json",
            "0.2": "../transformation/spss-syntax-frontend-0.2.schema.json",
        }[version]
        _require_exact_field(
            manifest.get("request_schema"),
            request_reference,
            f"{manifest_relative}: request_schema",
        )
        request_relative = _resolve_manifest_reference(manifest_relative, request_reference)
        frontend_schemas[version] = _schema(root, request_relative)
        _validate_cases(
            manifest.get("cases"),
            frontend_schemas[version],
            "request",
            manifest_relative,
        )

        if version == "0.1":
            _require_exact_field(
                manifest.get("plan_contract"),
                "openstatspec-transformation-plan-v0.1",
                f"{manifest_relative}: plan_contract",
            )
            plan_reference = "../transformation/plan-0.1.schema.json"
            _require_exact_field(
                manifest.get("plan_schema"),
                plan_reference,
                f"{manifest_relative}: plan_schema",
            )
            resolved_plan_reference = _resolve_manifest_reference(
                manifest_relative,
                plan_reference,
            )
            plan_schema = _schema(root, resolved_plan_reference)
            _validate_expected_plans(
                manifest.get("cases"),
                {"openstatspec-transformation-plan-v0.1": plan_schema},
                manifest_relative,
            )
        else:
            _require_exact_field(
                manifest.get("plan_contracts"),
                [
                    "openstatspec-transformation-plan-v0.1",
                    "openstatspec-transformation-plan-v0.2",
                ],
                f"{manifest_relative}: plan_contracts",
            )
            plan_references = {
                "openstatspec-transformation-plan-v0.1": "../transformation/plan-0.1.schema.json",
                "openstatspec-transformation-plan-v0.2": "../transformation/plan-0.2.schema.json",
            }
            _require_exact_field(
                manifest.get("plan_schemas"),
                plan_references,
                f"{manifest_relative}: plan_schemas",
            )
            resolved_plan_schemas = {
                contract: _schema(
                    root,
                    _resolve_manifest_reference(manifest_relative, reference),
                )
                for contract, reference in plan_references.items()
            }
            _validate_expected_plans(
                manifest.get("cases"),
                resolved_plan_schemas,
                manifest_relative,
            )
        frontend_manifests[version] = manifest

    binding_contracts = {
        "0.1": "openstatspec-in-place-transformation-v0.1",
        "0.2": "openstatspec-in-place-transformation-v0.2",
    }
    binding_manifests: dict[str, dict[str, object]] = {}
    for version, manifest_relative in BINDING_MANIFESTS.items():
        manifest = _load_manifest(root, manifest_relative, version, binding_contracts[version])
        if version == "0.2":
            audit_reference = "../sql/transformation-plan-profile-schema.sql"
            _require_exact_field(
                manifest.get("audit_schema"),
                audit_reference,
                f"{manifest_relative}: audit_schema",
            )
            resolved_audit_reference = _resolve_manifest_reference(
                manifest_relative,
                audit_reference,
            )
            _require_file(root, resolved_audit_reference)
        binding_manifests[version] = manifest

    return ArtifactInventory(
        plan_cases={version: len(manifest["cases"]) for version, manifest in plan_manifests.items()},
        frontend_declared_cases={
            version: len(manifest["cases"])
            for version, manifest in frontend_manifests.items()
        },
        frontend_effective_cases={
            version: len(manifest["cases"])
            for version, manifest in frontend_manifests.items()
        },
        binding_cases={
            version: len(manifest["cases"])
            for version, manifest in binding_manifests.items()
        },
    )
