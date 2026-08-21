from __future__ import annotations

import hashlib
import json
from copy import deepcopy
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
    "0.3": "conformance/spss-syntax-frontend-0.3.json",
}
BINDING_MANIFESTS = {
    "0.1": "conformance/in-place-transformation-0.1.json",
    "0.2": "conformance/in-place-transformation-0.2.json",
}
V030_COMMIT = "cd8f198c68b849eb8ed018a894670a0904c2181d"
V030_PROFILE_DOCUMENTS = (
    "docs/transformation-plan-profile-0.2.md",
    "docs/spss-syntax-frontend-profile-0.2.md",
    "docs/transformation-plan-sql-binding-0.2.md",
)


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
    return _sha256(normalized.encode("utf-8"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _expected_error(case: Mapping[str, object], context: str) -> str | None:
    value = case.get("expected_error")
    _require(
        value is None or (isinstance(value, str) and bool(value)),
        f"{context}: expected_error must be null or a non-empty string",
    )
    return value if isinstance(value, str) else None


def _schema_is_valid(value: object, schema: Mapping[str, object]) -> bool:
    try:
        Draft202012Validator(schema).validate(value)
    except ValidationError:
        return False
    return True


def _validate_plan_manifests(
    root: Path,
    manifests: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    """Return version -> case-id -> successful canonical plan case."""
    successful: dict[str, Mapping[str, object]] = {}
    for version, manifest in manifests.items():
        manifest_relative = PLAN_MANIFESTS[version]
        schema_reference = manifest.get("schema")
        _require(
            isinstance(schema_reference, str),
            f"{manifest_relative}: schema must be a string",
        )
        schema = _schema(root, _resolve_manifest_reference(manifest_relative, schema_reference))
        cases = manifest.get("cases")
        _require(isinstance(cases, list), f"{manifest_relative}: cases must be a list")
        successful_cases: dict[str, Mapping[str, object]] = {}
        validator = Draft202012Validator(schema)
        for index, case in enumerate(cases):
            context = f"{manifest_relative}.cases[{index}]"
            _require(isinstance(case, dict), f"{context}: each case must be an object")
            expected_error = _expected_error(case, context)
            plan = case.get("plan")
            _require(isinstance(plan, dict), f"{context}.plan: must be an object")
            expected_hash = case.get("expected_plan_hash")
            if expected_error is not None:
                _require(
                    "expected_plan_hash" not in case or expected_hash is None,
                    f"{context}: failing case must omit expected_plan_hash or set it to null",
                )
                continue

            try:
                validator.validate(plan)
            except ValidationError as error:
                raise ArtifactValidationError(
                    f"{context}.plan: schema validation failed: {error.message}"
                ) from None
            _require(
                plan.get("contract") == manifest.get("contract"),
                f"{context}.plan: contract does not match manifest",
            )
            actual_hash = _sha256(canonical_json_bytes(plan))
            _require(
                isinstance(expected_hash, str) and expected_hash == actual_hash,
                f"{context}: plan hash mismatch",
            )
            successful_cases[case["id"]] = case
        successful[version] = successful_cases
    return successful


def _frontend_plan_schemas(
    root: Path,
    version: str,
    manifest: Mapping[str, object],
) -> Mapping[str, Mapping[str, object]]:
    manifest_relative = FRONTEND_MANIFESTS[version]
    if version == "0.1":
        contract = manifest.get("plan_contract")
        reference = manifest.get("plan_schema")
        _require(
            isinstance(contract, str) and isinstance(reference, str),
            f"{manifest_relative}: plan contract and schema must be declared",
        )
        return {
            contract: _schema(
                root,
                _resolve_manifest_reference(manifest_relative, reference),
            )
        }

    references = manifest.get("plan_schemas")
    _require(isinstance(references, dict), f"{manifest_relative}: plan_schemas must be an object")
    schemas: dict[str, Mapping[str, object]] = {}
    for contract, reference in references.items():
        _require(
            isinstance(contract, str) and isinstance(reference, str),
            f"{manifest_relative}: plan schema references must be strings",
        )
        schemas[contract] = _schema(
            root,
            _resolve_manifest_reference(manifest_relative, reference),
        )
    return schemas


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _expand_frontend_cases(
    root: Path,
    version: str,
    manifest: Mapping[str, object],
    manifests: Mapping[str, Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    """Return inherited cases with contract override followed by declared cases."""

    def expand(
        current_version: str,
        current_manifest: Mapping[str, object],
        stack: tuple[str, ...],
    ) -> tuple[Mapping[str, object], ...]:
        _require(
            current_version not in stack,
            f"{FRONTEND_MANIFESTS[current_version]}: inherited manifest cycle",
        )
        current_stack = (*stack, current_version)
        current_relative = FRONTEND_MANIFESTS[current_version]
        declared_cases = current_manifest.get("cases")
        _require(isinstance(declared_cases, list), f"{current_relative}: cases must be a list")
        declared_by_id = {
            case["id"]: case
            for case in declared_cases
            if isinstance(case, dict) and isinstance(case.get("id"), str)
        }

        entries = current_manifest.get("inherited_manifests", [])
        _require(
            isinstance(entries, list),
            f"{current_relative}: inherited_manifests must be a list",
        )
        expanded: list[Mapping[str, object]] = []
        for index, entry in enumerate(entries):
            context = f"{current_relative}.inherited_manifests[{index}]"
            _require(isinstance(entry, dict), f"{context}: must be an object")
            reference = entry.get("manifest")
            try:
                parts = _canonical_parts(reference)
            except ArtifactValidationError:
                raise ArtifactValidationError(
                    f"{context}: invalid inherited manifest: {reference!r}"
                ) from None
            _require(
                len(parts) == 1 and parts[0] == reference,
                f"{context}: invalid inherited manifest: {reference!r}",
            )
            target_versions = [
                target_version
                for target_version, target_relative in FRONTEND_MANIFESTS.items()
                if target_relative == f"conformance/{reference}"
                and _version_key(target_version) < _version_key(current_version)
            ]
            _require(
                len(target_versions) == 1 and target_versions[0] in manifests,
                f"{context}: inherited manifest must target an older registered Frontend manifest",
            )
            target_version = target_versions[0]
            target_manifest = manifests[target_version]
            _require(
                entry.get("request_contract_override") == current_manifest.get("contract"),
                f"{context}: request_contract_override must match current manifest contract",
            )
            superseded = entry.get("superseded_cases")
            _require(isinstance(superseded, dict), f"{context}: superseded_cases must be an object")
            target_declared = target_manifest.get("cases")
            _require(
                isinstance(target_declared, list),
                f"{FRONTEND_MANIFESTS[target_version]}: cases must be a list",
            )
            target_by_id = {
                case["id"]: case
                for case in target_declared
                if isinstance(case, dict) and isinstance(case.get("id"), str)
            }
            for old_id, replacement_id in superseded.items():
                _require(
                    isinstance(old_id, str) and isinstance(replacement_id, str),
                    f"{context}: superseded case IDs must be strings",
                )
                _require(
                    old_id in target_by_id,
                    f"{context}: unknown inherited case: {old_id}",
                )
                _require(
                    replacement_id in declared_by_id,
                    f"{context}: unknown replacement case: {replacement_id}",
                )
                old_request = target_by_id[old_id].get("request")
                replacement_request = declared_by_id[replacement_id].get("request")
                _require(
                    isinstance(old_request, dict)
                    and isinstance(replacement_request, dict)
                    and old_request.get("source_text") == replacement_request.get("source_text"),
                    f"{context}: superseded case source text mismatch: {old_id}",
                )

            for inherited_case in expand(target_version, target_manifest, current_stack):
                old_id = inherited_case["id"]
                if old_id in superseded:
                    continue
                case = deepcopy(inherited_case)
                case["id"] = f"{target_version}/{old_id}"
                request = case.get("request")
                _require(
                    isinstance(request, dict),
                    f"{context}: inherited case request must be an object",
                )
                request["contract"] = entry["request_contract_override"]
                expanded.append(case)

        expanded.extend(deepcopy(case) for case in declared_cases)
        seen: set[str] = set()
        for case in expanded:
            case_id = case.get("id")
            _require(
                isinstance(case_id, str) and case_id not in seen,
                f"{current_relative}: duplicate expanded case id: {case_id}",
            )
            seen.add(case_id)
        return tuple(expanded)

    return expand(version, manifest, ())


def _case_source_version(case_id: str, version: str) -> str:
    if version == "0.3" and "/" in case_id:
        source_version, _, _ = case_id.partition("/")
        if source_version in {"0.1", "0.2"}:
            return source_version
    return version


def _resolve_frontend_plans(
    root: Path,
    manifests: Mapping[str, Mapping[str, object]],
    plan_cases: Mapping[str, Mapping[str, object]],
    effective_cases: Mapping[str, tuple[Mapping[str, object], ...]],
) -> Mapping[str, Mapping[str, Mapping[str, object]]]:
    """Return version -> case-id -> resolved canonical plan for successes."""
    resolved: dict[str, dict[str, Mapping[str, object]]] = {}
    for version in ("0.1", "0.2", "0.3"):
        manifest = manifests[version]
        manifest_relative = FRONTEND_MANIFESTS[version]
        request_reference = manifest.get("request_schema")
        _require(
            isinstance(request_reference, str),
            f"{manifest_relative}: request_schema must be a string",
        )
        request_schema = _schema(
            root,
            _resolve_manifest_reference(manifest_relative, request_reference),
        )
        plan_schemas = _frontend_plan_schemas(root, version, manifest)
        cases = effective_cases[version]
        successful: dict[str, Mapping[str, object]] = {}
        for index, case in enumerate(cases):
            context = f"{manifest_relative}.cases[{index}]"
            _require(isinstance(case, dict), f"{context}: each case must be an object")
            source_version = _case_source_version(case["id"], version)
            expected_error = _expected_error(case, context)
            request = case.get("request")
            _require(isinstance(request, dict), f"{context}.request: must be an object")
            source_text = request.get("source_text")
            if isinstance(source_text, str):
                actual_source_hash = source_hash(source_text)
                _require(
                    isinstance(case.get("expected_source_hash"), str)
                    and case.get("expected_source_hash") == actual_source_hash,
                    f"{context}: source hash mismatch",
                )
            request_valid = _schema_is_valid(request, request_schema)
            if expected_error == "plan_schema_invalid":
                _require(
                    not request_valid,
                    f"{context}: plan_schema_invalid requires an invalid request",
                )
            else:
                _require(
                    request_valid,
                    f"{context}.request: schema validation failed",
                )

            plan_fields = (
                "expected_plan",
                "expected_plan_0_1",
                "expected_plan_case",
                "expected_plan_case_0_1",
            )
            present_plan_fields = [field for field in plan_fields if field in case]
            if expected_error is not None:
                for field in (*plan_fields, "expected_plan_contract", "expected_plan_hash"):
                    _require(
                        field not in case,
                        f"{context}: failing case must omit {field}",
                    )
                continue

            _require(
                len(present_plan_fields) == 1,
                f"{context}: successful case must declare exactly one expected plan",
            )
            expected_field = present_plan_fields[0]
            plan: Mapping[str, object]
            referenced_plan_hash: object = None
            if expected_field in {"expected_plan", "expected_plan_0_1"}:
                inline_plan = case.get(expected_field)
                _require(
                    isinstance(inline_plan, dict),
                    f"{context}.{expected_field}: must be an object",
                )
                plan = inline_plan
            elif expected_field == "expected_plan_case":
                plan_version = "0.1" if source_version == "0.1" else "0.2"
                expected_contract = case.get("expected_plan_contract")
                _require(
                    expected_contract is None
                    or expected_contract == manifests[source_version].get(
                        "plan_contract", "openstatspec-transformation-plan-v0.2"
                    ),
                    f"{context}: expected_plan_contract does not match expected_plan_case",
                )
                reference = case.get(expected_field)
                _require(
                    isinstance(reference, str),
                    f"{context}.{expected_field}: must be a string",
                )
                referenced_case = plan_cases[plan_version].get(reference)
                _require(
                    referenced_case is not None,
                    f"{context}: unknown plan case: {reference}",
                )
                plan = referenced_case["plan"]
                referenced_plan_hash = referenced_case.get("expected_plan_hash")
            else:
                _require(
                    source_version in {"0.2", "0.3"},
                    f"{context}.{expected_field}: only Frontend 0.2 and 0.3 may use this reference",
                )
                reference = case.get(expected_field)
                _require(
                    isinstance(reference, str),
                    f"{context}.{expected_field}: must be a string",
                )
                frontend_01_plan = resolved["0.1"].get(reference)
                _require(
                    frontend_01_plan is not None,
                    f"{context}: unknown Frontend 0.1 plan case: {reference}",
                )
                plan = frontend_01_plan

            contract = plan.get("contract")
            _require(
                isinstance(contract, str) and contract in plan_schemas,
                f"{context}: unsupported expected plan contract",
            )
            try:
                Draft202012Validator(plan_schemas[contract]).validate(plan)
            except ValidationError as error:
                raise ArtifactValidationError(
                    f"{context}: expected plan schema validation failed: {error.message}"
                ) from None
            declared_contract = case.get("expected_plan_contract")
            _require(
                declared_contract is None or declared_contract == contract,
                f"{context}: expected_plan_contract does not match plan",
            )
            expected_hash = case.get("expected_plan_hash", referenced_plan_hash)
            actual_hash = _sha256(canonical_json_bytes(plan))
            _require(
                isinstance(expected_hash, str) and expected_hash == actual_hash,
                f"{context}: plan hash mismatch",
            )
            successful[case["id"]] = plan
        resolved[version] = successful
    return resolved


def _validate_binding_manifests(
    manifests: Mapping[str, Mapping[str, object]],
    plan_cases: Mapping[str, Mapping[str, object]],
    frontend_plans: Mapping[str, Mapping[str, Mapping[str, object]]],
    frontend_manifests: Mapping[str, Mapping[str, object]],
) -> None:
    for version, manifest in manifests.items():
        manifest_relative = BINDING_MANIFESTS[version]
        cases = manifest.get("cases")
        _require(isinstance(cases, list), f"{manifest_relative}: cases must be a list")
        for index, case in enumerate(cases):
            context = f"{manifest_relative}.cases[{index}]"
            _require(isinstance(case, dict), f"{context}: each case must be an object")
            expected_error = _expected_error(case, context)
            if expected_error is not None:
                _require(
                    case.get("mutation_started") is False
                    or (
                        case.get("mutation_started") is True
                        and case.get("failure_point") == "after_data_and_metadata_before_audit"
                    ),
                    f"{context}: failing binding case must set mutation_started to false",
                )
            if version != "0.2":
                continue

            has_plan_reference = "applied_plan_case" in case
            has_frontend_reference = "applied_frontend_case" in case
            _require(
                has_plan_reference == has_frontend_reference,
                f"{context}: binding plan and frontend references must be paired",
            )
            if not has_plan_reference:
                continue

            plan_reference = case.get("applied_plan_case")
            frontend_reference = case.get("applied_frontend_case")
            _require(
                isinstance(plan_reference, str),
                f"{context}: applied_plan_case must be a string",
            )
            _require(
                isinstance(frontend_reference, str),
                f"{context}: applied_frontend_case must be a string",
            )
            plan_case = plan_cases["0.2"].get(plan_reference)
            _require(
                plan_case is not None,
                f"{context}: unknown plan case: {plan_reference}",
            )
            frontend_plan = frontend_plans["0.2"].get(frontend_reference)
            _require(
                frontend_plan is not None,
                f"{context}: unknown frontend case: {frontend_reference}",
            )
            _require(
                frontend_plan == plan_case["plan"],
                f"{context}: binding reference mismatch",
            )

            expected_audit = case.get("expected_audit")
            if expected_audit is None:
                continue
            _require(
                isinstance(expected_audit, dict),
                f"{context}.expected_audit: must be an object",
            )
            plan = plan_case["plan"]
            frontend_case = next(
                (
                    frontend_case
                    for frontend_case in frontend_manifests["0.2"].get("cases", [])
                    if isinstance(frontend_case, dict)
                    and frontend_case.get("id") == frontend_reference
                ),
                None,
            )
            _require(
                isinstance(frontend_case, dict),
                f"{context}: unknown frontend case: {frontend_reference}",
            )
            expected_values = {
                "plan_hash": plan_case.get("expected_plan_hash"),
                "source_hash": frontend_case.get("expected_source_hash"),
                "canonical_plan_json": canonical_json_bytes(plan).decode("utf-8"),
                "operation_count": len(plan["operations"]),
            }
            for field, expected in expected_values.items():
                if field in expected_audit:
                    _require(
                        expected_audit[field] == expected,
                        f"{context}.expected_audit.{field}: audit identity mismatch",
                    )


def _require_exact_field(value: object, expected: object, context: str) -> None:
    _require(value == expected, f"{context}: has an unexpected value")


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
    _require(
        "current public specification release and is immutable" in roadmap,
        "ROADMAP release status mismatch",
    )
    _require(V030_COMMIT in roadmap, "ROADMAP v0.3.0 commit mismatch")

    classification = (root / "docs/spss-frontend-roadmap.md").read_text(encoding="utf-8")
    for phrase in (
        "Frontend 0.3, Plan 0.1/0.2",
        "New Plan/Frontend/Binding generation",
        "Separate case-transformation profile",
        "Explicit non-goal",
    ):
        _require(phrase in classification, f"SPSS classification is missing {phrase}")


def validate_contract_artifacts(root: Path) -> ArtifactInventory:
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
        _schema(root, schema_relative)
        plan_manifests[version] = manifest
    plan_cases = _validate_plan_manifests(root, plan_manifests)

    frontend_manifests: dict[str, dict[str, object]] = {}
    frontend_contracts = {
        "0.1": "openstatspec-spss-syntax-frontend-v0.1",
        "0.2": "openstatspec-spss-syntax-frontend-v0.2",
        "0.3": "openstatspec-spss-syntax-frontend-v0.3",
    }
    for version, manifest_relative in FRONTEND_MANIFESTS.items():
        request_reference = {
            "0.1": "../transformation/spss-syntax-frontend-0.1.schema.json",
            "0.2": "../transformation/spss-syntax-frontend-0.2.schema.json",
            "0.3": "../transformation/spss-syntax-frontend-0.3.schema.json",
        }[version]
        manifest = _load_manifest(root, manifest_relative, version, frontend_contracts[version])
        _require_exact_field(
            manifest.get("request_schema"),
            request_reference,
            f"{manifest_relative}: request_schema",
        )
        request_relative = _resolve_manifest_reference(manifest_relative, request_reference)
        _schema(root, request_relative)

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
            _schema(root, resolved_plan_reference)
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
            for reference in plan_references.values():
                _schema(
                    root,
                    _resolve_manifest_reference(manifest_relative, reference),
                )
        frontend_manifests[version] = manifest
    frontend_effective_cases = {
        version: _expand_frontend_cases(root, version, manifest, frontend_manifests)
        for version, manifest in frontend_manifests.items()
    }
    frontend_plans = _resolve_frontend_plans(
        root,
        frontend_manifests,
        plan_cases,
        frontend_effective_cases,
    )

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
    _validate_binding_manifests(
        binding_manifests,
        plan_cases,
        frontend_plans,
        frontend_manifests,
    )

    return ArtifactInventory(
        plan_cases={version: len(manifest["cases"]) for version, manifest in plan_manifests.items()},
        frontend_declared_cases={
            version: len(manifest["cases"])
            for version, manifest in frontend_manifests.items()
        },
        frontend_effective_cases={
            version: len(cases)
            for version, cases in frontend_effective_cases.items()
        },
        binding_cases={
            version: len(manifest["cases"])
            for version, manifest in binding_manifests.items()
        },
    )
