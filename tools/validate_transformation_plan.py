"""Validate Transformation Plan 0.1 and its SPSS-like frontend fixtures."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from validate_repository import canonical_hash, require, require_string


ROOT = Path(__file__).resolve().parents[1]
PLAN_MANIFEST = ROOT / "conformance/transformation-plan-0.1.json"
FRONTEND_MANIFEST = ROOT / "conformance/spss-syntax-frontend-0.1.json"
PLAN_SCHEMA = ROOT / "transformation/plan-0.1.schema.json"
FRONTEND_SCHEMA = ROOT / "transformation/spss-syntax-frontend-0.1.schema.json"
IN_PLACE_MANIFEST = ROOT / "conformance/in-place-transformation-0.1.json"

IN_PLACE_SUCCESS_IDS = {
    "mysql-recode-and-labels-preserve-dataset-and-table-identity",
    "dolt-recode-and-labels-preserve-controlled-context",
}
IN_PLACE_EXPECTED_ERRORS = {
    "reject-dolt-branch-mismatch": "dolt_branch_mismatch",
    "reject-dolt-head-mismatch": "dolt_head_mismatch",
    "reject-dolt-dirty-working-set": "dolt_working_set_dirty",
    "reject-mysql-nontransactional-create-target": "schema_change_not_atomic",
}
IN_PLACE_FORBIDDEN_ARTIFACTS = {
    "derived_dataset_row",
    "persistent_output_table",
    "full_table_copy",
    "staging_dataset",
    "staging_relation",
    "snapshot_table",
    "rollback_table",
    "dataset_version_row",
    "retirement_or_recovery_row",
    "temporary_object_residue",
}
IN_PLACE_AUDIT_FIELDS = {
    "apply_id",
    "contract_id",
    "database_profile",
    "dataset_id",
    "physical_table_schema",
    "physical_table_name",
    "plan_hash",
    "source_hash",
    "actor",
    "status",
    "dolt_branch",
    "dolt_head_before",
    "dolt_head_after",
    "operation_count",
    "started_at",
    "completed_at",
}


def binary64_value(value: object, context: str) -> tuple[str, str]:
    require(isinstance(value, dict), f"{context}: typed value must be an object.")
    require(set(value) in ({"type", "bits"}, {"type", "value"}), f"{context}: typed value fields are invalid.")
    kind = value.get("type")
    if kind == "binary64":
        bits = value.get("bits")
        require(
            isinstance(bits, str)
            and len(bits) == 16
            and all(character in "0123456789abcdef" for character in bits),
            f"{context}: binary64 bits must be 16 lowercase hex digits.",
        )
        raw = int(bits, 16)
        require((raw >> 52) & 0x7FF != 0x7FF, f"{context}: non-finite binary64 is forbidden.")
        require(bits != "8000000000000000", f"{context}: negative zero must canonicalize to positive zero.")
        return kind, bits
    require(kind == "string" and isinstance(value.get("value"), str), f"{context}: typed value kind is invalid.")
    return "string", value["value"]


def binary64_number(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def validate_result(result: object, context: str) -> set[str]:
    require(isinstance(result, dict), f"{context}: result must be an object.")
    kind = result.get("kind")
    if kind == "literal":
        require(set(result) == {"kind", "value"}, f"{context}: literal result fields are invalid.")
        return {binary64_value(result["value"], context + ".value")[0]}
    require(kind in {"system_missing", "copy"} and set(result) == {"kind"}, f"{context}: result is invalid.")
    return {kind}


def validate_plan(plan: object, context: str) -> str | None:
    require(isinstance(plan, dict) and set(plan) == {"contract", "input_alias", "operations"}, f"{context}: plan fields are invalid.")
    require(plan["contract"] == "openstatspec-transformation-plan-v0.1", f"{context}: contract is invalid.")
    require_string(plan["input_alias"], context + ".input_alias")
    operations = plan["operations"]
    require(isinstance(operations, list) and operations, f"{context}: operations are missing.")
    semantic_error: str | None = None
    for operation_index, operation in enumerate(operations):
        op_context = f"{context}.operations[{operation_index}]"
        require(isinstance(operation, dict), f"{op_context}: operation must be an object.")
        op = operation.get("op")
        if op == "recode":
            require(
                set(operation) == {"op", "source", "target", "target_mode", "rules", "unmatched"},
                f"{op_context}: recode fields are invalid.",
            )
            source = require_string(operation["source"], op_context + ".source")
            target = require_string(operation["target"], op_context + ".target")
            require(not target.startswith("__"), f"{op_context}: reserved target name.")
            mode = operation["target_mode"]
            require(mode in {"create", "replace"}, f"{op_context}: target mode is invalid.")
            require(mode != "replace" or source == target, f"{op_context}: replace target must equal source.")
            rules = operation["rules"]
            require(isinstance(rules, list) and rules, f"{op_context}: rules are missing.")
            result_kinds: set[str] = set()
            for rule_index, rule in enumerate(rules):
                rule_context = f"{op_context}.rules[{rule_index}]"
                require(isinstance(rule, dict) and set(rule) == {"match", "result"}, f"{rule_context}: fields are invalid.")
                match = rule["match"]
                require(isinstance(match, dict), f"{rule_context}.match must be an object.")
                match_kind = match.get("kind")
                if match_kind == "values":
                    require(set(match) == {"kind", "values"}, f"{rule_context}.match fields are invalid.")
                    require(isinstance(match["values"], list) and match["values"], f"{rule_context}: values are missing.")
                    for value_index, value in enumerate(match["values"]):
                        binary64_value(value, f"{rule_context}.match.values[{value_index}]")
                elif match_kind == "range":
                    require(set(match) == {"kind", "lower", "upper"}, f"{rule_context}.match fields are invalid.")
                    lower_kind, lower_bits = binary64_value(match["lower"], rule_context + ".match.lower")
                    upper_kind, upper_bits = binary64_value(match["upper"], rule_context + ".match.upper")
                    require(lower_kind == upper_kind == "binary64", f"{rule_context}: range endpoints must be binary64.")
                    if binary64_number(lower_bits) > binary64_number(upper_bits):
                        semantic_error = semantic_error or "invalid_numeric_range"
                else:
                    require(match_kind == "system_missing" and set(match) == {"kind"}, f"{rule_context}.match is invalid.")
                result_kinds.update(validate_result(rule["result"], rule_context + ".result"))
            result_kinds.update(validate_result(operation["unmatched"], op_context + ".unmatched"))
            literal_kinds = result_kinds & {"binary64", "string"}
            if len(literal_kinds) > 1:
                semantic_error = semantic_error or "mixed_result_types"
        elif op == "set_variable_label":
            require(set(operation) == {"op", "variable", "label"}, f"{op_context}: variable-label fields are invalid.")
            require_string(operation["variable"], op_context + ".variable")
            require(isinstance(operation["label"], str), f"{op_context}.label must be a string.")
        elif op == "replace_value_labels":
            require(set(operation) == {"op", "variable", "labels"}, f"{op_context}: value-label fields are invalid.")
            require_string(operation["variable"], op_context + ".variable")
            labels = operation["labels"]
            require(isinstance(labels, list) and labels, f"{op_context}: labels are missing.")
            seen: set[tuple[str, str]] = set()
            for label_index, label in enumerate(labels):
                label_context = f"{op_context}.labels[{label_index}]"
                require(isinstance(label, dict) and set(label) == {"value", "label"}, f"{label_context}: fields are invalid.")
                key = binary64_value(label["value"], label_context + ".value")
                if key in seen:
                    semantic_error = semantic_error or "duplicate_value_label"
                seen.add(key)
                require(isinstance(label["label"], str), f"{label_context}.label must be a string.")
        else:
            require(False, f"{op_context}: unknown operation.")
    return semantic_error


def validate_plan_manifest() -> dict[str, dict[str, object]]:
    manifest = json.loads(PLAN_MANIFEST.read_text(encoding="utf-8"))
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"manifest_version", "profile", "contract", "schema", "cases"},
        "Transformation Plan manifest fields are invalid.",
    )
    require(manifest["manifest_version"] == "0.1", "Unexpected Transformation Plan manifest version.")
    require(manifest["profile"] == "OpenStatSpec Transformation Plan 0.1", "Unexpected Transformation Plan profile.")
    require(manifest["contract"] == "openstatspec-transformation-plan-v0.1", "Unexpected Transformation Plan contract.")
    require(manifest["schema"] == "../transformation/plan-0.1.schema.json", "Unexpected Transformation Plan schema path.")
    expected_cases = {
        "numeric-recode-and-declared-labels": None,
        "string-value-label-replacement": None,
        "reject-descending-range": "invalid_numeric_range",
        "reject-duplicate-value-label": "duplicate_value_label",
    }
    case_map: dict[str, dict[str, object]] = {}
    for case in manifest["cases"]:
        require(isinstance(case, dict) and set(case) == {"id", "plan", "expected_plan_hash", "expected_error"}, "Transformation Plan case fields are invalid.")
        identifier = require_string(case["id"], "Transformation Plan case id")
        require(identifier not in case_map, f"Duplicate Transformation Plan case: {identifier}")
        case_map[identifier] = case
        error = validate_plan(case["plan"], identifier)
        require(error == case["expected_error"] == expected_cases.get(identifier), f"{identifier}: semantic result differs.")
        if error is None:
            require(case["expected_plan_hash"] == canonical_hash(case["plan"]), f"{identifier}: plan hash differs.")
        else:
            require(case["expected_plan_hash"] is None, f"{identifier}: invalid plan must not claim a hash.")
    require(set(case_map) == set(expected_cases), "Transformation Plan conformance case set is incomplete.")
    return case_map


def validate_frontend_manifest(plan_cases: dict[str, dict[str, object]]) -> int:
    manifest = json.loads(FRONTEND_MANIFEST.read_text(encoding="utf-8"))
    require(
        isinstance(manifest, dict)
        and set(manifest)
        == {"manifest_version", "profile", "contract", "plan_contract", "request_schema", "plan_schema", "cases"},
        "SPSS frontend manifest fields are invalid.",
    )
    require(manifest["manifest_version"] == "0.1", "Unexpected SPSS frontend manifest version.")
    require(manifest["profile"] == "OpenStatSpec SPSS-like Syntax Frontend 0.1", "Unexpected SPSS frontend profile.")
    require(manifest["contract"] == "openstatspec-spss-syntax-frontend-v0.1", "Unexpected SPSS frontend contract.")
    require(manifest["plan_contract"] == "openstatspec-transformation-plan-v0.1", "Unexpected frontend plan contract.")
    expected_errors = {
        "recode-labels-and-value-labels": None,
        "in-place-recode-default-copy": None,
        "string-value-labels": None,
        "recode-varlists-positionally": None,
        "value-label-varlists-and-groups": None,
        "reject-unknown-command": "unsupported_spss_command",
        "reject-unknown-variable": "unknown_variable",
        "reject-nonfinal-else": "else_not_last",
        "reject-string-system-missing": "system_missing_for_string",
        "reject-duplicate-value-label": "duplicate_value_label",
        "reject-string-target-without-declaration": "string_target_requires_declaration",
        "reject-comment-command": "unsupported_spss_command",
        "reject-inline-comment": "spss_syntax_error",
    }
    identifiers: set[str] = set()
    for case in manifest["cases"]:
        require(isinstance(case, dict), "SPSS frontend case must be an object.")
        identifier = require_string(case.get("id"), "SPSS frontend case id")
        require(identifier not in identifiers, f"Duplicate SPSS frontend case: {identifier}")
        identifiers.add(identifier)
        request = case.get("request")
        require(isinstance(request, dict) and set(request) == {"contract", "input_alias", "input_schema", "source_text"}, f"{identifier}: request fields are invalid.")
        require(request["contract"] == manifest["contract"], f"{identifier}: request contract differs.")
        source = require_string(request["source_text"], f"{identifier}.source_text")
        require(source == source.replace("\r\n", "\n").replace("\r", "\n"), f"{identifier}: source is not LF-normalized.")
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        require(case.get("expected_source_hash") == source_hash, f"{identifier}: source hash differs.")
        require(case.get("expected_error") == expected_errors.get(identifier), f"{identifier}: expected diagnostic differs.")
        if case["expected_error"] is None:
            if "expected_plan_case" in case:
                allowed = {"id", "request", "expected_plan_case", "expected_source_hash", "expected_error"}
                require(set(case) == allowed | ({"expected_output_metadata"} if "expected_output_metadata" in case else set()), f"{identifier}: fields are invalid.")
                plan_case = plan_cases.get(case["expected_plan_case"])
                require(plan_case is not None and plan_case["expected_error"] is None, f"{identifier}: referenced plan case is invalid.")
            else:
                allowed = {"id", "request", "expected_plan", "expected_plan_hash", "expected_source_hash", "expected_error"}
                require(set(case) == allowed | ({"expected_output_metadata"} if "expected_output_metadata" in case else set()), f"{identifier}: fields are invalid.")
                require(validate_plan(case["expected_plan"], identifier + ".expected_plan") is None, f"{identifier}: expected plan is invalid.")
                require(case["expected_plan_hash"] == canonical_hash(case["expected_plan"]), f"{identifier}: expected plan hash differs.")
            if identifier == "in-place-recode-default-copy":
                require(case.get("expected_output_metadata") == {
                    "q1": {
                        "variable_label": "Original score",
                        "value_labels": [{
                            "value": {"type": "binary64", "bits": "3ff0000000000000"},
                            "label": "Original one",
                        }],
                    },
                }, f"{identifier}: metadata preservation proof differs.")
        else:
            require(set(case) == {"id", "request", "expected_source_hash", "expected_error"}, f"{identifier}: failure fields are invalid.")
    require(identifiers == set(expected_errors), "SPSS frontend conformance case set is incomplete.")
    return len(identifiers)


def validate_in_place_failure_case(case: dict[str, object], identifier: str) -> None:
    if identifier == "reject-mysql-nontransactional-create-target":
        require(
            set(case)
            == {"id", "database_profile", "source_text", "expected_error",
                "mutation_started"},
            f"{identifier}: failure fields are invalid.",
        )
        require(case["database_profile"] == "mysql", f"{identifier}: profile differs.")
        require(" INTO " in case["source_text"].upper(), f"{identifier}: create target is missing.")
        require(
            case["expected_error"] == IN_PLACE_EXPECTED_ERRORS[identifier],
            f"{identifier}: diagnostic differs.",
        )
        require(case["mutation_started"] is False, f"{identifier}: mutation starts.")
        return
    require(
        set(case)
        == {"id", "database_profile", "expected_context", "observed_context",
            "expected_error", "mutation_started"},
        f"{identifier}: failure fields are invalid.",
    )
    require(case["database_profile"] == "dolt", f"{identifier}: failure must use Dolt.")
    expected, observed = case["expected_context"], case["observed_context"]
    require(
        isinstance(expected, dict)
        and set(expected) == {"branch", "head"}
        and isinstance(observed, dict)
        and set(observed) == {"branch", "head", "working_set_clean"},
        f"{identifier}: controlled context is invalid.",
    )
    require(
        case["expected_error"] == IN_PLACE_EXPECTED_ERRORS[identifier],
        f"{identifier}: diagnostic differs.",
    )
    require(case["mutation_started"] is False, f"{identifier}: mutation starts.")
    if identifier == "reject-dolt-branch-mismatch":
        valid = (
            observed["branch"] != expected["branch"]
            and observed["head"] == expected["head"]
            and observed["working_set_clean"] is True
        )
    elif identifier == "reject-dolt-head-mismatch":
        valid = (
            observed["branch"] == expected["branch"]
            and observed["head"] != expected["head"]
            and observed["working_set_clean"] is True
        )
    else:
        valid = (
            observed["branch"] == expected["branch"]
            and observed["head"] == expected["head"]
            and observed["working_set_clean"] is False
        )
    require(valid, f"{identifier}: fixture does not isolate its declared failure.")


def validate_in_place_success_case(case: dict[str, object], identifier: str) -> None:
    require(
        set(case)
        == {"id", "database_profile", "source_text", "before", "after",
            "forbidden_artifacts", "required_audit_fields"},
        f"{identifier}: success fields are invalid.",
    )
    before, after = case["before"], case["after"]
    require(
        isinstance(before, dict) and isinstance(after, dict),
        f"{identifier}: identity snapshots are invalid.",
    )
    for field in ("dataset_id", "physical_table_schema", "physical_table_name"):
        require(before[field] == after[field], f"{identifier}: {field} changes.")
    require(
        before["dataset_count"] == after["dataset_count"],
        f"{identifier}: dataset count grows.",
    )
    require(
        before["persistent_data_table_count"] == after["persistent_data_table_count"],
        f"{identifier}: persistent data-table count grows.",
    )
    require(
        set(case["forbidden_artifacts"]) == IN_PLACE_FORBIDDEN_ARTIFACTS,
        f"{identifier}: forbidden-artifact proof is incomplete.",
    )
    require(
        set(case["required_audit_fields"]) == IN_PLACE_AUDIT_FIELDS,
        f"{identifier}: compact audit fields are incomplete.",
    )
    require(
        " INTO " not in case["source_text"].upper(),
        f"{identifier}: implicit-commit success creates a target.",
    )
    require(
        after.get("same_table_recode_target") == "score"
        and "same_table_has_column" not in after,
        f"{identifier}: success does not prove an existing-target recode.",
    )
    if case["database_profile"] == "mysql":
        require(
            not any(key.startswith("dolt_") for key in before | after),
            f"{identifier}: non-Dolt case contains Dolt context.",
        )
    else:
        require(case["database_profile"] == "dolt", f"{identifier}: unexpected profile.")
        require(
            before["dolt_branch"] == after["dolt_branch"]
            and before["dolt_head"] == after["dolt_head"],
            f"{identifier}: Dolt branch/HEAD changes.",
        )
        require(after["dolt_commit_performed"] is False, f"{identifier}: Dolt commit.")


def validate_in_place_manifest() -> None:
    manifest = json.loads(IN_PLACE_MANIFEST.read_text(encoding="utf-8"))
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"manifest_version", "profile", "contract", "cases"},
        "In-place manifest fields are invalid.",
    )
    require(manifest["manifest_version"] == "0.1", "Unexpected in-place manifest version.")
    require(
        manifest["profile"] == "OpenStatSpec In-Place Transformation Binding 0.1",
        "Unexpected in-place profile.",
    )
    require(
        manifest["contract"] == "openstatspec-in-place-transformation-v0.1",
        "Unexpected in-place contract.",
    )
    cases = manifest["cases"]
    require(isinstance(cases, list), "In-place cases must be an array.")
    case_map = {require_string(case.get("id"), "In-place case id"): case for case in cases}
    require(len(case_map) == len(cases), "Duplicate in-place case.")
    require(
        set(case_map) == IN_PLACE_SUCCESS_IDS | set(IN_PLACE_EXPECTED_ERRORS),
        "In-place conformance case set is incomplete.",
    )
    for identifier in IN_PLACE_SUCCESS_IDS:
        validate_in_place_success_case(case_map[identifier], identifier)
    for identifier in IN_PLACE_EXPECTED_ERRORS:
        validate_in_place_failure_case(case_map[identifier], identifier)


def validate_repository_links() -> None:
    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    frontend_schema = json.loads(FRONTEND_SCHEMA.read_text(encoding="utf-8"))
    require(plan_schema["$id"].endswith("transformation-plan-0.1.schema.json"), "Transformation Plan schema ID is invalid.")
    require(frontend_schema["$id"].endswith("spss-syntax-frontend-0.1.schema.json"), "SPSS frontend schema ID is invalid.")
    plan_sql = (ROOT / "sql/transformation-plan-profile-schema.sql").read_text(encoding="utf-8")
    require("CREATE TABLE transformation_apply (" in plan_sql, "Compact apply audit table is missing.")
    require(
        "openstatspec-in-place-transformation-v0.1" in plan_sql
        and "openstatspec-dolt-in-place-transformation-v0.1" not in plan_sql,
        "Compact apply audit does not use the generic in-place contract.",
    )
    for field in ("database_profile", "physical_table_schema", "physical_table_name"):
        require(field in plan_sql, f"Compact apply audit field is missing: {field}")
    for forbidden in (
        "transformation_plan_version",
        "transformation_plan_compilation",
        "transformation_plan_run_binding",
        "transformation_run_artifact",
    ):
        require(forbidden not in plan_sql, f"Forbidden history/copy audit relation remains: {forbidden}")
    binding = (ROOT / "docs/transformation-plan-sql-binding-0.1.md").read_text(encoding="utf-8")
    binding_normalized = " ".join(binding.split())
    for phrase in (
        "dataset_id`, physical schema, and physical table name remain unchanged",
        "MUST NOT publish a derived dataset",
        "does not version successful data states",
        "MUST NOT call `DOLT_COMMIT`",
        "clean Dolt working set",
        "For a non-Dolt profile every Dolt-specific field is NULL",
        "MySQL-family implicit-commit DDL",
        "schema_change_not_atomic",
    ):
        require(phrase in binding_normalized, f"In-place binding requirement is missing: {phrase}")

    validate_in_place_manifest()


def validate_all() -> tuple[int, int]:
    plan_cases = validate_plan_manifest()
    frontend_count = validate_frontend_manifest(plan_cases)
    validate_repository_links()
    from validate_transformation_plan_0_2 import validate_all as validate_0_2

    validate_0_2()
    return len(plan_cases), frontend_count


def main() -> None:
    plan_count, frontend_count = validate_all()
    print(
        f"Validated {plan_count} Transformation Plan and "
        f"{frontend_count} SPSS frontend conformance cases."
    )


if __name__ == "__main__":
    main()
