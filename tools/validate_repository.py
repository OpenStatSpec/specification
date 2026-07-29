"""Validate the self-contained OpenStatSpec specification release inputs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conformance/spss-sav-zsav-1.0.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


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
        == {"minimum_inclusive": "2.2.2", "maximum_inclusive": "2.2.2"},
        "Dolt claimed version range is unexpected.",
    )
    require(dolt["exact_ci_tested_versions"] == ["2.2.2"], "Dolt exact CI-tested versions are unexpected.")
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

    validate_dialect_baseline()
    json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"Validated {len(identifiers) - 1} binary fixtures and one generated preflight fixture.")


if __name__ == "__main__":
    main()
