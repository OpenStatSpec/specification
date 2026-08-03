"""Validate the additive Transformation Plan and SPSS frontend 0.2 fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator


from validate_repository import canonical_hash, require, require_string
from validate_transformation_plan import validate_plan as validate_plan_0_1


ROOT = Path(__file__).resolve().parents[1]
PLAN_0_1 = ROOT / "conformance/transformation-plan-0.1.json"
FRONTEND_0_1 = ROOT / "conformance/spss-syntax-frontend-0.1.json"
PLAN_SCHEMA_0_1 = ROOT / "transformation/plan-0.1.schema.json"
PLAN = ROOT / "conformance/transformation-plan-0.2.json"
FRONTEND = ROOT / "conformance/spss-syntax-frontend-0.2.json"
IN_PLACE = ROOT / "conformance/in-place-transformation-0.2.json"
AUDIT_SCHEMA = ROOT / "sql/transformation-plan-profile-schema.sql"
PLAN_SCHEMA = ROOT / "transformation/plan-0.2.schema.json"
FRONTEND_SCHEMA = ROOT / "transformation/spss-syntax-frontend-0.2.schema.json"


def typed_value(value: object, context: str) -> str:
    require(isinstance(value, dict), f"{context}: typed value must be an object.")
    if value.get("type") == "binary64":
        require(set(value) == {"type", "bits"}, f"{context}: binary64 fields differ.")
        bits = value["bits"]
        require(
            isinstance(bits, str)
            and len(bits) == 16
            and all(character in "0123456789abcdef" for character in bits),
            f"{context}: binary64 bits differ.",
        )
        exponent = (int(bits, 16) >> 52) & 0x7FF
        require(exponent != 0x7FF and bits != "8000000000000000", f"{context}: noncanonical binary64.")
        return "numeric"
    require(
        value.get("type") == "string"
        and set(value) == {"type", "value"}
        and isinstance(value.get("value"), str),
        f"{context}: string value differs.",
    )
    return "string"


def typed_value_key(value: object, context: str) -> tuple[str, str]:
    kind = typed_value(value, context)
    return (kind, value["bits"] if kind == "numeric" else value["value"])


def operand(value: object, context: str) -> str:
    require(isinstance(value, dict), f"{context}: operand must be an object.")
    if value.get("kind") == "variable":
        require(set(value) == {"kind", "variable"}, f"{context}: variable operand fields differ.")
        require_string(value["variable"], context + ".variable")
        return "variable"
    require(value.get("kind") == "literal" and set(value) == {"kind", "value"}, f"{context}: operand differs.")
    return typed_value(value["value"], context + ".value")


def predicate(value: object, context: str) -> bool:
    require(isinstance(value, dict), f"{context}: predicate must be an object.")
    if value.get("expression") == "comparison":
        require(set(value) == {"expression", "left", "operator", "right"}, f"{context}: comparison fields differ.")
        require(value["operator"] in {"=", "<", "<=", ">", ">="}, f"{context}: comparison operator differs.")
        kinds = {operand(value["left"], context + ".left"), operand(value["right"], context + ".right")}
        return "string" in kinds
    require(value.get("expression") == "boolean", f"{context}: expression kind differs.")
    require(set(value) == {"expression", "operator", "operands"}, f"{context}: boolean fields differ.")
    require(value["operator"] in {"and", "or"}, f"{context}: boolean operator differs.")
    children = value["operands"]
    require(isinstance(children, list) and len(children) >= 2, f"{context}: boolean operands differ.")
    for index, child in enumerate(children):
        require(
            not (
                isinstance(child, dict)
                and child.get("expression") == "boolean"
                and child.get("operator") == value["operator"]
            ),
            f"{context}.operands[{index}]: same-operator boolean chain must be flattened.",
        )
    return any(predicate(child, f"{context}.operands[{index}]") for index, child in enumerate(children))


def validate_plan(plan: object, context: str) -> str | None:
    require(isinstance(plan, dict) and set(plan) == {"contract", "input_alias", "operations"}, f"{context}: plan fields differ.")
    require(plan["contract"] == "openstatspec-transformation-plan-v0.2", f"{context}: contract differs.")
    require_string(plan["input_alias"], context + ".input_alias")
    operations = plan["operations"]
    require(isinstance(operations, list) and operations, f"{context}: operations missing.")
    semantic_error = None
    allowed = {
        "assign", "conditional_assign", "set_variable_label", "replace_value_labels",
        "set_format", "set_measurement_level", "execute", "recode",
    }
    for index, operation in enumerate(operations):
        op_context = f"{context}.operations[{index}]"
        require(isinstance(operation, dict) and operation.get("op") in allowed, f"{op_context}: operation differs.")
        op = operation["op"]
        if op == "assign":
            require(set(operation) == {"op", "target", "target_mode", "value"}, f"{op_context}: assign fields differ.")
            target = require_string(operation["target"], op_context + ".target")
            require(operation["target_mode"] in {"create", "replace"}, f"{op_context}: target mode differs.")
            if target.startswith("__"):
                semantic_error = semantic_error or "reserved_target_name"
            if operand(operation["value"], op_context + ".value") == "string":
                semantic_error = semantic_error or "expression_type_unsupported"
        elif op == "conditional_assign":
            require(set(operation) == {"op", "condition", "target", "value"}, f"{op_context}: conditional fields differ.")
            target = require_string(operation["target"], op_context + ".target")
            string_predicate = predicate(operation["condition"], op_context + ".condition")
            if target.startswith("__"):
                semantic_error = semantic_error or "reserved_target_name"
            string_value = operand(operation["value"], op_context + ".value") == "string"
            if string_predicate or string_value:
                semantic_error = semantic_error or "expression_type_unsupported"
        elif op == "set_variable_label":
            require(set(operation) == {"op", "variable", "label"} and isinstance(operation["label"], str), f"{op_context}: label fields differ.")
        elif op == "replace_value_labels":
            require(set(operation) == {"op", "variable", "labels"} and isinstance(operation["labels"], list), f"{op_context}: value labels differ.")
            require_string(operation["variable"], op_context + ".variable")
            require(operation["labels"], f"{op_context}: labels missing.")
            seen: set[tuple[str, str]] = set()
            for label_index, label in enumerate(operation["labels"]):
                require(set(label) == {"value", "label"} and isinstance(label["label"], str), f"{op_context}.labels[{label_index}]: fields differ.")
                key = typed_value_key(label["value"], f"{op_context}.labels[{label_index}].value")
                if key in seen:
                    semantic_error = semantic_error or "duplicate_value_label"
                seen.add(key)
        elif op == "set_format":
            require(set(operation) == {"op", "variable", "family", "width", "decimals"}, f"{op_context}: format fields differ.")
            require(operation["family"] == "F", f"{op_context}: format family differs.")
            width, decimals = operation["width"], operation["decimals"]
            require(isinstance(width, int) and 1 <= width <= 40, f"{op_context}: width differs.")
            require(isinstance(decimals, int) and 0 <= decimals <= 16, f"{op_context}: decimals differ.")
            if decimals and width < decimals + 2:
                semantic_error = semantic_error or "invalid_format"
        elif op == "set_measurement_level":
            require(set(operation) == {"op", "variable", "level"}, f"{op_context}: level fields differ.")
            require(operation["level"] in {"nominal", "ordinal", "scale"}, f"{op_context}: level differs.")
        elif op == "execute":
            require(set(operation) == {"op"}, f"{op_context}: execute fields differ.")
        else:
            require(op == "recode", f"{op_context}: unknown operation.")
            legacy_error = validate_plan_0_1(
                {"contract": "openstatspec-transformation-plan-v0.1",
                 "input_alias": plan["input_alias"],
                 "operations": [operation]},
                op_context,
            )
            semantic_error = semantic_error or legacy_error
    return semantic_error


def validate_plan_manifest() -> dict[str, dict[str, object]]:
    manifest = json.loads(PLAN.read_text(encoding="utf-8"))
    require(set(manifest) == {"manifest_version", "profile", "contract", "schema", "canonicalization", "cases"}, "0.2 plan manifest fields differ.")
    require(manifest["manifest_version"] == "0.2", "0.2 plan manifest version differs.")
    require(manifest["contract"] == "openstatspec-transformation-plan-v0.2", "0.2 plan contract differs.")
    require(manifest["canonicalization"] == "restricted-rfc8785-utf8-sha256", "0.2 canonicalization differs.")
    cases = {}
    expected = {
        "sequential-conditional-binary-existing-target": None,
        "three-term-and-flattens-source-order": None,
        "reject-string-predicate": "expression_type_unsupported",
        "nested-or-inequalities-variable-operands-create": None,
        "reject-invalid-format": "invalid_format",
        "reject-reserved-assignment-target": "reserved_target_name",
        "reject-duplicate-value-label": "duplicate_value_label",
    }
    for case in manifest["cases"]:
        require(set(case) == {"id", "plan", "expected_plan_hash", "expected_error"}, "0.2 plan case fields differ.")
        identifier = require_string(case["id"], "0.2 plan case id")
        require(identifier not in cases, f"Duplicate 0.2 plan case: {identifier}")
        cases[identifier] = case
        error = validate_plan(case["plan"], identifier)
        require(error == case["expected_error"] == expected.get(identifier), f"{identifier}: semantic result differs.")
        if error is None:
            require(case["expected_plan_hash"] == canonical_hash(case["plan"]), f"{identifier}: golden plan hash differs.")
        else:
            require(case["expected_plan_hash"] is None, f"{identifier}: invalid plan claims a hash.")
    require(set(cases) == set(expected), "0.2 plan case set differs.")
    return cases


def validate_frontend(plan_cases: dict[str, dict[str, object]]) -> int:
    manifest = json.loads(FRONTEND.read_text(encoding="utf-8"))
    require(set(manifest) == {"manifest_version", "profile", "contract", "plan_contracts", "request_schema", "plan_schemas", "cases"}, "0.2 frontend manifest fields differ.")
    require(manifest["contract"] == "openstatspec-spss-syntax-frontend-v0.2", "0.2 frontend contract differs.")
    require(manifest["plan_contracts"] == [
        "openstatspec-transformation-plan-v0.1",
        "openstatspec-transformation-plan-v0.2",
    ], "0.2 frontend plan contracts differ.")
    require(manifest["plan_schemas"] == {
        "openstatspec-transformation-plan-v0.1": "../transformation/plan-0.1.schema.json",
        "openstatspec-transformation-plan-v0.2": "../transformation/plan-0.2.schema.json",
    }, "0.2 frontend plan-schema mapping differs.")
    legacy_manifest = json.loads(FRONTEND_0_1.read_text(encoding="utf-8"))
    legacy_cases = {case["id"]: case for case in legacy_manifest["cases"]}
    identifiers = set()
    expected_failures = {
        "reject-string-expression": "expression_type_unsupported",
        "reject-missing-conditional-target": "conditional_target_missing",
        "reject-invalid-format": "invalid_format",
    }
    for case in manifest["cases"]:
        identifier = require_string(case["id"], "0.2 frontend case id")
        require(identifier not in identifiers, f"Duplicate 0.2 frontend case: {identifier}")
        identifiers.add(identifier)
        request = case["request"]
        require(request["contract"] == manifest["contract"], f"{identifier}: request contract differs.")
        source = request["source_text"].replace("\r\n", "\n").replace("\r", "\n")
        require(source == request["source_text"], f"{identifier}: source is not normalized.")
        require(case["expected_source_hash"] == hashlib.sha256(source.encode("utf-8")).hexdigest(), f"{identifier}: source hash differs.")
        if identifier in expected_failures:
            require(
                set(case) == {"id", "request", "expected_source_hash", "expected_error"},
                f"{identifier}: frontend failure fields differ.",
            )
            require(
                case["expected_error"] == expected_failures[identifier],
                f"{identifier}: frontend diagnostic differs.",
            )
        elif "expected_plan_case" in case:
            require(case["expected_error"] is None, f"{identifier}: frontend success claims an error.")
            require(set(case) == {"id", "request", "expected_plan_case", "expected_plan_hash", "expected_source_hash", "expected_error"}, f"{identifier}: frontend success fields differ.")
            require(case["expected_plan_case"] in plan_cases, f"{identifier}: plan fixture missing.")
            require(case["expected_plan_hash"] == plan_cases[case["expected_plan_case"]]["expected_plan_hash"], f"{identifier}: plan hash link differs.")
            required_tokens = {
                "compute-if-labels-format-level-execute-existing-target": (
                    "COMPUTE ", "IF (", " AND ", "FORMATS ", "VARIABLE LEVEL ", "EXECUTE.",
                ),
                "three-term-and-flattens-source-order": (
                    "IF (", "source_a = 1 AND source_b = 1 AND source_c = 1", "EXECUTE.",
                ),
                "parenthesized-three-term-and-flattens-source-order": (
                    "IF ((source_a = 1 AND source_b = 1) AND source_c = 1)", "EXECUTE.",
                ),
                "nested-or-inequality-variable-operands-create": (
                    "COMPUTE ", "IF (", " OR ", " AND ", ">=", "<", "<=", "EXECUTE.",
                ),
            }[identifier]
            for token in required_tokens:
                require(token in source, f"{identifier}: bounded command coverage missing: {token}")
        else:
            require(identifier == "old-subset-retains-v0.1-plan", f"Unexpected 0.2 frontend case: {identifier}")
            require(set(case) == {"id", "request", "expected_plan_contract", "expected_plan_case_0_1", "expected_plan_hash", "expected_source_hash", "expected_error"}, f"{identifier}: 0.1 compatibility fields differ.")
            legacy_case = legacy_cases.get(case["expected_plan_case_0_1"])
            require(legacy_case is not None and "expected_plan" in legacy_case, f"{identifier}: immutable 0.1 plan fixture missing.")
            legacy_plan = legacy_case["expected_plan"]
            require(validate_plan_0_1(legacy_plan, identifier + ".0.1_plan") is None, f"{identifier}: immutable 0.1 plan is invalid.")
            require(case["expected_plan_contract"] == legacy_plan["contract"], f"{identifier}: 0.1 contract differs.")
            require(case["expected_plan_hash"] == legacy_case["expected_plan_hash"], f"{identifier}: 0.1 fixture hash differs.")
            require(case["expected_plan_hash"] == canonical_hash(legacy_plan), f"{identifier}: 0.1 canonical hash differs.")
    require(identifiers == {
        "compute-if-labels-format-level-execute-existing-target",
        "three-term-and-flattens-source-order",
        "parenthesized-three-term-and-flattens-source-order",
        "nested-or-inequality-variable-operands-create",
        "old-subset-retains-v0.1-plan",
        "reject-string-expression",
        "reject-missing-conditional-target",
        "reject-invalid-format",
    }, "0.2 frontend case set differs.")
    return len(identifiers)


def validate_in_place() -> None:
    manifest = json.loads(IN_PLACE.read_text(encoding="utf-8"))
    require(
        set(manifest) == {"manifest_version", "profile", "contract", "audit_schema", "cases"},
        "0.2 binding manifest fields differ.",
    )
    require(manifest["manifest_version"] == "0.2", "0.2 binding manifest version differs.")
    require(manifest["contract"] == "openstatspec-in-place-transformation-v0.2", "0.2 binding contract differs.")
    require(
        manifest["audit_schema"] == "../sql/transformation-plan-profile-schema.sql",
        "0.2 binding audit schema link differs.",
    )
    audit_schema_path = (IN_PLACE.parent / manifest["audit_schema"]).resolve()
    require(audit_schema_path == AUDIT_SCHEMA.resolve(), "0.2 binding audit schema path differs.")
    audit_schema = audit_schema_path.read_text(encoding="utf-8")
    require(
        "contract_id IN (" in audit_schema
        and "'openstatspec-in-place-transformation-v0.1'" in audit_schema
        and f"'{manifest['contract']}'" in audit_schema,
        "In-place audit schema does not accept both 0.1 and 0.2 contracts.",
    )
    case_list = manifest["cases"]
    require(isinstance(case_list, list), "0.2 binding cases must be an array.")
    cases = {require_string(case.get("id"), "0.2 binding case id"): case for case in case_list}
    require(len(cases) == len(case_list), "Duplicate 0.2 binding case id.")
    expected_ids = {
        "dolt-preprovisioned-target-sequential-null-semantics",
        "dolt-preprovisioned-target-or-null-semantics",
    } | {
        f"{profile}-create-target-fails-before-mutation"
        for profile in ("dolt", "mysql", "mariadb")
    }
    require(set(cases) == expected_ids, "0.2 binding case set differs.")

    success = cases["dolt-preprovisioned-target-sequential-null-semantics"]
    require(set(success) == {
        "id", "database_profile", "before", "after", "expected_audit",
        "forbidden_artifacts", "required_audit_fields", "expected_error",
    }, "0.2 binding success fields differ.")
    require(success["database_profile"] == "dolt" and success["expected_error"] is None, "Dolt success identity differs.")
    before, after = success["before"], success["after"]
    for field in (
        "dataset_id", "physical_table_schema", "physical_table_name",
        "dataset_count", "persistent_data_table_count", "case_count",
        "dolt_branch", "dolt_head",
    ):
        require(before[field] == after[field], f"Dolt success changes {field}.")
    require(before["case_count"] == len(before["rows"]) == len(after["rows"]) == 4, "Dolt case count differs.")
    before_ordinals = [row["__case_ordinal"] for row in before["rows"]]
    after_ordinals = [row["__case_ordinal"] for row in after["rows"]]
    require(before_ordinals == after_ordinals == [1, 2, 3, 4], "Dolt case order differs.")
    require(before["target_provisioning"] == {
        "physical_column": True,
        "catalog_variable": True,
        "dolt_commit": before["dolt_head"],
    }, "Dolt physical/catalog provisioning is not coupled to HEAD.")
    require(before["working_set_clean"] is True and after["working_set_clean"] is False, "Dolt working-set state differs.")
    require([row["target"] for row in after["rows"]] == [1, 0, 0, 0], "Three-valued IF result differs.")
    require(after["dolt_commit_performed"] is False, "Apply performs DOLT_COMMIT.")
    require(success["expected_audit"] == {
        "contract_id": manifest["contract"],
        "operation_count": 7,
        "dolt_branch": before["dolt_branch"],
        "dolt_head_before": before["dolt_head"],
        "dolt_head_after": after["dolt_head"],
    }, "Dolt expected audit identity differs.")
    require(set(success["forbidden_artifacts"]) == {
        "derived_dataset_row", "persistent_output_table", "full_table_copy",
        "staging_dataset", "staging_relation", "snapshot_table", "rollback_table",
        "dataset_version_row", "retirement_or_recovery_row", "temporary_object_residue",
    }, "Dolt forbidden-artifact proof differs.")
    require(set(success["required_audit_fields"]) == {
        "apply_id", "contract_id", "database_profile", "dataset_id",
        "physical_table_schema", "physical_table_name", "plan_hash", "source_hash",
        "actor", "status", "dolt_branch", "dolt_head_before", "dolt_head_after",
        "operation_count", "started_at", "completed_at",
    }, "Dolt required audit fields differ.")

    or_case = cases["dolt-preprovisioned-target-or-null-semantics"]
    require(set(or_case) == {
        "id", "database_profile", "target_preprovisioned", "condition",
        "before_rows", "after_rows", "expected_error",
    }, "Dolt OR-null case fields differ.")
    require(or_case["database_profile"] == "dolt" and or_case["target_preprovisioned"] is True, "Dolt OR-null identity differs.")
    require(or_case["condition"] == "source_a = 1 OR source_b = 1", "Dolt OR-null condition differs.")
    require(or_case["before_rows"] == [
        {"__case_ordinal": 1, "source_a": None, "source_b": 1, "target": 0},
        {"__case_ordinal": 2, "source_a": None, "source_b": 0, "target": 0},
    ], "Dolt OR-null inputs differ.")
    require(or_case["after_rows"] == [
        {"__case_ordinal": 1, "target": 1},
        {"__case_ordinal": 2, "target": 0},
    ], "Dolt OR three-valued outputs differ.")
    require(or_case["expected_error"] is None, "Dolt OR-null case unexpectedly fails.")

    for profile in ("dolt", "mysql", "mariadb"):
        case = cases[f"{profile}-create-target-fails-before-mutation"]
        require(set(case) == {"id", "database_profile", "target_mode", "expected_error", "mutation_started"}, f"{profile}: failure fields differ.")
        require(case["database_profile"] == profile and case["target_mode"] == "create", f"{profile}: failure identity differs.")
        require(case["expected_error"] == "schema_change_not_atomic" and case["mutation_started"] is False, f"{profile}: create-target gate differs.")


def validate_links() -> None:
    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    legacy_plan_schema = json.loads(PLAN_SCHEMA_0_1.read_text(encoding="utf-8"))
    frontend_schema = json.loads(FRONTEND_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(plan_schema)
    Draft202012Validator.check_schema(legacy_plan_schema)
    Draft202012Validator.check_schema(frontend_schema)
    plan_validator = Draft202012Validator(plan_schema)
    legacy_plan_validator = Draft202012Validator(legacy_plan_schema)
    frontend_validator = Draft202012Validator(frontend_schema)
    plan_manifest = json.loads(PLAN.read_text(encoding="utf-8"))
    legacy_plan_manifest = json.loads(PLAN_0_1.read_text(encoding="utf-8"))
    legacy_frontend_manifest = json.loads(FRONTEND_0_1.read_text(encoding="utf-8"))
    frontend_manifest = json.loads(FRONTEND.read_text(encoding="utf-8"))
    for case in plan_manifest["cases"]:
        plan_validator.validate(case["plan"])
    for case in legacy_plan_manifest["cases"]:
        legacy_plan_validator.validate(case["plan"])
    for case in legacy_frontend_manifest["cases"]:
        if "expected_plan" in case:
            legacy_plan_validator.validate(case["expected_plan"])
    for case in frontend_manifest["cases"]:
        frontend_validator.validate(case["request"])
    require(plan_schema["$id"].endswith("transformation-plan-0.2.schema.json"), "0.2 plan schema ID differs.")
    require(frontend_schema["$id"].endswith("spss-syntax-frontend-0.2.schema.json"), "0.2 frontend schema ID differs.")
    binding = (ROOT / "docs/transformation-plan-sql-binding-0.2.md").read_text(encoding="utf-8")
    require(legacy_plan_schema["$id"].endswith("transformation-plan-0.1.schema.json"), "0.1 plan schema ID differs.")
    binding_normalized = " ".join(binding.split())
    require("MySQL, MariaDB, and Dolt MUST reject" in binding_normalized, "Non-atomic profile gate missing.")
    require("separate, explicit, versioned provisioning action" in binding_normalized, "Provisioning contract missing.")
    require("MUST NOT commit, switch, merge, reset" in binding_normalized, "Dolt no-commit contract missing.")


def validate_all() -> tuple[int, int]:
    plan_cases = validate_plan_manifest()
    frontend_count = validate_frontend(plan_cases)
    validate_in_place()
    validate_links()
    return len(plan_cases), frontend_count


def main() -> None:
    plan_count, frontend_count = validate_all()
    print(f"Validated {plan_count} Transformation Plan 0.2 and {frontend_count} SPSS frontend 0.2 cases.")


if __name__ == "__main__":
    main()
