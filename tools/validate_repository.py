"""Validate the self-contained OpenStatSpec specification release inputs."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import struct
from pathlib import Path
from uuid import UUID

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conformance/spss-sav-zsav-1.0.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

def validate_transformation_integrity() -> None:
    manifest_paths = {
        "plan": ROOT / "conformance/transformation-plan-0.2.json",
        "frontend": ROOT / "conformance/spss-syntax-frontend-0.2.json",
        "binding": ROOT / "conformance/in-place-transformation-0.2.json",
        "plan_0_1": ROOT / "conformance/transformation-plan-0.1.json",
        "frontend_0_1": ROOT / "conformance/spss-syntax-frontend-0.1.json",
        "binding_0_1": ROOT / "conformance/in-place-transformation-0.1.json",
    }
    expected_metadata = {
        "plan": {"manifest_version": "0.2", "profile": "OpenStatSpec Transformation Plan 0.2", "contract": "openstatspec-transformation-plan-v0.2", "canonicalization": "restricted-rfc8785-utf8-sha256"},
        "frontend": {"manifest_version": "0.2", "profile": "OpenStatSpec SPSS-like Syntax Frontend 0.2", "contract": "openstatspec-spss-syntax-frontend-v0.2"},
        "binding": {"manifest_version": "0.2", "profile": "OpenStatSpec In-Place Transformation Binding 0.2", "contract": "openstatspec-in-place-transformation-v0.2"},
        "plan_0_1": {"manifest_version": "0.1", "profile": "OpenStatSpec Transformation Plan 0.1", "contract": "openstatspec-transformation-plan-v0.1"},
        "frontend_0_1": {"manifest_version": "0.1", "profile": "OpenStatSpec SPSS-like Syntax Frontend 0.1", "contract": "openstatspec-spss-syntax-frontend-v0.1"},
        "binding_0_1": {"manifest_version": "0.1", "profile": "OpenStatSpec In-Place Transformation Binding 0.1", "contract": "openstatspec-in-place-transformation-v0.1"},
    }
    manifests: dict[str, dict[str, object]] = {}
    for name, path in manifest_paths.items():
        document = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(document, dict), f"{path.name}: manifest must be an object.")
        require(isinstance(document.get("cases"), list), f"{path.name}: cases must be an array.")
        for field, expected in expected_metadata[name].items():
            require(document.get(field) == expected, f"{path.name}: {field} declaration differs.")
        identifiers: set[str] = set()
        for case in document["cases"]:
            require(isinstance(case, dict), f"{path.name}: case must be an object.")
            identifier = require_string(case.get("id"), f"{path.name}: case id")
            require(identifier not in identifiers, f"{path.name}: duplicate case id: {identifier}")
            identifiers.add(identifier)
        manifests[name] = document

    links = [
        (manifest_paths["plan"], manifests["plan"]["schema"]),
        (manifest_paths["frontend"], manifests["frontend"]["request_schema"]),
        *[(manifest_paths["frontend"], link) for link in manifests["frontend"]["plan_schemas"].values()],
        (manifest_paths["binding"], manifests["binding"]["audit_schema"]),
        (manifest_paths["plan_0_1"], manifests["plan_0_1"]["schema"]),
        (manifest_paths["frontend_0_1"], manifests["frontend_0_1"]["request_schema"]),
        (manifest_paths["frontend_0_1"], manifests["frontend_0_1"]["plan_schema"]),
    ]
    schema_validators: dict[Path, Draft202012Validator] = {}
    for manifest_path, link in links:
        require(isinstance(link, str) and link and not Path(link).is_absolute(), f"{manifest_path.name}: schema link must be relative.")
        schema_path = (manifest_path.parent / link).resolve()
        require(schema_path.is_file(), f"{manifest_path.name}: schema link does not exist: {link}")
        if schema_path.suffix == ".json":
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            require(isinstance(schema, dict), f"{schema_path.name}: schema must be an object.")
            Draft202012Validator.check_schema(schema)
            schema_validators[schema_path] = Draft202012Validator(schema)
    plan_validator = schema_validators[(manifest_paths["plan"].parent / manifests["plan"]["schema"]).resolve()]
    legacy_plan_validator = schema_validators[(manifest_paths["plan_0_1"].parent / manifests["plan_0_1"]["schema"]).resolve()]
    request_validator = schema_validators[(manifest_paths["frontend"].parent / manifests["frontend"]["request_schema"]).resolve()]
    legacy_request_validator = schema_validators[(manifest_paths["frontend_0_1"].parent / manifests["frontend_0_1"]["request_schema"]).resolve()]

    def canonical_hash(value: object) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def normalized_source_hash(source: str) -> str:
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    frontend_plan_fields = {
        "expected_plan_case", "expected_plan_case_0_1", "expected_plan",
        "expected_plan_0_1", "expected_plan_contract",
    }
    plan_hashes: dict[str, str] = {}
    for case in manifests["plan"]["cases"]:
        require(isinstance(case, dict), "0.2 plan case must be an object.")
        identifier = require_string(case.get("id"), "0.2 plan case id")
        require(plan_validator.is_valid(case.get("plan")), f"{identifier}: plan violates its declared schema.")
        if case.get("expected_error") is None:
            require(isinstance(case.get("plan"), dict), f"{identifier}: successful plan is missing.")
            digest = canonical_hash(case["plan"])
            require(case.get("expected_plan_hash") == digest, f"{identifier}: canonical plan hash differs.")
            plan_hashes[identifier] = digest
        else:
            require(case.get("expected_plan_hash") is None, f"{identifier}: rejected plan hash must be null.")

    legacy_plan_hashes: dict[str, str] = {}
    for case in manifests["plan_0_1"]["cases"]:
        identifier = require_string(case.get("id"), "0.1 plan case id")
        require(legacy_plan_validator.is_valid(case.get("plan")), f"{identifier}: 0.1 plan violates its declared schema.")
        if case.get("expected_error") is None:
            digest = canonical_hash(case.get("plan"))
            require(case.get("expected_plan_hash") == digest, f"{identifier}: canonical 0.1 plan hash differs.")
            legacy_plan_hashes[identifier] = digest
        else:
            require(case.get("expected_plan_hash") is None, f"{identifier}: rejected 0.1 plan hash must be null.")

    for case in manifests["frontend_0_1"]["cases"]:
        identifier = require_string(case.get("id"), "0.1 frontend case id")
        request = case.get("request")
        require(legacy_request_validator.is_valid(request), f"{identifier}: 0.1 request violates its declared schema.")
        source = request.get("source_text")
        if isinstance(source, str):
            require(case.get("expected_source_hash") == normalized_source_hash(source), f"{identifier}: 0.1 source hash differs.")
        if case.get("expected_error") is not None:
            require(frontend_plan_fields.isdisjoint(case), f"{identifier}: failed frontend case contains plan output fields.")
            require(case.get("expected_plan_hash") is None, f"{identifier}: failed frontend plan hash must be absent or null.")
            continue
        if "expected_plan_case" in case:
            reference = case["expected_plan_case"]
            require(reference in legacy_plan_hashes, f"{identifier}: referenced 0.1 plan is missing.")
        else:
            require("expected_plan" in case, f"{identifier}: embedded 0.1 plan is missing.")
            require(legacy_plan_validator.is_valid(case["expected_plan"]), f"{identifier}: embedded 0.1 plan violates its declared schema.")
            digest = canonical_hash(case["expected_plan"])
            require(case.get("expected_plan_hash") == digest, f"{identifier}: embedded 0.1 plan hash differs.")
    legacy_frontend_hashes = {
        case["id"]: (case["expected_plan_hash"], case["expected_source_hash"])
        for case in manifests["frontend_0_1"]["cases"]
        if case.get("expected_error") is None and "expected_plan_hash" in case
    }
    frontend_hashes: dict[str, tuple[str, str]] = {}
    for case in manifests["frontend"]["cases"]:
        require(isinstance(case, dict), "0.2 frontend case must be an object.")
        identifier = require_string(case.get("id"), "0.2 frontend case id")
        request = case.get("request")
        require(request_validator.is_valid(request), f"{identifier}: request violates its declared schema.")
        source = request.get("source_text")
        if isinstance(source, str):
            require(case.get("expected_source_hash") == normalized_source_hash(source), f"{identifier}: source hash differs.")
        if case.get("expected_error") is not None:
            require(frontend_plan_fields.isdisjoint(case), f"{identifier}: failed frontend case contains plan output fields.")
            require(case.get("expected_plan_hash") is None, f"{identifier}: failed frontend plan hash must be absent or null.")
            continue
        if "expected_plan_case" in case:
            reference = case["expected_plan_case"]
            require(reference in plan_hashes and case.get("expected_plan_hash") == plan_hashes[reference], f"{identifier}: referenced 0.2 plan hash differs.")
        elif "expected_plan_case_0_1" in case:
            reference = case["expected_plan_case_0_1"]
            require(reference in legacy_frontend_hashes and case.get("expected_plan_hash") == legacy_frontend_hashes[reference][0], f"{identifier}: referenced 0.1 plan hash differs.")
        else:
            require("expected_plan_0_1" in case, f"{identifier}: embedded plan is missing.")
            require(legacy_plan_validator.is_valid(case["expected_plan_0_1"]), f"{identifier}: embedded plan violates its declared schema.")
            require(case.get("expected_plan_hash") == canonical_hash(case["expected_plan_0_1"]), f"{identifier}: embedded plan hash differs.")
        frontend_hashes[identifier] = (case["expected_plan_hash"], case["expected_source_hash"])

    for case in manifests["binding"]["cases"]:
        if not isinstance(case, dict) or "applied_plan_case" not in case:
            continue
        plan_id, frontend_id = case["applied_plan_case"], case.get("applied_frontend_case")
        require(plan_id in plan_hashes and frontend_id in frontend_hashes, f"{case.get('id')}: applied fixture reference is missing.")
        audit = case.get("expected_audit")
        require(frontend_hashes[frontend_id][0] == plan_hashes[plan_id] and isinstance(audit, dict) and audit.get("plan_hash") == plan_hashes[plan_id] and audit.get("source_hash") == frontend_hashes[frontend_id][1], f"{case.get('id')}: applied fixture hashes differ.")


def require_well_formed_create_table_blocks(
    schema: str,
    context: str,
) -> None:
    matches = list(re.finditer(
        r"(?m)^CREATE TABLE ([A-Za-z_][A-Za-z0-9_]*) \(", schema
    ))
    names = [match.group(1) for match in matches]
    require(
        len(names) == len(set(names)),
        f"{context}: duplicate CREATE TABLE declaration.",
    )
    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(schema)
        )
        terminator = schema.find(");", match.end())
        require(
            terminator != -1 and terminator < next_start,
            f"{context}: CREATE TABLE {match.group(1)} is not terminated "
            "before the next declaration.",
        )


def require_string(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value), f"{context}: must be a non-empty string.")
    return value


def require_string_list(value: object, context: str) -> list[str]:
    require(isinstance(value, list) and bool(value), f"{context}: must be a non-empty list.")
    require(
        all(isinstance(item, str) and item for item in value),
        f"{context}: entries must be non-empty strings.",
    )
    return value


def validate_expected_catalog(identifier: str, catalog: object) -> None:
    require(isinstance(catalog, dict) and bool(catalog), f"{identifier}: expected_catalog must be a non-empty object.")
    allowed = {
        "weight_variable",
        "value_labels",
        "dataset_attributes",
        "variable_attributes",
        "variable_sets",
        "multiple_response_sets",
    }
    require(set(catalog) <= allowed, f"{identifier}: expected_catalog contains an unknown key.")

    if "weight_variable" in catalog:
        require_string(catalog["weight_variable"], f"{identifier}.weight_variable")

    if "value_labels" in catalog:
        labels = catalog["value_labels"]
        require(isinstance(labels, list) and labels, f"{identifier}.value_labels must be non-empty.")
        ordinals: dict[str, list[int]] = {}
        for index, label in enumerate(labels):
            context = f"{identifier}.value_labels[{index}]"
            require(isinstance(label, dict), f"{context}: must be an object.")
            require(set(label) == {"variable", "ordinal", "kind", "value", "label"}, f"{context}: fields are incomplete.")
            variable = require_string(label["variable"], context + ".variable")
            ordinal = label["ordinal"]
            require(isinstance(ordinal, int) and ordinal > 0, f"{context}.ordinal must be positive.")
            kind = label["kind"]
            require(kind in {"numeric", "string"}, f"{context}.kind is invalid.")
            require(
                (kind == "numeric" and isinstance(label["value"], (int, float)) and not isinstance(label["value"], bool))
                or (kind == "string" and isinstance(label["value"], str)),
                f"{context}.value does not match kind.",
            )
            require_string(label["label"], context + ".label")
            ordinals.setdefault(variable, []).append(ordinal)
        for variable, values in ordinals.items():
            require(values == list(range(1, len(values) + 1)), f"{identifier}: value-label ordinals for {variable} are not contiguous.")

    for key in ("dataset_attributes", "variable_attributes"):
        if key not in catalog:
            continue
        attributes = catalog[key]
        require(isinstance(attributes, list) and attributes, f"{identifier}.{key} must be non-empty.")
        seen: set[tuple[str, ...]] = set()
        for index, attribute in enumerate(attributes):
            context = f"{identifier}.{key}[{index}]"
            require(isinstance(attribute, dict), f"{context}: must be an object.")
            required = {"name", "values"} | ({"variable"} if key == "variable_attributes" else set())
            require(set(attribute) == required, f"{context}: fields are incomplete.")
            name = require_string(attribute["name"], context + ".name")
            variable = require_string(attribute["variable"], context + ".variable") if "variable" in attribute else ""
            require_string_list(attribute["values"], context + ".values")
            identity = (variable, name)
            require(identity not in seen, f"{context}: duplicate attribute declaration.")
            seen.add(identity)

    if "variable_sets" in catalog:
        sets = catalog["variable_sets"]
        require(isinstance(sets, list) and sets, f"{identifier}.variable_sets must be non-empty.")
        for index, item in enumerate(sets, 1):
            context = f"{identifier}.variable_sets[{index - 1}]"
            require(isinstance(item, dict) and set(item) == {"ordinal", "name", "members"}, f"{context}: fields are incomplete.")
            require(item["ordinal"] == index, f"{context}.ordinal must be contiguous from one.")
            require_string(item["name"], context + ".name")
            members = require_string_list(item["members"], context + ".members")
            require(len(members) == len(set(members)), f"{context}.members must be unique.")

    if "multiple_response_sets" in catalog:
        sets = catalog["multiple_response_sets"]
        require(isinstance(sets, list) and sets, f"{identifier}.multiple_response_sets must be non-empty.")
        required = {"ordinal", "name", "kind", "label", "counted_kind", "counted_value", "category_labels", "label_source", "members"}
        for index, item in enumerate(sets, 1):
            context = f"{identifier}.multiple_response_sets[{index - 1}]"
            require(isinstance(item, dict) and set(item) == required, f"{context}: fields are incomplete.")
            require(item["ordinal"] == index, f"{context}.ordinal must be contiguous from one.")
            require_string(item["name"], context + ".name")
            require(item["kind"] in {"MD", "MC"}, f"{context}.kind is invalid.")
            require(item["label"] is None or isinstance(item["label"], str), f"{context}.label is invalid.")
            counted_kind = item["counted_kind"]
            require(counted_kind in {None, "numeric", "string"}, f"{context}.counted_kind is invalid.")
            require(
                (counted_kind is None and item["counted_value"] is None)
                or (counted_kind == "numeric" and isinstance(item["counted_value"], (int, float)) and not isinstance(item["counted_value"], bool))
                or (counted_kind == "string" and isinstance(item["counted_value"], str)),
                f"{context}.counted_value does not match counted_kind.",
            )
            require(item["category_labels"] is None or isinstance(item["category_labels"], str), f"{context}.category_labels is invalid.")
            require(item["label_source"] is None or isinstance(item["label_source"], str), f"{context}.label_source is invalid.")
            members = require_string_list(item["members"], context + ".members")
            require(len(members) == len(set(members)), f"{context}.members must be unique.")


def validate_identifier_limit(profile: str, value: object) -> None:
    context = f"dialect profile {profile}.identifier_limit"
    require(isinstance(value, dict), f"{context}: must be an object.")
    require(set(value) == {"value", "unit", "source", "repertoire"}, f"{context}: fields are incomplete.")
    require(isinstance(value["value"], int) and value["value"] > 0, f"{context}.value must be positive.")
    require(value["unit"] in {"bytes", "characters"}, f"{context}.unit must be bytes or characters.")
    require_string(value["source"], context + ".source")
    require_string(value["repertoire"], context + ".repertoire")


def validate_limit_evidence(
    value: object,
    context: str,
    expected_value: int,
    expected_unit: str,
    expected_classification: str,
) -> None:
    require(isinstance(value, dict), f"{context}: must be an object.")
    require(
        set(value) == {"value", "unit", "classification", "source"},
        f"{context}: fields are incomplete.",
    )
    require(value["value"] == expected_value, f"{context}.value is unexpected.")
    require(value["unit"] == expected_unit, f"{context}.unit is unexpected.")
    require(
        value["classification"] == expected_classification,
        f"{context}.classification is unexpected.",
    )
    require_string(value["source"], context + ".source")


def validate_dialect_baseline() -> None:
    path = ROOT / "sql/dialect-profile-baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    require(baseline.get("contract") == "openstatspec-strict-wide-table-v1", "Unexpected SQL dialect contract.")
    common = baseline.get("common")
    require(isinstance(common, dict), "SQL dialect common contract is missing.")
    binding = common.get("catalog_binding")
    require(isinstance(binding, dict), "SQL dialect catalog binding is missing.")
    require(
        set(binding) == {
            "exclusive_namespace_required",
            "exclusive_resolution_required",
            "identity_relation",
            "foreign_object_collision",
        },
        "SQL dialect catalog binding fields are incomplete.",
    )
    require(binding["exclusive_namespace_required"] is True, "Catalog namespace isolation must be required.")
    require(binding["exclusive_resolution_required"] is True, "Exclusive catalog resolution must be required.")
    require(binding["identity_relation"] == "catalog_identity", "Unexpected catalog identity relation.")
    require(binding["foreign_object_collision"] == "fail_without_modification", "Foreign catalog collisions must fail.")
    version_policy = baseline.get("server_version_policy")
    require(isinstance(version_policy, dict), "SQL server version policy is missing.")
    require(
        set(version_policy)
        == {"reviewed_on", "claim_scope", "ci_evidence", "reference_adapter_targets"},
        "SQL server version policy fields are incomplete.",
    )
    require(version_policy["reviewed_on"] == "2026-07-31", "SQL server policy review date is unexpected.")
    require(
        version_policy["claim_scope"] == "maintained_release_series",
        "Server claims must remain conservative release-series claims.",
    )
    require(
        version_policy["ci_evidence"] == "exact_patch_version",
        "Server CI evidence must name exact patch versions.",
    )
    targets = version_policy["reference_adapter_targets"]
    expected_targets = {
        "mysql": {
            "claimed_release_series": ["8.4.x", "9.7.x"],
            "exact_ci_target_versions": ["8.4.11", "9.7.2"],
            "latest_stable_version": "9.7.2",
        },
        "mariadb": {
            "claimed_release_series": ["11.4.x", "11.8.x", "12.3.x"],
            "exact_ci_target_versions": ["11.4.12", "11.8.8", "12.3.2"],
            "latest_stable_version": "12.3.2",
        },
        "postgresql": {
            "claimed_release_series": ["17.x", "18.x"],
            "exact_ci_target_versions": ["17.10", "18.4"],
            "latest_stable_version": "18.4",
        },
        "dolt": {
            "claimed_release_series": ["2.2.x"],
            "minimum_inclusive": "2.2.2",
            "maximum_exclusive": "2.3.0",
            "exact_ci_target_versions": ["2.2.2", "2.2.3"],
            "latest_stable_version": "2.2.3",
        },
    }
    require(
        isinstance(targets, dict) and set(targets) == set(expected_targets),
        "Reference-adapter server target set is incomplete.",
    )
    for engine, expected in expected_targets.items():
        target = targets[engine]
        require(
            isinstance(target, dict) and set(target) == set(expected),
            f"{engine} server target fields are incomplete.",
        )
        require_string_list(target["claimed_release_series"], f"{engine} claimed release series")
        require_string_list(target["exact_ci_target_versions"], f"{engine} exact CI targets")
        require(target == expected, f"{engine} server target policy is unexpected.")
    profiles = baseline.get("profiles")
    require(isinstance(profiles, dict) and profiles, "SQL dialect profiles are missing.")
    expected_modes = {
        "sqlite": ["dedicated_database", "attached_database", "reserved_prefix"],
        "postgresql": ["schema"],
        "mysql_mariadb_innodb": ["database"],
        "dolt": ["database"],
    }
    require(set(profiles) == set(expected_modes), "SQL dialect profile set is incomplete.")
    for name, profile in profiles.items():
        require(isinstance(name, str) and name, "SQL dialect profile name is invalid.")
        require(isinstance(profile, dict), f"SQL dialect profile {name} must be an object.")
        validate_identifier_limit(name, profile.get("identifier_limit"))
        modes = profile.get("catalog_namespace_modes")
        require_string_list(modes, f"dialect profile {name}.catalog_namespace_modes")
        require(modes == expected_modes[name], f"Unexpected catalog namespace modes for {name}.")
    dolt = profiles["dolt"]
    require(
        set(dolt)
        == {
            "engine",
            "transport",
            "identity",
            "claimed_version_range",
            "exact_ci_tested_versions",
            "maximum_columns_default",
            "maximum_source_variables_default",
            "identifier_quoting",
            "identifier_limit",
            "catalog_namespace_modes",
            "catalog_binding_policy",
            "numeric_type",
            "string_type",
            "case_ordinal_type",
            "maximum_row_bytes_default",
            "limit_evidence",
            "storage_evidence",
            "transactional_ddl",
            "failure_cleanup_required",
            "effective_limits_must_be_published",
            "transformation_workflow",
        },
        "Dolt profile fields are incomplete.",
    )
    require(dolt["engine"] == "dolt", "Dolt engine identity is missing.")
    require(dolt["transport"] == "mysql_compatible", "Dolt transport must remain separate from engine identity.")
    identity = dolt["identity"]
    require(isinstance(identity, dict), "Dolt identity declaration is missing.")
    require(
        set(identity)
        == {
            "required_probes",
            "version_comment_normalized_equals",
            "signals_must_be_mutually_consistent",
            "failure_policy",
        },
        "Dolt identity declaration fields are incomplete.",
    )
    require(
        identity["required_probes"] == ["@@version", "@@version_comment", "DOLT_VERSION()"],
        "Dolt positive identity probes are incomplete.",
    )
    require(identity["version_comment_normalized_equals"] == "dolt", "Dolt version-comment identity is unexpected.")
    require(identity["signals_must_be_mutually_consistent"] is True, "Dolt identity signals must agree.")
    require(
        identity["failure_policy"] == "fail_before_catalog_or_dataset_mutation",
        "Dolt identity must fail closed before catalog or dataset mutation.",
    )
    require(
        dolt["claimed_version_range"]
        == {"minimum_inclusive": "2.2.2", "maximum_exclusive": "2.3.0"},
        "Dolt claimed version range is unexpected.",
    )
    require(dolt["exact_ci_tested_versions"] == ["2.2.2", "2.2.3"], "Dolt exact CI-tested versions are unexpected.")
    require(dolt["maximum_columns_default"] == 306, "Dolt physical-column envelope is unexpected.")
    require(dolt["maximum_source_variables_default"] == 305, "Dolt source-variable envelope is unexpected.")
    require(dolt["identifier_quoting"] == "backtick", "Dolt identifier quoting is unexpected.")
    require(dolt["identifier_limit"]["value"] == 64, "Dolt identifier envelope is unexpected.")
    require(dolt["identifier_limit"]["unit"] == "bytes", "Dolt identifiers must be byte-measured.")
    require(
        dolt["identifier_limit"]["repertoire"] == "ASCII-safe generated physical identifiers",
        "Dolt identifier repertoire is unexpected.",
    )
    require(dolt["catalog_binding_policy"] == "dedicated_database", "Dolt needs a dedicated database.")
    require(dolt["numeric_type"] == "DOUBLE", "Dolt numeric type must preserve binary64.")
    require(dolt["string_type"] == "LONGTEXT NOT NULL", "Dolt text type is unexpected.")
    require(dolt["case_ordinal_type"] == "BIGINT NOT NULL PRIMARY KEY", "Dolt case ordinal type is unexpected.")
    require(dolt["maximum_row_bytes_default"] == 65504, "Dolt row envelope is unexpected.")
    evidence = dolt["limit_evidence"]
    require(isinstance(evidence, dict), "Dolt limit evidence is missing.")
    require(
        set(evidence)
        == {
            "maximum_physical_columns",
            "maximum_source_variables",
            "identifier_length",
            "maximum_row_size",
        },
        "Dolt limit evidence set is incomplete.",
    )
    validate_limit_evidence(
        evidence["maximum_physical_columns"],
        "Dolt physical columns",
        306,
        "columns",
        "proposed_adapter_envelope",
    )
    validate_limit_evidence(
        evidence["maximum_source_variables"],
        "Dolt source variables",
        305,
        "variables",
        "proposed_adapter_envelope",
    )
    validate_limit_evidence(
        evidence["identifier_length"],
        "Dolt identifier length",
        64,
        "bytes",
        "observed_exact_version",
    )
    validate_limit_evidence(
        evidence["maximum_row_size"],
        "Dolt row size",
        65504,
        "bytes",
        "proposed_adapter_envelope",
    )
    require(
        "307 physical columns both succeeded" in evidence["maximum_physical_columns"]["source"],
        "Dolt column evidence must state that 307 columns also succeeded.",
    )
    require(
        "no native row-size maximum is claimed" in evidence["maximum_row_size"]["source"],
        "Dolt row evidence must not claim a native boundary.",
    )
    storage = dolt["storage_evidence"]
    require(isinstance(storage, dict) and set(storage) == {"binary64", "text"}, "Dolt storage evidence is incomplete.")
    require(
        storage["binary64"]
        == {
            "type": "DOUBLE",
            "classification": "observed_exact_version",
            "source": "maximum finite binary64 round-tripped exactly on pinned live Dolt 2.2.2",
        },
        "Dolt DOUBLE evidence is unexpected.",
    )
    require(
        storage["text"]["type"] == "LONGTEXT NOT NULL"
        and storage["text"]["observed_value_bytes"] == 65504
        and storage["text"]["classification"] == "observed_exact_version"
        and isinstance(storage["text"]["source"], str)
        and bool(storage["text"]["source"]),
        "Dolt LONGTEXT evidence is unexpected.",
    )
    require(dolt["transactional_ddl"] is False, "Dolt DDL must be treated as non-atomic.")
    require(dolt["failure_cleanup_required"] is True, "Dolt compensating cleanup is required.")
    require(
        dolt["effective_limits_must_be_published"]
        == [
            "maximum_physical_columns",
            "maximum_source_variables",
            "maximum_identifier_bytes",
            "maximum_value_bytes",
            "maximum_row_bytes",
            "maximum_statement_bytes",
        ],
        "Dolt effective limit declarations are incomplete.",
    )
    require(dolt["transformation_workflow"] == "unsupported", "Dolt must not claim the Transformation Workflow.")



JCS_SAFE_INTEGER = 9_007_199_254_740_991


def canonical_json(value: object) -> str:
    """RFC 8785 serialization for this profile's integer-only JSON number domain."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > JCS_SAFE_INTEGER:
            raise ValueError("integer_out_of_range")
        return str(value)
    if isinstance(value, float):
        raise ValueError("non_integer_number")
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("unpaired_surrogate")
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("non_string_key")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        return "{" + ",".join(
            canonical_json(key) + ":" + canonical_json(value[key]) for key in keys
        ) + "}"
    raise ValueError("unsupported_type")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def relation_snapshot_hash(schema_hash: str, rows: list[list[object]]) -> str:
    def value_envelope(value: object, *, ordinal: bool = False) -> dict[str, object]:
        if ordinal:
            require(isinstance(value, int), "Relation snapshot ordinal must be an integer.")
            return {"t": "i", "v": str(value)}
        if value is None:
            return {"t": "null"}
        if isinstance(value, str):
            return {"t": "s", "v": value}
        require(isinstance(value, (int, float)) and not isinstance(value, bool), "Unsupported snapshot value.")
        return {"t": "f64", "v": struct.pack(">d", float(value)).hex()}

    envelope = {
        "hash_kind": "relation_snapshot",
        "hash_version": "openstatspec-relation-snapshot-v1",
        "schema_hash": schema_hash,
        "rows": [
            [value_envelope(row[0], ordinal=True)]
            + [value_envelope(value) for value in row[1:]]
            for row in rows
        ],
    }
    return canonical_hash(envelope)


def validate_transformation_profile() -> None:
    path = ROOT / "conformance/sql-transformation-workflow-0.1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    require(set(manifest) == {"manifest_version", "profile", "contract", "hash_profile", "canonicalization_cases", "fixtures", "cases", "recovery_cases"}, "Transformation manifest fields are incomplete.")
    require(manifest["manifest_version"] == "0.1", "Unexpected transformation manifest version.")
    require(manifest["profile"] == "OpenStatSpec SQL Transformation Workflow 0.1", "Unexpected transformation profile.")
    require(manifest["contract"] == "openstatspec-sql-transformation-workflow-v0.1", "Unexpected transformation contract.")
    require(manifest["hash_profile"] == {
        "json_canonicalization": "RFC8785",
        "hash_kind": "relation_snapshot",
        "hash_algorithm": "sha256",
        "hash_version": "openstatspec-relation-snapshot-v1",
    }, "Unexpected transformation hash profile.")
    for canonical_case in manifest["canonicalization_cases"]:
        if "canonical" in canonical_case:
            require(canonical_json(canonical_case["value"]) == canonical_case["canonical"], f"{canonical_case['id']}: canonical JSON differs.")
        else:
            try:
                canonical_json(canonical_case["value"])
            except ValueError as error:
                require(str(error) == canonical_case["expected_error"], f"{canonical_case['id']}: wrong canonicalization error.")
            else:
                require(False, f"{canonical_case['id']}: canonicalization should fail.")

    fixtures = manifest["fixtures"]
    require(isinstance(fixtures, list) and fixtures, "Transformation fixtures are missing.")
    fixture_map: dict[str, dict[str, object]] = {}
    for fixture in fixtures:
        require(isinstance(fixture, dict) and set(fixture) == {"id", "dialect", "dataset_id", "physical_relation_key", "technical_ordinal", "schema", "rows", "schema_hash", "snapshot_hash"}, "Transformation fixture fields are incomplete.")
        identifier = require_string(fixture["id"], "transformation fixture id")
        require(identifier not in fixture_map, f"Duplicate transformation fixture: {identifier}")
        require(fixture["dialect"] == "sqlite", f"{identifier}: repository fixture must use SQLite.")
        require(fixture["technical_ordinal"] == "__case_ordinal", f"{identifier}: unexpected technical ordinal.")
        require(isinstance(fixture["schema"], dict), f"{identifier}: schema must be an object.")
        require(isinstance(fixture["rows"], list) and fixture["rows"], f"{identifier}: rows are missing.")
        require(fixture["schema_hash"] == canonical_hash(fixture["schema"]), f"{identifier}: schema hash mismatch.")
        require(fixture["snapshot_hash"] == relation_snapshot_hash(fixture["schema_hash"], fixture["rows"]), f"{identifier}: snapshot hash mismatch.")
        fixture_map[identifier] = fixture

    required_cases = {
        "parameterized-filter-materialized", "aggregate-drops-implicit-weight",
        "parameter-free-immutable-view", "reject-view-with-parameters",
        "reject-mutating-sql", "reject-undeclared-relation",
        "reject-input-hash-change", "reject-cyclic-lineage",
        "reject-invalid-weight-propagation", "publication-failure-is-atomic",
        "reject-volatile-function", "reject-external-io-function",
        "reject-tied-order-key",
    }
    required_failures = {
        "reject-view-with-parameters": ("parameter_invalid", "preflight"),
        "reject-mutating-sql": ("unsafe_sql", "ast_validation"),
        "reject-undeclared-relation": ("undeclared_relation_access", "ast_validation"),
        "reject-input-hash-change": ("input_hash_mismatch", "input_snapshot"),
        "reject-cyclic-lineage": ("input_not_immutable", "lineage_validation"),
        "reject-invalid-weight-propagation": ("output_validation_failed", "output_validation"),
        "publication-failure-is-atomic": ("publication_failed", "publication"),
        "reject-volatile-function": ("volatile_sql", "ast_validation"),
        "reject-external-io-function": ("external_io_forbidden", "ast_validation"),
        "reject-tied-order-key": ("non_unique_order_key", "order_validation"),
    }
    cases = manifest["cases"]
    require(isinstance(cases, list) and cases, "Transformation conformance cases are missing.")
    identifiers: set[str] = set()
    case_map: dict[str, dict[str, object]] = {}
    case_fields = {"id", "fixture_id", "transformation_id", "version_number", "dialect_family", "server_version_constraint", "output_mode", "query_sql", "driver_bindings", "parameter_declarations", "parameter_envelopes", "input_envelopes", "order_key", "declared_output_schema", "fault", "row_semantics", "metadata_policy", "expected"}
    expected_fields = {"status", "rows", "schema_hash", "content_hash", "definition_hash", "parameters_hash", "input_set_hash", "events", "invariants"}
    for case in cases:
        require(isinstance(case, dict) and set(case) == case_fields, "Transformation case fields are incomplete.")
        identifier = require_string(case["id"], "transformation case id")
        require(identifier not in identifiers, f"Duplicate transformation case: {identifier}")
        identifiers.add(identifier)
        case_map[identifier] = case
        require(case["fixture_id"] in fixture_map, f"{identifier}: fixture does not exist.")
        require(case["output_mode"] in {"materialized", "view"}, f"{identifier}: invalid output mode.")
        try:
            require(str(UUID(case["transformation_id"])) == case["transformation_id"], f"{identifier}: transformation_id is not a canonical UUID.")
        except (ValueError, TypeError):
            require(False, f"{identifier}: transformation_id is not a UUID.")
        require(isinstance(case["version_number"], int) and case["version_number"] > 0, f"{identifier}: version_number must be positive.")
        require_string(case["query_sql"], f"{identifier}.query_sql")
        normalized_sql = case["query_sql"].replace("\r\n", "\n").replace("\r", "\n")
        require(case["query_sql"] == normalized_sql, f"{identifier}: query_sql is not LF-normalized.")
        require(case["dialect_family"] == "sqlite" and isinstance(case["server_version_constraint"], str), f"{identifier}: dialect declaration is invalid.")
        require(isinstance(case["driver_bindings"], dict), f"{identifier}: driver bindings must be an object.")
        require(isinstance(case["parameter_declarations"], list) and isinstance(case["parameter_envelopes"], list), f"{identifier}: parameter envelopes are missing.")
        require(isinstance(case["input_envelopes"], list) and case["input_envelopes"], f"{identifier}: input envelopes are missing.")
        require(isinstance(case["order_key"], list), f"{identifier}: order_key must be an array.")
        for item in case["order_key"]:
            require(isinstance(item, dict) and set(item) == {"expression", "direction", "nulls", "collation"}, f"{identifier}: order item fields are incomplete.")
            require(item["direction"] in {"ASC", "DESC"} and item["nulls"] in {"FIRST", "LAST"}, f"{identifier}: order direction/nulls are invalid.")
        if case["order_key"]:
            require(" ORDER BY " in case["query_sql"] and " NULLS " in case["query_sql"], f"{identifier}: SQL lacks explicit order semantics.")
        require(isinstance(case["declared_output_schema"], dict) and set(case["declared_output_schema"]) == {"variables", "weight"}, f"{identifier}: output schema must contain variables and weight.")
        output_kinds = {item["physical_name"]: item["logical_storage_kind"] for item in case["declared_output_schema"]["variables"]}
        for item in case["order_key"]:
            require(item["expression"] in output_kinds, f"{identifier}: order expression is not an output column.")
            collatable = output_kinds[item["expression"]] == "string"
            if collatable:
                require(isinstance(item["collation"], str) and bool(item["collation"]), f"{identifier}: textual ordering needs a fixed dialect collation.")
                require(f"{item['expression']} COLLATE {item['collation']}" in case["query_sql"], f"{identifier}: textual SQL order does not use its declared collation.")
            else:
                require(item["collation"] is None, f"{identifier}: non-collatable ordering must declare null collation.")
                require(f"{item['expression']} COLLATE" not in case["query_sql"], f"{identifier}: non-collatable SQL order must not use collation.")
        parent_names = {item["physical_name"] for item in fixture_map[case["fixture_id"]]["schema"]["variables"]} | {fixture_map[case["fixture_id"]]["technical_ordinal"]}
        for variable in case["declared_output_schema"]["variables"]:
            require(isinstance(variable, dict) and {"column_ordinal", "physical_name", "logical_storage_kind", "is_nullable", "lineage_kind", "lineage", "metadata"} <= set(variable), f"{identifier}: output variable descriptor is incomplete.")
            for lineage in variable["lineage"]:
                require(isinstance(lineage, dict) and set(lineage) == {"input_alias", "parent_column", "expression_role"}, f"{identifier}: lineage descriptor is incomplete.")
                require(lineage["input_alias"] == "parent" and lineage["parent_column"] in parent_names, f"{identifier}: lineage does not resolve through its declared input.")
        require(case["fault"] is None or isinstance(case["fault"], dict), f"{identifier}: fault must be null or an object.")
        require(case["row_semantics"] in {"one_to_one", "filter", "aggregate", "join", "reshape", "other"}, f"{identifier}: invalid row semantics.")
        require(case["metadata_policy"] in {"none", "identity_only", "declared"}, f"{identifier}: invalid metadata policy.")
        expected = case["expected"]
        require(isinstance(expected, dict) and set(expected) == expected_fields, f"{identifier}: expected result fields are incomplete.")
        require(expected["status"] in {"succeeded", "failed"}, f"{identifier}: invalid expected status.")
        require(isinstance(expected["events"], list) and isinstance(expected["invariants"], list), f"{identifier}: events/invariants must be arrays.")
        definition = {"contract": manifest["contract"], "transformation_id": case["transformation_id"], "version_number": case["version_number"], "query_sql": normalized_sql, "dialect_family": case["dialect_family"], "server_version_constraint": case["server_version_constraint"], "output_mode": case["output_mode"], "row_semantics": case["row_semantics"], "metadata_policy": case["metadata_policy"], "output_schema": case["declared_output_schema"], "deterministic_order": case["order_key"], "parameter_declarations": case["parameter_declarations"]}
        require(expected["definition_hash"] == canonical_hash(definition), f"{identifier}: definition hash mismatch.")
        require(expected["parameters_hash"] == canonical_hash({"hash_kind": "parameter_set", "hash_version": "openstatspec-parameter-set-v1", "parameters": case["parameter_envelopes"]}), f"{identifier}: parameters hash mismatch.")
        require(expected["input_set_hash"] == canonical_hash({"hash_kind": "input_set", "hash_version": "openstatspec-input-set-v1", "inputs": case["input_envelopes"]}), f"{identifier}: input-set hash mismatch.")
        require([item["parameter_name"] for item in case["parameter_declarations"]] == [item["parameter_name"] for item in case["parameter_envelopes"]] == list(case["driver_bindings"]), f"{identifier}: parameter declaration/binding order differs.")
        require(all(item["input_alias"] for item in case["input_envelopes"]), f"{identifier}: input alias is missing from its hash envelope.")
        if expected["status"] == "succeeded":
            require(expected["events"] == [], f"{identifier}: successful case must have no error events.")
            require(isinstance(expected["rows"], list), f"{identifier}: successful rows are missing.")
            schema_hash = canonical_hash(case["declared_output_schema"])
            require(expected["schema_hash"] == schema_hash, f"{identifier}: output schema hash mismatch.")
            ordinal_rows = [[ordinal, *row] for ordinal, row in enumerate(expected["rows"], 1)]
            require(expected["content_hash"] == relation_snapshot_hash(schema_hash, ordinal_rows), f"{identifier}: output content hash mismatch.")
        else:
            require(expected["rows"] is None and expected["schema_hash"] is None and expected["content_hash"] is None, f"{identifier}: failed output must be null.")
            require(len(expected["events"]) == 1 and set(expected["events"][0]) == {"code", "phase"}, f"{identifier}: failed case needs one exact event.")
            require(identifier in required_failures, f"{identifier}: unexpected failing case.")
            require((expected["events"][0]["code"], expected["events"][0]["phase"]) == required_failures[identifier], f"{identifier}: error event differs from the normative result.")
            require({"failed_run_retained", "no_derived_dataset", "no_published_output"} <= set(expected["invariants"]), f"{identifier}: failure atomicity invariants are incomplete.")
    require(identifiers == required_cases, "Transformation conformance case set is incomplete.")

    recovery_cases = manifest["recovery_cases"]
    require(isinstance(recovery_cases, list), "Transformation recovery cases must be an array.")
    require(len(recovery_cases) == 2, "Transformation recovery case set is incomplete.")
    recovery_fields = {
        "id", "trigger", "initial_status", "staging_relation_key", "event",
        "invariants", "terminal_status_after_reconciliation",
    }
    expected_recovery = {
        "cleanup-failure-quarantines-staging": ("cleanup_failed", {"code": "cleanup_failed", "phase": "cleanup"}),
        "crash-leaves-quarantined-staging": ("process_crash", None),
    }
    recovery_ids: set[str] = set()
    required_recovery_invariants = {
        "no_derived_dataset", "no_published_output",
        "quarantined_staging_not_exposed",
        "run_remains_started_while_staging_exists",
        "reconciliation_required",
        "remove_only_recorded_profile_owned_staging", "success_forbidden",
    }
    for recovery in recovery_cases:
        require(isinstance(recovery, dict) and set(recovery) == recovery_fields, "Transformation recovery case fields are incomplete.")
        identifier = require_string(recovery["id"], "transformation recovery case id")
        require(identifier not in recovery_ids, f"Duplicate transformation recovery case: {identifier}")
        recovery_ids.add(identifier)
        require(identifier in expected_recovery, f"Unexpected transformation recovery case: {identifier}")
        trigger, event = expected_recovery[identifier]
        require(recovery["trigger"] == trigger, f"{identifier}: unexpected recovery trigger.")
        require(recovery["event"] == event, f"{identifier}: unexpected recovery event.")
        require(recovery["initial_status"] == "started", f"{identifier}: quarantined staging must keep the run started.")
        require(recovery["terminal_status_after_reconciliation"] == "failed", f"{identifier}: reconciliation must terminate as failed.")
        require_string(recovery["staging_relation_key"], f"{identifier}.staging_relation_key")
        require(recovery["staging_relation_key"].startswith("sqlite:main.__openstatspec_staging_"), f"{identifier}: staging key is outside the profile-owned namespace.")
        require(set(recovery["invariants"]) == required_recovery_invariants, f"{identifier}: recovery invariants are incomplete.")
    require(recovery_ids == set(expected_recovery), "Transformation recovery case identifiers are incomplete.")

    fixture = fixture_map["core-respondents"]
    columns = fixture["schema"]["variables"]
    connection = sqlite3.connect(":memory:")
    ddl_columns = ["__case_ordinal INTEGER NOT NULL PRIMARY KEY"] + [
        f'"{column["physical_name"]}" {"TEXT" if column["logical_storage_kind"] == "string" else "REAL"}'
        for column in columns
    ]
    connection.execute(f'CREATE TABLE parent ({", ".join(ddl_columns)})')
    placeholders = ",".join("?" for _ in range(len(columns) + 1))
    connection.executemany(f"INSERT INTO parent VALUES ({placeholders})", fixture["rows"])
    for identifier in ("parameterized-filter-materialized", "aggregate-drops-implicit-weight", "parameter-free-immutable-view"):
        case = case_map[identifier]
        rows = [list(row) for row in connection.execute(case["query_sql"], case["driver_bindings"]).fetchall()]
        require(rows == case["expected"]["rows"], f"{identifier}: executable SQL rows differ.")
    tied = case_map["reject-tied-order-key"]
    cursor = connection.execute(tied["query_sql"], tied["driver_bindings"])
    tied_rows = cursor.fetchall()
    names = [item[0] for item in cursor.description]
    key_indexes = [names.index(item["expression"]) for item in tied["order_key"]]
    tuples = [tuple(row[index] for index in key_indexes) for row in tied_rows]
    require(len(tuples) != len(set(tuples)), "Tied-order fixture does not contain a duplicate order tuple.")
    connection.close()

    require(case_map["reject-view-with-parameters"]["driver_bindings"], "Parameterized-view case lacks bindings.")
    require(case_map["reject-mutating-sql"]["query_sql"].startswith("DELETE "), "Mutating-SQL case is not mutating.")
    require("FROM other" in case_map["reject-undeclared-relation"]["query_sql"], "Undeclared-relation case is invalid.")
    require("random()" in case_map["reject-volatile-function"]["query_sql"], "Volatile case lacks a volatile call.")
    require("read_csv(" in case_map["reject-external-io-function"]["query_sql"], "External-I/O case lacks an external call.")
    expected_faults = {"reject-input-hash-change": {"kind": "input_hash_override", "value": "0" * 64}, "reject-cyclic-lineage": {"kind": "lineage_cycle"}, "publication-failure-is-atomic": {"kind": "publication_failure"}}
    for case in cases:
        require(case["fault"] == expected_faults.get(case["id"]), f"{case['id']}: fault structure differs from the normative fixture.")
    lineage_kinds = {"identity", "computed", "aggregate", "constant"}
    expression_roles = {"identity", "contributing", "grouping", "ordering"}
    for case in cases:
        for variable in case["declared_output_schema"]["variables"]:
            require(variable["lineage_kind"] in lineage_kinds, f"{case['id']}: invalid lineage_kind.")
            require(all(item["expression_role"] in expression_roles for item in variable["lineage"]), f"{case['id']}: invalid expression_role.")

    schema = (ROOT / "sql/transformation-workflow-profile-schema.sql").read_text(encoding="utf-8")
    require_well_formed_create_table_blocks(
        schema, "SQL Transformation Workflow schema"
    )
    require_well_formed_create_table_blocks(
        (ROOT / "sql/transformation-plan-profile-schema.sql").read_text(
            encoding="utf-8"
        ),
        "Transformation Plan schema",
    )
    require("CHECK (contract_id = 'openstatspec-sql-transformation-workflow-v0.1')" in schema, "Transformation profile identity is not enforced.")
    require("CHECK (core_contract_id = 'openstatspec-strict-wide-table-v1')" in schema, "Transformation profile does not bind the immutable core contract.")
    for field in ("output_schema_json", "deterministic_order_json", "physical_relation_key", "snapshot_hash_kind", "snapshot_hash_algorithm", "snapshot_hash_version", "content_hash_kind", "content_hash_algorithm", "content_hash_version"):
        require(field in schema, f"Transformation schema field is missing: {field}")
    require("retired_at" not in schema, "Append-only transformation schema must not contain retired_at.")
    for table in ("transformation_profile_identity", "transformation_definition", "transformation_version", "transformation_parameter", "transformation_run", "transformation_run_parameter", "transformation_run_input", "derived_dataset", "derived_variable", "derived_variable_lineage", "derived_dataset_weight_variable", "derived_dataset_disposition_event", "transformation_event"):
        require(f"CREATE TABLE {table} (" in schema, f"Transformation schema table is missing: {table}")
    require("FOREIGN KEY (transformation_version_id, definition_hash)" in schema, "Run is not bound to its immutable definition hash.")
    require("FOREIGN KEY (transformation_run_id, input_ordinal)" in schema, "Lineage is not bound to a run input.")
    require("identity | computed | aggregate | constant" in schema, "DDL lineage_kind enum is incomplete.")
    require("identity | contributing | grouping | ordering" in schema, "DDL expression_role enum is incomplete.")
    require("retired | physical_removal_requested | physical_removed" in schema, "DDL removal protocol states are incomplete.")

    profile = (ROOT / "docs/sql-transformation-workflow-profile-0.1.md").read_text(encoding="utf-8")
    for phrase in ("Lookup relations are forbidden", "openstatspec-relation-snapshot-v1", "openstatspec-parameter-set-v1", "openstatspec-input-set-v1", "physical_relation_key", "physical_removal_requested", "crash reconciler", "non_unique_order_key", "dialect-aware AST parser", "database MUST enforce an authorizer", "`transformation_id`, positive `version_number`", "stored `query_sql` MUST already equal", "non-collatable", "default is insufficient", "`input_alias`"):
        require(phrase in profile, f"Transformation profile requirement is missing: {phrase}")
    example = (ROOT / "examples/sql-transformation-workflow.md").read_text(encoding="utf-8")
    for phrase in ("recoverable quarantined staging", "remain non-terminal `started`", "`succeeded`. An observed cleanup failure"):
        require(phrase in profile, f"Transformation recovery requirement is missing: {phrase}")
    require("FROM parent" in example and ":minimum_age" in example, "Transformation example is incomplete.")
    require('"collation": null' in example and "respondent_id COLLATE BINARY" not in example, "PostgreSQL numeric order example has an invalid collation.")
    print(f"Validated 3 executable-success and {len(cases) - 3} structural-failure SQL workflow cases with {len(fixtures)} executable fixture.")

def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("manifest_version") == "1.0", "Unexpected manifest version.")
    require(
        manifest.get("profile") == "OpenStatSpec SPSS SAV/ZSAV 1.0",
        "Unexpected conformance profile.",
    )

    fixtures = manifest.get("fixtures")
    require(isinstance(fixtures, list) and fixtures, "Fixture manifest is empty.")
    capabilities = manifest.get("required_capabilities")
    require(isinstance(capabilities, list) and capabilities, "Required capabilities are missing.")
    require(
        len(capabilities) == len(set(capabilities))
        and all(isinstance(item, str) and item for item in capabilities),
        "Required capabilities must be unique non-empty strings.",
    )
    allowed_directions = {"import", "export", "semantic_round_trip"}
    required_failure_expectations = {
        "atomic_failure",
        "no_dataset_row",
        "no_data_table",
        "operation_record",
        "fidelity_event_null_dataset_id",
        "target_capability_exceeded",
    }
    identifiers: set[str] = set()
    generator = (ROOT / "conformance/fixtures/generate-fixtures.sps").read_text(
        encoding="utf-8"
    )
    for fixture in fixtures:
        identifier = fixture.get("id")
        source = fixture.get("source")
        require(isinstance(identifier, str) and identifier, "Fixture ID is missing.")
        require(identifier not in identifiers, f"Duplicate fixture ID: {identifier}")
        identifiers.add(identifier)
        require(isinstance(source, str) and source, f"{identifier}: source is missing.")
        directions = fixture.get("directions")
        expectations = fixture.get("expects")
        require(isinstance(directions, list) and directions, f"{identifier}: directions are missing.")
        require(set(directions) <= allowed_directions, f"{identifier}: unknown direction.")
        require(len(directions) == len(set(directions)), f"{identifier}: duplicate direction.")
        require(isinstance(expectations, list) and expectations, f"{identifier}: expectations are missing.")
        require(
            len(expectations) == len(set(expectations))
            and all(isinstance(item, str) and item for item in expectations),
            f"{identifier}: expectations must be unique non-empty strings.",
        )

        expected_catalog = fixture.get("expected_catalog")
        if expected_catalog is not None:
            validate_expected_catalog(identifier, expected_catalog)
        expected_contracts = {
            "value_labels_typed_ordered": "value_labels",
            "long_string_value_labels": "value_labels",
            "dataset_attribute_arrays": "dataset_attributes",
            "variable_attribute_arrays": "variable_attributes",
            "variable_sets_ordered": "variable_sets",
            "multiple_response_md": "multiple_response_sets",
            "multiple_response_mc": "multiple_response_sets",
            "multiple_response_members_ordered": "multiple_response_sets",
            "multiple_response_counted_value": "multiple_response_sets",
            "multiple_response_string_counted_value": "multiple_response_sets",
            "multiple_response_category_label_behavior": "multiple_response_sets",
            "multiple_response_label_source": "multiple_response_sets",
            "weight_variable": "weight_variable",
        }
        for expectation, catalog_key in expected_contracts.items():
            if expectation in expectations:
                require(
                    isinstance(expected_catalog, dict) and catalog_key in expected_catalog,
                    f"{identifier}: {expectation} requires expected_catalog.{catalog_key}.",
                )

        path = ROOT / "conformance" / source
        if identifier == "preflight-failure":
            require(directions == ["import"], "The preflight fixture is import-only.")
            require(set(expectations) == required_failure_expectations, "The preflight expectations are incomplete.")
            require(
                not path.exists(),
                "The target-specific preflight fixture must be generated by the runner.",
            )
            continue

        require(path.is_file(), f"{identifier}: fixture file is missing: {source}")
        expected_header = b"$FL3" if path.suffix.lower() == ".zsav" else b"$FL2"
        require(
            path.read_bytes()[:4] == expected_header,
            f"{identifier}: invalid {path.suffix} file header.",
        )
        require(path.name in generator, f"{identifier}: generator does not name {path.name}.")

    schema = (ROOT / "sql/schema-outline.sql").read_text(encoding="utf-8")
    identity_ddl = schema.split("CREATE TABLE catalog_identity (", 1)[1].split(");", 1)[0]
    for field in ("catalog_identity_key", "contract_id", "schema_version", "created_at"):
        require(field in identity_ddl, f"Catalog identity field is missing: {field}")
    require(
        "CHECK (contract_id = 'openstatspec-strict-wide-table-v1')" in identity_ddl,
        "Catalog identity contract is not enforced by the logical schema.",
    )
    for forbidden in ("specification_status", "specification_release", "specification_commit"):
        require(forbidden not in identity_ddl, f"Catalog identity must not duplicate capability field: {forbidden}")
    dialects = (ROOT / "sql/dialect-profiles.md").read_text(encoding="utf-8")
    require("fixed single-schema `search_path`" in dialects, "PostgreSQL fixed-connection catalog binding is missing.")
    require("connection fixed to that selected database" in dialects, "MySQL fixed-connection catalog binding is missing.")
    for phrase in (
        "## Dolt profile",
        "`profile=dolt`",
        "`engine=dolt`",
        "`@@version_comment` MUST equal `dolt`",
        "`DOLT_VERSION()`",
        "before catalog creation, migration or audit writes",
        "Identity failure always leaves zero database mutation",
        "One dedicated Dolt database",
        "307 physical columns",
        "not an observed Dolt row-size boundary",
        "Only after supported Dolt identity has been established",
        "Unknown or unclaimed identity never reaches this audit path",
        "otherwise empty dedicated database",
        "MAY initialize the normative catalog",
        "immediately verify the new singleton `catalog_identity`",
        "MUST first prove the",
        "selected namespace is empty or already owned",
        "neither empty nor owned MUST fail without modification",
        "SQL Transformation Workflow Profile is unsupported",
    ):
        require(phrase in dialects, f"Dolt normative declaration is missing: {phrase}")
    capabilities = (ROOT / "sql/profile-capabilities.md").read_text(encoding="utf-8")
    for phrase in (
        "selected profile and database engine separately from transport and driver",
        "separate list of exact CI-tested server versions",
        "maximum value, row-size and per-statement limits",
        "transport selection is not product identity",
        "zero database mutation",
    ):
        require(phrase in capabilities, f"Dolt capability requirement is missing: {phrase}")
    require("row-count" not in capabilities, "Capabilities must not invent an unsupported row-count limit.")
    server_policy = (ROOT / "sql/server-version-policy.md").read_text(encoding="utf-8")
    for phrase in (
        "A floating major, minor or",
        "MySQL 26.7 is excluded",
        "Dolt remains an independent, essential profile",
        "`>=3.24.0,<4.0.0`",
        "`>=3.35.0,<4.0.0`",
        "roadmap-only; see the",
    ):
        require(phrase in server_policy, f"SQL server version policy is missing: {phrase}")
    mssql_roadmap = (ROOT / "docs/mssql-dialect-roadmap.md").read_text(encoding="utf-8")
    for phrase in (
        "supported OpenStatSpec target",
        "`mssql-python`",
        "`pyodbc`",
        "`PDO_SQLSRV`",
        "`SERVERPROPERTY`",
        "`ProductVersion`",
        "`mcr.microsoft.com/mssql/server`",
        "exact cumulative-update tag",
        "complete official fixture manifest",
        "`SET XACT_ABORT ON`",
        "`XACT_STATE()`",
        "forbidden while any partial",
    ):
        require(phrase in mssql_roadmap, f"MSSQL roadmap is missing: {phrase}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("Dolt profiles" in readme, "README does not list the independent Dolt profile.")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    require(
        "independent, fail-closed Dolt 2.2.2 SQL profile" in changelog,
        "Changelog does not record the Dolt profile.",
    )

    for table in (
        "catalog_identity",
        "dataset",
        "operation",
        "variable",
        "dataset_weight_variable",
        "value_label",
        "missing_rule",
        "dataset_attribute",
        "variable_attribute",
        "document",
        "variable_set",
        "multiple_response_set",
        "fidelity_event",
    ):
        require(f"CREATE TABLE {table} (" in schema, f"Schema table is missing: {table}")

    validate_transformation_profile()
    validate_transformation_integrity()

    validate_dialect_baseline()
    json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"Validated {len(identifiers) - 1} binary fixtures and one generated preflight fixture.")


if __name__ == "__main__":
    main()
