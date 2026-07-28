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
    for table in (
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

    for path in (
        ROOT / "sql/dialect-profile-baseline.json",
        MANIFEST,
    ):
        json.loads(path.read_text(encoding="utf-8"))

    print(f"Validated {len(identifiers) - 1} binary fixtures and one generated preflight fixture.")


if __name__ == "__main__":
    main()
