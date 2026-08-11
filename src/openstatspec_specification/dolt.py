"""Validate the self-contained OpenStatSpec specification release inputs."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import struct
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "conformance/spss-sav-zsav-1.0.json"


class DoltDeclarationError(ValueError):
    """A semantic or resource-integrity failure in a Dolt declaration set."""

    def __init__(self, message: str, *, code: str = "invalid_dolt_declaration") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DoltDeclarationSource:
    """A directory or installed-package root containing authoritative SQL resources."""

    root: Traversable
    filesystem_root: Path | None = None

    @classmethod
    def packaged(cls) -> "DoltDeclarationSource":
        root = resources.files("openstatspec_specification")
        return cls(root=root, filesystem_root=root if isinstance(root, Path) else None)

    @classmethod
    def from_directory(cls, root: str | Path) -> "DoltDeclarationSource":
        path = Path(root)
        if not path.exists() or not path.is_dir():
            raise DoltDeclarationError(
                "Dolt declaration source directory does not exist: " + str(path),
                code="source_directory_missing",
            )
        if path.is_symlink():
            raise DoltDeclarationError(
                "Dolt declaration source root must not be a symlink.",
                code="source_root_symlink",
            )
        resolved = path.resolve()
        return cls(root=resolved, filesystem_root=resolved)

    @staticmethod
    def _parts(relative_path: str) -> tuple[str, ...]:
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or "\\" in relative_path
            or relative_path.startswith("/")
        ):
            raise DoltDeclarationError(
                "Resource path is not canonical and relative: " + repr(relative_path),
                code="invalid_resource_path",
            )
        parts = tuple(relative_path.split("/"))
        if any(part in {"", ".", ".."} for part in parts):
            raise DoltDeclarationError(
                "Resource path is not canonical and relative: " + repr(relative_path),
                code="invalid_resource_path",
            )
        return parts

    def resource(self, relative_path: str) -> Traversable:
        parts = self._parts(relative_path)
        current: Traversable = self.root
        if self.filesystem_root is not None:
            candidate = self.filesystem_root
            for part in parts:
                candidate = candidate / part
                if candidate.is_symlink():
                    raise DoltDeclarationError(
                        "Resource path traverses a symlink: " + relative_path,
                        code="resource_symlink",
                    )
            try:
                candidate.resolve().relative_to(self.filesystem_root.resolve())
            except ValueError as error:
                raise DoltDeclarationError(
                    "Resource path escapes its source root: " + relative_path,
                    code="resource_path_escape",
                ) from error
        for part in parts:
            current = current.joinpath(part)
        return current

    @staticmethod
    def _resource_io_error(operation: str, error: OSError) -> DoltDeclarationError:
        return DoltDeclarationError(
            "Dolt declaration resource I/O failed during "
            + operation
            + " ("
            + type(error).__name__
            + ").",
            code="resource_io_error",
        )

    def is_directory(self, relative_path: str) -> bool:
        resource = self.resource(relative_path)
        try:
            return resource.is_dir()
        except OSError as error:
            raise self._resource_io_error("directory inspection", error) from None

    def read_bytes(self, relative_path: str) -> bytes:
        resource = self.resource(relative_path)
        try:
            is_file = resource.is_file()
        except OSError as error:
            raise self._resource_io_error("file inspection", error) from None
        if not is_file:
            raise DoltDeclarationError(
                "Required Dolt declaration resource is missing: " + relative_path,
                code="resource_missing",
            )
        try:
            return resource.read_bytes()
        except OSError as error:
            raise self._resource_io_error("file read", error) from None

    def read_json(self, relative_path: str) -> Any:
        try:
            return json.loads(self.read_bytes(relative_path).decode("utf-8"))
        except UnicodeDecodeError as error:
            raise DoltDeclarationError(
                "Dolt declaration resource is not UTF-8: " + relative_path,
                code="resource_not_utf8",
            ) from error
        except json.JSONDecodeError as error:
            raise DoltDeclarationError(
                "Dolt declaration resource is not valid JSON: " + relative_path,
                code="resource_invalid_json",
            ) from error

    def declaration_resources(self) -> tuple[Traversable, ...]:
        directory = self.resource("sql/dolt-adapter-declarations")
        try:
            is_directory = directory.is_dir()
        except OSError as error:
            raise self._resource_io_error("directory inspection", error) from None
        if not is_directory:
            raise DoltDeclarationError(
                "Dolt adapter declaration directory is missing.",
                code="declaration_directory_missing",
            )
        try:
            declarations = tuple(
                sorted(
                    (
                        entry
                        for entry in directory.iterdir()
                        if entry.name.endswith(".json")
                    ),
                    key=lambda entry: entry.name,
                )
            )
        except OSError as error:
            raise self._resource_io_error("directory listing", error) from None
        for entry in declarations:
            try:
                is_file = entry.is_file()
            except OSError as error:
                raise self._resource_io_error(
                    "declaration file inspection", error,
                ) from None
            if not is_file:
                raise DoltDeclarationError(
                    "A Dolt declaration JSON resource is not a regular file.",
                    code="declaration_not_file",
                )
            if isinstance(entry, Path) and entry.is_symlink():
                raise DoltDeclarationError(
                    "A Dolt declaration JSON resource must not be a symlink.",
                    code="declaration_symlink",
                )
        return declarations


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DoltDeclarationError(message)


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
    if profile == "dolt":
        require(value["value"] is None, f"{context}.value must remain unestablished in the generic profile.")
        require(value["unit"] is None, f"{context}.unit must remain unestablished in the generic profile.")
    else:
        require(isinstance(value["value"], int) and value["value"] > 0, f"{context}.value must be positive.")
        require(value["unit"] in {"bytes", "characters"}, f"{context}.unit must be bytes or characters.")
    require_string(value["source"], context + ".source")
    require_string(value["repertoire"], context + ".repertoire")


def verify_evidence_artifact(
    source: DoltDeclarationSource,
    *,
    artifact_ref: str,
    artifact_sha256: str,
    context: str = "Dolt evidence artifact",
) -> bytes:
    """Read one canonical evidence artifact and verify its lowercase SHA-256."""

    artifact_parts = artifact_ref.split("/")
    require(
        "\\" not in artifact_ref
        and not artifact_ref.startswith("/")
        and all(part not in {"", ".", ".."} for part in artifact_parts),
        context + ".artifact_ref must be a canonical repository-relative path.",
    )
    evidence_root = ("sql", "dolt-adapter-declarations", "evidence")
    require(
        tuple(artifact_parts[:3]) == evidence_root and len(artifact_parts) > 3,
        context + ".artifact_ref must be under "
        + "/".join(evidence_root)
        + "/.",
    )
    require(
        re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is not None,
        context + ".artifact_sha256 must be lowercase SHA-256.",
    )
    artifact_bytes = source.read_bytes(artifact_ref)
    require(
        hashlib.sha256(artifact_bytes).hexdigest() == artifact_sha256,
        context + ".artifact_sha256 does not match the artifact.",
    )
    return artifact_bytes


def validate_dolt_declaration(
    dolt: object,
    context: str,
    *,
    source: DoltDeclarationSource | None = None,
) -> Mapping[str, Any]:
    require(isinstance(dolt, dict), f"{context} must be an object.")
    declaration_source = source or DoltDeclarationSource.packaged()
    require(
        set(dolt) == {
            "declaration_schema_id",
            "declaration_kind",
            "declaration_id",
            "adapter_implementation_id",
            "adapter_version",
            "specification_commit",
            "conformance_run_id",
            "conformance_status",
            "import_enabled",
            "claimed_product_versions",
            "tested_product_versions",
            "active_product_version",
            "active_product_version_evidence_id",
            "evidence_records",
            "version_declaration_contract",
            "concrete_adapter_declaration_contract",
            "wire_protocol",
            "inherited_mysql_innodb_limits_forbidden",
            "maximum_columns_default",
            "maximum_columns_default_source",
            "identifier_quoting",
            "identifier_limit",
            "catalog_namespace_modes",
            "numeric_type",
            "string_type",
            "case_ordinal_type",
            "product_identity",
            "catalog_mutation_boundary",
            "transactional_ddl",
            "ddl_atomicity_case",
            "repository_commit_is_sql_atomicity_boundary",
            "version_control_mutations",
            "failure_cleanup_required_unless_atomicity_proven",
            "cleanup_failure",
            "limit_bases",
            "limit_declarations",
            "column_limit_relationship",
            "effective_limit_rule",
            "dataset_total_is_emitted_statement_limit",
            "boundary_conformance",
        },
        "Dolt top-level profile fields are incomplete.",
    )

    require(dolt["declaration_schema_id"] == "openstatspec-dolt-adapter-declaration-v1", "Unexpected Dolt declaration schema.")
    declaration_kind = dolt["declaration_kind"]
    require(isinstance(declaration_kind, str), "Dolt declaration kind must be a string.")
    require(declaration_kind in {"symbolic_template", "concrete_adapter"}, "Unexpected Dolt declaration kind.")
    exact_version_pattern = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
    adapter_version_pattern = re.compile(
        r"^[0-9]+\.[0-9]+\.[0-9]+"
        r"(?:(?:a|b|rc)[0-9]+|\.post[0-9]+|\.dev[0-9]+)?"
        r"(?:\+[0-9A-Za-z.-]+)?$"
    )
    canonical_id_pattern = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
    specification_commit_pattern = re.compile(r"^[0-9a-f]{40}$")
    binding_fields = (
        "declaration_id",
        "adapter_implementation_id",
        "adapter_version",
        "specification_commit",
        "conformance_run_id",
    )

    if declaration_kind == "symbolic_template":
        require(
            all(dolt[field] is None for field in binding_fields),
            "The symbolic Dolt template must not claim concrete adapter bindings.",
        )
    else:
        for field in ("declaration_id", "adapter_implementation_id", "conformance_run_id"):
            value = require_string(dolt[field], "Dolt " + field)
            require(
                value == value.strip() and canonical_id_pattern.fullmatch(value) is not None,
                "Dolt " + field + " is not canonical.",
            )
            require(
                not value.casefold().startswith(("template", "placeholder", "pending")),
                "Dolt " + field + " retains a template placeholder.",
            )
        adapter_version = require_string(dolt["adapter_version"], "Dolt adapter_version")
        require(
            adapter_version == adapter_version.strip()
            and adapter_version_pattern.fullmatch(adapter_version) is not None,
            "Dolt adapter_version must be an exact canonical adapter release.",
        )
        specification_commit = require_string(
            dolt["specification_commit"], "Dolt specification_commit",
        )
        require(
            specification_commit_pattern.fullmatch(specification_commit) is not None,
            "Dolt specification_commit must be an exact lowercase 40-hex commit.",
        )

    def validate_exact_versions(value: object, context: str, require_nonempty: bool) -> list[str]:
        require(isinstance(value, list), f"{context} must be an array.")
        require(not require_nonempty or bool(value), f"{context} must be non-empty.")
        require(all(isinstance(version, str) and bool(version) for version in value), f"{context} entries must be strings.")
        require(len(value) == len(set(value)), f"{context} entries must be unique.")
        for version in value:
            require(version == version.strip(), f"{context} entries must be trim-identical.")
            require(exact_version_pattern.fullmatch(version) is not None, f"{context} entry is not a canonical exact product version.")
        return value

    concrete_declaration = declaration_kind == "concrete_adapter"
    claimed_versions = validate_exact_versions(
        dolt["claimed_product_versions"],
        "Dolt claimed_product_versions",
        concrete_declaration,
    )
    tested_versions = validate_exact_versions(
        dolt["tested_product_versions"],
        "Dolt tested_product_versions",
        concrete_declaration,
    )
    require(set(tested_versions) <= set(claimed_versions), "Dolt tested product versions must be a subset of claimed versions.")
    def is_template_placeholder(value: object) -> bool:
        return isinstance(value, str) and (
            value.casefold() in {"template", "placeholder", "pending"}
            or value.casefold().startswith(("template_", "placeholder_", "pending_"))
        )

    evidence_records = dolt["evidence_records"]
    require(isinstance(evidence_records, list), "Dolt evidence_records must be an array.")
    evidence_by_id: dict[str, dict[str, object]] = {}
    evidence_id_pattern = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
    evidence_artifact_root = "sql/dolt-adapter-declarations/evidence"
    if concrete_declaration:
        require(
            declaration_source.is_directory(evidence_artifact_root),
            "Dolt evidence artifact root is missing.",
        )
    for index, evidence_record in enumerate(evidence_records):
        evidence_context = f"Dolt evidence_records[{index}]"
        require(isinstance(evidence_record, dict), f"{evidence_context} must be an object.")
        require(
            set(evidence_record) == {"evidence_id", "kind", "exact_versions", "artifact_ref", "artifact_sha256", "measurement", "observed"},
            f"{evidence_context} fields are incomplete.",
        )
        evidence_id = require_string(evidence_record["evidence_id"], evidence_context + ".evidence_id")
        require(evidence_id_pattern.fullmatch(evidence_id) is not None, f"{evidence_context}.evidence_id is not canonical.")
        require(evidence_id not in evidence_by_id, f"{evidence_context}.evidence_id is duplicated.")
        if concrete_declaration:
            require(not is_template_placeholder(evidence_id), f"{evidence_context}.evidence_id retains a template placeholder.")
        require(isinstance(evidence_record["kind"], str), f"{evidence_context}.kind must be a string.")
        require(
            evidence_record["kind"] in {"product_identity", "limit", "boundary", "fault", "ddl_atomicity", "structural"},
            f"{evidence_context}.kind is invalid.",
        )
        evidence_versions = validate_exact_versions(evidence_record["exact_versions"], evidence_context + ".exact_versions", True)
        require(set(evidence_versions) <= set(tested_versions), f"{evidence_context}.exact_versions must be tested.")
        artifact_ref = require_string(evidence_record["artifact_ref"], evidence_context + ".artifact_ref")
        artifact_sha256 = require_string(evidence_record["artifact_sha256"], evidence_context + ".artifact_sha256")
        require_string(evidence_record["measurement"], evidence_context + ".measurement")
        require(evidence_record["observed"] is not None, f"{evidence_context}.observed is required.")
        if concrete_declaration:
            require(not is_template_placeholder(artifact_ref), f"{evidence_context}.artifact_ref retains a template placeholder.")
            require(not is_template_placeholder(evidence_record["measurement"]), f"{evidence_context}.measurement retains a template placeholder.")
            require(not is_template_placeholder(evidence_record["observed"]), f"{evidence_context}.observed retains a template placeholder.")
            verify_evidence_artifact(
                declaration_source,
                artifact_ref=artifact_ref,
                artifact_sha256=artifact_sha256,
                context=evidence_context,
            )
        evidence_by_id[evidence_id] = evidence_record

    active_product_version = dolt["active_product_version"]
    active_product_version_evidence_id = dolt["active_product_version_evidence_id"]
    if declaration_kind == "symbolic_template":
        require(dolt["conformance_status"] == "pending", "The symbolic Dolt template must remain pending.")
        require(dolt["import_enabled"] is False, "The symbolic Dolt template must not enable import.")
        require(claimed_versions == [] and tested_versions == [], "The pending Dolt template must not claim or test versions.")
        require(active_product_version is None and active_product_version_evidence_id is None, "The pending Dolt template must not claim an active product version.")
        require(evidence_records == [], "The pending Dolt template must not claim live evidence.")
    else:
        require(dolt["conformance_status"] == "tested", "A concrete Dolt adapter declaration must be tested.")
        require(dolt["import_enabled"] is True, "A concrete tested Dolt adapter declaration must enable import.")
        require(bool(claimed_versions), "A concrete Dolt adapter declaration must claim exact versions.")
        require(bool(tested_versions), "A concrete Dolt adapter declaration must name tested exact versions.")
        require(bool(evidence_records), "A concrete Dolt adapter declaration must publish evidence records.")
        active_versions = validate_exact_versions([active_product_version], "Dolt active_product_version", True)
        require(active_versions[0] in tested_versions, "The active Dolt product version must be tested before import.")
        require_string(active_product_version_evidence_id, "Dolt active_product_version_evidence_id")
        require(active_product_version_evidence_id in evidence_by_id, "Dolt active product-version evidence does not resolve.")
        active_evidence = evidence_by_id[active_product_version_evidence_id]
        require(active_evidence["kind"] == "product_identity", "Dolt active product-version evidence kind is invalid.")
        require(active_product_version in active_evidence["exact_versions"], "Dolt active product-version evidence does not cover the active version.")
        require(active_evidence["measurement"] == "DOLT_VERSION()", "Dolt active product-version evidence measurement is invalid.")
        require(active_evidence["observed"] == active_product_version, "Dolt active product-version evidence does not record the active version.")

    require(
        dolt["version_declaration_contract"] == {
            "concrete_claimed_versions": "nonempty_unique_canonical_exact_product_versions",
            "concrete_tested_versions": "nonempty_unique_canonical_exact_subset_of_claimed",
            "canonical_exact_product_version_pattern": r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$",
            "trim_identical_required": True,
            "active_product_version_source": "DOLT_VERSION()",
            "active_product_version_membership": "tested_product_versions_with_applicable_evidence",
            "claimed_but_untested_failure": "reject_before_mutation",
            "membership_failure": "reject_before_mutation",
            "placeholder_versions_forbidden": True,
        },
        "Dolt version-declaration contract is incomplete.",
    )
    require(
        dolt["concrete_adapter_declaration_contract"] == {
            "declaration_kind": "concrete_adapter",
            "conformance_status": "tested",
            "import_enabled": True,
            "applicable_layer_exact_versions": "nonempty_canonical_exact_subset_of_tested_product_versions",
            "non_structural_limit_values": "positive_integers",
            "effective_limit": "numeric_minimum_of_applicable_non_effective_layers",
            "per_basis_column_relationship": "physical_columns_equals_source_variables_plus_one",
            "structural_row_value": "positive_integer_or_structured_not_applicable_proof",
            "structural_row_discriminator": "kind",
            "boundary_case_evidence": "nonnull_measured_value_observed_equals_expected_nonempty_evidence_id_and_nonempty_canonical_exact_versions_subset_of_tested",
        },
        "Dolt concrete-adapter declaration contract is incomplete.",
    )

    require(dolt["wire_protocol"] == "mysql", "Dolt must declare the MySQL wire protocol.")
    require(
        dolt["inherited_mysql_innodb_limits_forbidden"] is True,
        "Dolt must forbid inherited MySQL/InnoDB limits.",
    )
    require(dolt["maximum_columns_default"] is None, "Dolt must not inherit a generic column default.")
    require_string(dolt["maximum_columns_default_source"], "Dolt maximum_columns_default_source")
    require(dolt["identifier_quoting"] == "backtick", "Unexpected Dolt identifier quoting.")
    identifier_limit = dolt["identifier_limit"]
    require(isinstance(identifier_limit, dict), "Dolt identifier_limit must be an object.")
    require(set(identifier_limit) == {"value", "unit", "source", "repertoire"}, "Dolt identifier_limit fields are incomplete.")
    require_string(identifier_limit["source"], "Dolt identifier_limit.source")
    require_string(identifier_limit["repertoire"], "Dolt identifier_limit.repertoire")
    if declaration_kind == "symbolic_template":
        require(identifier_limit["value"] is None and identifier_limit["unit"] is None, "The symbolic Dolt identifier limit must remain pending.")
    else:
        require(isinstance(identifier_limit["value"], int) and not isinstance(identifier_limit["value"], bool) and identifier_limit["value"] > 0, "Dolt concrete identifier_limit.value must be a positive integer.")
        require(identifier_limit["unit"] in {"bytes", "characters"}, "Dolt concrete identifier_limit.unit is not canonical.")
        require(all(token not in identifier_limit[field].casefold() for field in ("source", "repertoire") for token in ("template", "unestablished", "adapter declaration required")), "Dolt concrete identifier_limit retains template text.")
    require(dolt["catalog_namespace_modes"] == ["database"], "Unexpected Dolt catalog namespace mode.")
    require(dolt["numeric_type"] == "DOUBLE", "Unexpected Dolt numeric type.")
    require(dolt["string_type"] == "LONGTEXT NOT NULL", "Unexpected Dolt string type.")
    require(dolt["case_ordinal_type"] == "BIGINT NOT NULL PRIMARY KEY", "Unexpected Dolt case ordinal type.")
    require(dolt["transactional_ddl"] == "exact_product_version_evidence_required", "Unexpected Dolt DDL declaration.")
    require(dolt["repository_commit_is_sql_atomicity_boundary"] is False, "Dolt commit must not be SQL atomicity.")
    require(
        dolt["version_control_mutations"] == "forbidden_without_separate_namespaced_extension",
        "Dolt version-control mutations require a separate namespaced extension.",
    )
    require(dolt["failure_cleanup_required_unless_atomicity_proven"] is True, "Dolt cleanup guard is missing.")

    require(
        dolt["product_identity"] == {
            "version_comment_variable": "@@version_comment",
            "version_comment_comparison": "trim_casefold_exact",
            "version_comment_expected": "Dolt",
            "product_version_function": "DOLT_VERSION()",
            "product_version_must_be_nonempty": True,
            "active_product_version_must_match": "tested_product_versions_with_applicable_evidence",
            "claimed_but_untested_failure": "reject_before_mutation",
            "raw_wire_version_variable": "@@version",
            "raw_wire_version_recorded_separately": True,
            "raw_wire_version_is_product_version": False,
            "failure_mode": "reject_before_mutation",
        },
        "Dolt positive identity, active-version membership, and failure mode are incomplete.",
    )

    zero_mutation_state = {"mutations": "zero", "diagnostic_persistence": "out_of_band_only"}
    catalog_boundary = dolt["catalog_mutation_boundary"]
    require(
        catalog_boundary == {
            "catalog_install_migrate": "separate_operations",
            "import_catalog_state": "verified",
            "unverified_catalog_states": {
                "absent": zero_mutation_state,
                "foreign": zero_mutation_state,
                "ambiguous": zero_mutation_state,
            },
            "verified_preflight_failure": {
                "persistence_required": True,
                "diagnostic_persistence": "verified_catalog",
                "permitted_mutations": [
                    "failed_operation",
                    "target_capability_exceeded_fidelity_event",
                ],
                "fidelity_event_dataset_id": None,
                "dataset_row": "forbidden",
                "physical_data_table": "forbidden",
            },
            "cleanup_failure_reverification": {
                "required": True,
                "verified": {
                    "operation_status": "failed",
                    "diagnostic_persistence": "verified_catalog",
                    "fidelity_event_code": "cleanup_failed",
                    "fidelity_event_severity": "error",
                    "permitted_mutations": ["failed_operation", "cleanup_failed_fidelity_event"],
                },
                "unverified_or_ambiguous": {
                    "diagnostic_persistence": "out_of_band_only",
                    "further_mutations": "zero",
                },
            },
            "post_failure_verification": [
                "catalog_relations",
                "physical_data_table",
                "residual_objects",
                "dolt_status_diff",
                "branch",
                "commit_head",
            ],
        },
        "Dolt catalog mutation boundary is incomplete.",
    )

    cleanup_failure = dolt["cleanup_failure"]
    require(
        cleanup_failure == {
            "operation_status": "failed",
            "success_status_forbidden": True,
            "diagnostic_code": "cleanup_failed",
            "catalog_reverification_required_before_persistence": True,
            "verified_catalog_persistence": "fidelity_event",
            "unverified_catalog_persistence": "out_of_band_only",
            "detail_json_required_fields": [
                "original_cause",
                "cleanup_fault",
                "residual_object_inventory",
                "deterministic_recovery_evidence",
            ],
            "cleanup_fault_injection_required": True,
        },
        "Dolt cleanup-failure audit contract is incomplete.",
    )
    cleanup_reverification = catalog_boundary["cleanup_failure_reverification"]
    require(
        cleanup_reverification["required"] == cleanup_failure["catalog_reverification_required_before_persistence"],
        "Dolt cleanup-failure catalog reverification is inconsistent.",
    )
    require(
        cleanup_reverification["verified"]["operation_status"] == cleanup_failure["operation_status"]
        and cleanup_reverification["verified"]["fidelity_event_code"] == cleanup_failure["diagnostic_code"]
        and cleanup_reverification["verified"]["diagnostic_persistence"] == "verified_catalog",
        "Dolt cleanup failure is inconsistent with the reverified-catalog audit path.",
    )
    require(
        cleanup_reverification["unverified_or_ambiguous"] == {
            "diagnostic_persistence": "out_of_band_only",
            "further_mutations": "zero",
        }
        and cleanup_failure["unverified_catalog_persistence"] == cleanup_reverification["unverified_or_ambiguous"]["diagnostic_persistence"],
        "Dolt cleanup failure must stop mutation when catalog reverification fails.",
    )

    expected_bases = [
        "theoretical_engine",
        "live_observed_server",
        "active_configuration",
        "adapter_policy",
        "adapter_envelope",
        "effective",
    ]
    require(dolt["limit_bases"] == expected_bases, "Unexpected Dolt limit bases.")
    limits = dolt["limit_declarations"]
    template_symbols = {
        "physical_columns": "N_plus_1",
        "source_variables": "N",
        "identifier": "L",
        "value": "V",
        "structural_row": "R",
        "emitted_statement": "S",
    }
    require(isinstance(limits, dict) and set(limits) == set(template_symbols), "Dolt limit dimensions are incomplete.")
    record_fields = {"value", "unit", "scope", "basis", "evidence", "exact_versions", "applicable"}
    records_by_dimension: dict[str, dict[str, dict[str, object]]] = {}

    for name, records in limits.items():
        require(isinstance(records, list) and len(records) == len(expected_bases), f"Dolt {name} layers are incomplete.")
        require(all(isinstance(record, dict) for record in records), f"Dolt {name} layers must be objects.")
        for index, record in enumerate(records):
            require(set(record) == record_fields, f"Dolt {name}[{index}] record fields are incomplete.")
        require([record["basis"] for record in records] == expected_bases, f"Dolt {name} bases are out of order.")
        for record in records:
            require_string(record["unit"], f"Dolt {name}.unit")
            require_string(record["scope"], f"Dolt {name}.scope")
            require_string_list(record["evidence"], f"Dolt {name}.evidence")
            require(isinstance(record["applicable"], bool), f"Dolt {name}.applicable must be boolean.")
            exact_versions = validate_exact_versions(
                record["exact_versions"],
                f"Dolt {name}.{record['basis']}.exact_versions",
                concrete_declaration and record["applicable"],
            )
            if concrete_declaration:
                allowed_units = {
                    "physical_columns": {"columns"},
                    "source_variables": {"variables"},
                    "identifier": {"bytes", "characters"},
                    "value": {"bytes", "characters"},
                    "structural_row": {"bytes", "characters", "not_applicable"},
                    "emitted_statement": {"bytes"},
                }
                require(record["unit"] in allowed_units[name], f"Dolt concrete {name}.{record['basis']}.unit is not canonical.")
                require(all(not is_template_placeholder(evidence_id) for evidence_id in record["evidence"]), f"Dolt concrete {name}.{record['basis']} retains template evidence.")
                require(all(evidence_id in evidence_by_id for evidence_id in record["evidence"]), f"Dolt concrete {name}.{record['basis']} evidence does not resolve.")
                require(all(evidence_by_id[evidence_id]["kind"] == "limit" for evidence_id in record["evidence"]), f"Dolt concrete {name}.{record['basis']} evidence kind is invalid.")
                if record["applicable"]:
                    require(active_product_version in exact_versions, f"Dolt concrete {name}.{record['basis']} does not cover the active version.")
                    matching_evidence = [
                        evidence_by_id[evidence_id]
                        for evidence_id in record["evidence"]
                        if evidence_by_id[evidence_id]["measurement"] == f"{name}.{record['basis']}"
                        and evidence_by_id[evidence_id]["observed"] == record["value"]
                    ]
                    require(bool(matching_evidence), f"Dolt concrete {name}.{record['basis']} value is not linked to evidence.")
                    measured_versions = set().union(*(set(item["exact_versions"]) for item in matching_evidence))
                    require(set(exact_versions) <= measured_versions, f"Dolt concrete {name}.{record['basis']} measured value lacks per-version evidence coverage.")
            if not record["applicable"]:
                require(record["value"] is None, f"Dolt {name} non-applicable value must be null.")
                require(exact_versions == [], f"Dolt {name} non-applicable exact_versions must be empty.")
            elif declaration_kind == "symbolic_template":
                require(record["value"] == template_symbols[name], f"Dolt {name} uses an unknown template symbol.")
                require(exact_versions == [], f"Dolt {name} pending template must not claim version evidence.")
            else:
                require(bool(exact_versions), f"Dolt {name} applicable concrete layer needs exact versions.")
                require(set(exact_versions) <= set(tested_versions), f"Dolt {name} layer versions must be tested.")
                if name == "structural_row":
                    structural_value = record["value"]
                    if isinstance(structural_value, dict):
                        require(
                            set(structural_value) == {"kind", "reason", "inspected_structures"},
                            f"Dolt {name} not-applicable proof fields are incomplete.",
                        )
                        require(structural_value["kind"] == "not_applicable_proof", f"Dolt {name} proof kind is invalid.")
                        require_string(structural_value["reason"], f"Dolt {name}.reason")
                        require_string_list(structural_value["inspected_structures"], f"Dolt {name}.inspected_structures")
                    else:
                        require(isinstance(structural_value, int) and not isinstance(structural_value, bool) and structural_value > 0, f"Dolt {name} limit must be a positive integer.")
                else:
                    require(isinstance(record["value"], int) and not isinstance(record["value"], bool) and record["value"] > 0, f"Dolt {name} limit must be a positive integer.")
        by_basis = {record["basis"]: record for record in records}
        records_by_dimension[name] = by_basis
        require(by_basis["adapter_policy"]["applicable"], f"Dolt {name} adapter-policy layer must be applicable.")
        require(by_basis["effective"]["applicable"], f"Dolt {name} effective layer must be applicable.")
        if declaration_kind == "symbolic_template":
            require(
                by_basis["effective"]["value"] == template_symbols[name],
                f"Dolt {name} template effective symbol is inconsistent.",
            )
        else:
            applicable_values = [
                record["value"]
                for record in records
                if record["applicable"] and record["basis"] != "effective"
            ]
            if name == "structural_row" and all(isinstance(value, dict) for value in applicable_values):
                require(
                    isinstance(by_basis["effective"]["value"], dict),
                    "Dolt structural-row effective proof must remain structured.",
                )
            else:
                require(
                    all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in applicable_values),
                    f"Dolt {name} concrete applicable values must be positive integers.",
                )
                applicable_units = {
                    record["unit"]
                    for record in records
                    if record["applicable"] and record["basis"] != "effective"
                }
                require(
                    len(applicable_units) == 1,
                    f"Dolt {name} applicable limit layers must use one common unit.",
                )
                common_unit = next(iter(applicable_units))
                require(
                    by_basis["effective"]["unit"] == common_unit,
                    f"Dolt {name} effective limit unit must match applicable layers.",
                )
                require(
                    by_basis["effective"]["value"] == min(applicable_values),
                    f"Dolt {name} effective value is not the numeric minimum.",
                )

    require(
        dolt["column_limit_relationship"] == "each_applicable_basis_physical_columns_equals_source_variables_plus_one",
        "Dolt column-limit relationship is missing.",
    )
    for basis in expected_bases:
        physical = records_by_dimension["physical_columns"][basis]
        source = records_by_dimension["source_variables"][basis]
        if declaration_kind == "concrete_adapter":
            require(
                physical["applicable"] and source["applicable"],
                f"Dolt concrete {basis} source/physical layers must both be applicable.",
            )
        require(physical["applicable"] == source["applicable"], f"Dolt {basis} column-layer applicability differs.")
        if not physical["applicable"]:
            continue
        if declaration_kind == "symbolic_template":
            require(
                physical["value"] == "N_plus_1" and source["value"] == "N",
                f"Dolt {basis} symbolic source/physical relationship is inconsistent.",
            )
        else:
            require(
                physical["value"] == source["value"] + 1,
                f"Dolt {basis} physical-column limit must equal source-variable limit plus one.",
            )
    if declaration_kind == "concrete_adapter":
        effective_identifier = records_by_dimension["identifier"]["effective"]
        require(identifier_limit["value"] == effective_identifier["value"], "Dolt identifier_limit.value differs from effective L.")
        require(identifier_limit["unit"] == effective_identifier["unit"], "Dolt identifier_limit.unit differs from effective L unit.")

    require(
        dolt["effective_limit_rule"] == "concrete_numeric_minimum_of_all_applicable_non_effective_layers",
        "Unexpected Dolt effective-limit rule.",
    )
    require(dolt["dataset_total_is_emitted_statement_limit"] is False, "Dataset total must not be a statement limit.")

    boundary = dolt["boundary_conformance"]
    require(isinstance(boundary, dict), "Dolt boundary-conformance declaration must be an object.")
    require(
        set(boundary) == {
            "status",
            "case_evidence_contract",
            "identifier_cases",
            "column_cases",
            "longtext_cases",
            "double_cases",
            "double_exceptional_cases",
            "system_missing_collision_policy",
            "structural_row_cases",
            "statement_cases",
            "fault_conformance",
        },
        "Dolt boundary-conformance fields are incomplete.",
    )
    require(
        boundary["status"] == ("pending_template" if declaration_kind == "symbolic_template" else "tested"),
        "Dolt boundary-conformance status does not match declaration kind.",
    )
    require(
        boundary["case_evidence_contract"] == {
            "template_measured_value": None,
            "template_observed": None,
            "template_evidence_id": None,
            "template_exact_versions": [],
            "concrete_measured_value": "required_nonnull_machine_readable_value",
            "concrete_observed": "required_machine_readable_value_equal_to_expected",
            "concrete_evidence_id": "required_nonempty_string",
            "concrete_exact_versions": "nonempty_canonical_exact_subset_of_tested_product_versions",
        },
        "Dolt case-evidence contract is incomplete.",
    )

    def validate_boundary_cases(
        case_group: object,
        expected_cases: dict[str, tuple[str, str, str]],
        context: str,
        extra_fields: set[str] | None = None,
        evidence_kind: str = "boundary",
    ) -> None:
        require(isinstance(case_group, list), f"{context} must be an array.")
        require(all(isinstance(case, dict) for case in case_group), f"{context} entries must be objects.")
        for index, case in enumerate(case_group):
            require(
                set(case) == {"id", "measurement", "unit", "measured_value", "expected", "observed", "evidence_id", "exact_versions"} | (extra_fields or set()),
                f"{context}[{index}] fields are incomplete.",
            )
        case_ids = [case["id"] for case in case_group]
        require(all(isinstance(case_id, str) and case_id for case_id in case_ids), f"{context} case IDs must be strings.")
        require(len(case_ids) == len(set(case_ids)), f"{context} case IDs must be unique.")
        require(set(case_ids) == set(expected_cases), f"{context} case IDs are incomplete.")
        for case in case_group:
            expected_measurement, expected_unit, expected_result = expected_cases[case["id"]]
            if concrete_declaration:
                expected_unit = {
                    "declared_identifier_unit": records_by_dimension["identifier"]["effective"]["unit"],
                    "declared_value_unit": records_by_dimension["value"]["effective"]["unit"],
                    "declared_structural_row_unit": records_by_dimension["structural_row"]["effective"]["unit"],
                }.get(expected_unit, expected_unit)
            require(
                (case["measurement"], case["unit"], case["expected"]) == (expected_measurement, expected_unit, expected_result),
                f"{context}.{case['id']} expected result, concrete unit, or measurement is incorrect.",
            )
            exact_versions = validate_exact_versions(
                case["exact_versions"],
                f"{context}.{case['id']}.exact_versions",
                concrete_declaration,
            )
            if declaration_kind == "symbolic_template":
                require(case["measured_value"] is None and case["observed"] is None and case["evidence_id"] is None and exact_versions == [], f"{context}.{case['id']} template evidence must be pending.")
            else:
                require(case["measured_value"] is not None, f"{context}.{case['id']}.measured_value is required.")
                require(case["observed"] is not None, f"{context}.{case['id']}.observed is required.")
                require(case["observed"] == case["expected"], f"{context}.{case['id']} observed result differs from expected.")
                evidence_id = require_string(case["evidence_id"], f"{context}.{case['id']}.evidence_id")
                require(evidence_id in evidence_by_id, f"{context}.{case['id']} evidence does not resolve.")
                evidence_record = evidence_by_id[evidence_id]
                require(evidence_record["kind"] == evidence_kind, f"{context}.{case['id']} evidence kind is invalid.")
                require(evidence_record["measurement"] == case["measurement"], f"{context}.{case['id']} evidence measurement is invalid.")
                require(evidence_record["observed"] == case["measured_value"], f"{context}.{case['id']} measured value is not linked to evidence.")
                require(set(exact_versions) <= set(tested_versions), f"{context}.{case['id']} evidence versions must be tested.")
                require(active_product_version in exact_versions, f"{context}.{case['id']} evidence does not cover the active version.")
                require(set(exact_versions) <= set(evidence_record["exact_versions"]), f"{context}.{case['id']} evidence record does not cover declared versions.")

    validate_boundary_cases(
        [dolt["ddl_atomicity_case"]],
        {"ddl_atomicity": ("ddl_transaction_atomicity", "transaction_behavior", "ddl_atomicity_behavior_recorded")},
        "Dolt DDL atomicity case",
        evidence_kind="ddl_atomicity",
    )
    if concrete_declaration:
        require(dolt["ddl_atomicity_case"]["measured_value"] in {"atomic", "non_atomic"}, "Dolt DDL atomicity measured value is invalid.")

    validate_boundary_cases(
        boundary["identifier_cases"],
        {
            "L_minus_1": ("final_physical_identifier_length", "declared_identifier_unit", "accept_round_trip"),
            "L": ("final_physical_identifier_length", "declared_identifier_unit", "accept_round_trip"),
            "L_plus_1": ("final_physical_identifier_length", "declared_identifier_unit", "reject_before_mutation"),
            "multibyte_unit_measurement": ("final_physical_identifier_length", "declared_identifier_unit", "declared_unit_proved"),
            "embedded_backtick": ("source_and_physical_name", "utf8_bytes", "accept_escaped_round_trip"),
            "reserved_sql_word": ("source_and_physical_name", "utf8_bytes", "accept_quoted_round_trip"),
            "reserved_double_underscore_prefix": ("source_and_physical_name", "utf8_bytes", "accept_with_nonreserved_physical_name"),
            "truncation_collision": ("final_physical_names", "utf8_bytes", "accept_with_distinct_names_and_round_trip"),
            "casefold_collision": ("final_physical_names", "active_identifier_comparison", "accept_with_distinct_names_and_round_trip"),
            "collation_collision": ("final_physical_names", "active_collation", "accept_with_distinct_names_and_round_trip"),
            "physical_name_uniqueness": ("final_physical_names", "active_identifier_comparison", "all_unique"),
        },
        "Dolt identifier cases",
    )
    validate_boundary_cases(
        boundary["column_cases"],
        {
            "source_N": ("source_variable_count", "variables", "accept"),
            "source_N_plus_1": ("source_variable_count", "variables", "reject_before_mutation"),
            "physical_N_plus_1": ("physical_column_count_including_case_ordinal", "columns", "accept"),
            "physical_N_plus_2": ("physical_column_count_including_case_ordinal", "columns", "reject_before_mutation"),
        },
        "Dolt column cases",
    )
    validate_boundary_cases(
        boundary["longtext_cases"],
        {
            "schema_LONGTEXT": ("catalog_introspection_type", "sql_type", "equals_LONGTEXT"),
            "schema_NOT_NULL": ("catalog_introspection_nullability", "sql_nullability", "equals_NOT_NULL"),
            "empty_string": ("encoded_value", "utf8_bytes", "accept_byte_exact_round_trip"),
            "sql_null": ("stored_value", "sql_null", "reject"),
            "utf8_byte_exact_equality": ("encoded_value", "utf8_bytes", "accept_byte_exact_round_trip"),
            "encoded_65535_bytes": ("encoded_value", "utf8_bytes", "accept_byte_exact_round_trip"),
            "encoded_65536_bytes": ("encoded_value", "utf8_bytes", "accept_byte_exact_round_trip"),
            "V_minus_1": ("encoded_value", "declared_value_unit", "accept_byte_exact_round_trip"),
            "V": ("encoded_value", "declared_value_unit", "accept_byte_exact_round_trip"),
            "V_plus_1": ("encoded_value", "declared_value_unit", "reject_before_mutation"),
        },
        "Dolt LONGTEXT cases",
    )
    validate_boundary_cases(
        boundary["double_cases"],
        {
            "positive_zero": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "negative_zero": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "minimum_positive_subnormal": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "maximum_subnormal": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "minimum_normal": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "maximum_finite": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "ordinary_positive_finite": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "ordinary_negative_finite": ("ieee_754_binary64", "64_bit_pattern", "accept_bit_exact_round_trip"),
            "spss_system_missing": ("semantic_missing_value", "sql_null_mapping", "accept_semantic_round_trip_via_sql_null"),
        },
        "Dolt DOUBLE cases",
    )
    validate_boundary_cases(
        boundary["double_exceptional_cases"],
        {
            "nan": ("ieee_754_binary64_exceptional_class", "exceptional_class", "reject_before_mutation"),
            "positive_infinity": ("ieee_754_binary64_exceptional_class", "exceptional_class", "reject_before_mutation"),
            "negative_infinity": ("ieee_754_binary64_exceptional_class", "exceptional_class", "reject_before_mutation"),
        },
        "Dolt exceptional DOUBLE cases",
        {"policy"},
    )
    require(
        all(case["policy"] == "reject" for case in boundary["double_exceptional_cases"]),
        "Dolt exceptional DOUBLE cases must select their policy explicitly.",
    )
    require(
        boundary["system_missing_collision_policy"] == "system_missing_uses_sql_null_and_exceptional_classes_are_rejected",
        "Dolt system-missing collision policy is incomplete.",
    )

    structural_rows = boundary["structural_row_cases"]
    require(isinstance(structural_rows, dict) and set(structural_rows) == {"variant_schema", "selected_variant"}, "Dolt structural-row fields are incomplete.")
    require(
        structural_rows["variant_schema"] == {
            "discriminator": "kind",
            "allowed_kinds": ["numeric_boundary", "not_applicable_proof"],
            "numeric_boundary_case_ids": ["R_minus_1", "R", "R_plus_1"],
            "not_applicable_required_fields": [
                "kind",
                "reason",
                "inspected_structures",
                "measurement",
                "unit",
                "measured_value",
                "expected",
                "observed",
                "evidence_id",
                "exact_versions",
            ],
        },
        "Dolt structural-row variant schema is incomplete.",
    )
    selected_structural = structural_rows["selected_variant"]
    if declaration_kind == "symbolic_template":
        require(selected_structural is None, "The pending Dolt template must not select structural evidence.")
    else:
        require(isinstance(selected_structural, dict), "A concrete Dolt declaration must select structural evidence.")
        require(selected_structural.get("kind") in {"numeric_boundary", "not_applicable_proof"}, "Dolt structural-row kind is invalid.")
        if selected_structural["kind"] == "numeric_boundary":
            require(set(selected_structural) == {"kind", "cases"}, "Dolt numeric structural-row variant fields are incomplete.")
            validate_boundary_cases(
                selected_structural["cases"],
                {
                    "R_minus_1": ("structural_row_size", "declared_structural_row_unit", "accept_round_trip"),
                    "R": ("structural_row_size", "declared_structural_row_unit", "accept_round_trip"),
                    "R_plus_1": ("structural_row_size", "declared_structural_row_unit", "reject_before_mutation"),
                },
                "Dolt structural-row numeric cases",
                evidence_kind="structural",
            )
        else:
            require(
                set(selected_structural) == set(structural_rows["variant_schema"]["not_applicable_required_fields"]),
                "Dolt structural-row not-applicable proof fields are incomplete.",
            )
            require_string(selected_structural["reason"], "Dolt structural-row not-applicable reason")
            require_string_list(selected_structural["inspected_structures"], "Dolt structural-row inspected structures")
            require(selected_structural["measurement"] == "structural_row_limit_applicability", "Dolt structural-row proof measurement is invalid.")
            require(selected_structural["unit"] == "inspection_result", "Dolt structural-row proof unit is invalid.")
            require(selected_structural["measured_value"] is not None, "Dolt structural-row proof measured value is required.")
            require(selected_structural["expected"] == "not_applicable_proved", "Dolt structural-row proof expectation is invalid.")
            require(selected_structural["observed"] == selected_structural["expected"], "Dolt structural-row proof observation differs from expected.")
            structural_evidence_id = require_string(selected_structural["evidence_id"], "Dolt structural-row proof evidence_id")
            require(structural_evidence_id in evidence_by_id, "Dolt structural-row proof evidence does not resolve.")
            structural_evidence = evidence_by_id[structural_evidence_id]
            require(structural_evidence["kind"] == "structural", "Dolt structural-row proof evidence kind is invalid.")
            require(structural_evidence["measurement"] == selected_structural["measurement"], "Dolt structural-row proof evidence measurement is invalid.")
            require(structural_evidence["observed"] == selected_structural["measured_value"], "Dolt structural-row proof measured value is not linked to evidence.")
            structural_versions = validate_exact_versions(
                selected_structural["exact_versions"],
                "Dolt structural-row proof exact_versions",
                True,
            )
            require(set(structural_versions) <= set(tested_versions), "Dolt structural-row proof versions must be tested.")
            require(active_product_version in structural_versions, "Dolt structural-row proof does not cover the active version.")
            require(set(structural_versions) <= set(structural_evidence["exact_versions"]), "Dolt structural-row proof evidence does not cover declared versions.")
    validate_boundary_cases(
        boundary["statement_cases"],
        {
            "S_minus_1": ("encoded_statement_or_batch", "bytes", "accept"),
            "S": ("encoded_statement_or_batch", "bytes", "accept"),
            "S_plus_1": ("encoded_statement_or_batch", "bytes", "reject_or_split_before_emit"),
            "multi_batch_dataset": ("dataset_total_and_each_emitted_batch", "bytes", "accept_when_every_batch_at_most_S"),
        },
        "Dolt statement cases",
    )

    if concrete_declaration:
        def indexed_cases(case_group: list[dict[str, object]]) -> dict[str, dict[str, object]]:
            return {case["id"]: case for case in case_group}

        identifier_cases = indexed_cases(boundary["identifier_cases"])
        column_cases = indexed_cases(boundary["column_cases"])
        value_cases = indexed_cases(boundary["longtext_cases"])
        statement_cases = indexed_cases(boundary["statement_cases"])
        limit_l = records_by_dimension["identifier"]["effective"]["value"]
        limit_n = records_by_dimension["source_variables"]["effective"]["value"]
        limit_physical = records_by_dimension["physical_columns"]["effective"]["value"]
        limit_v = records_by_dimension["value"]["effective"]["value"]
        limit_s = records_by_dimension["emitted_statement"]["effective"]["value"]
        require(identifier_cases["L_minus_1"]["measured_value"] == limit_l - 1, "Dolt L-1 case is not linked to effective L.")
        require(identifier_cases["L"]["measured_value"] == limit_l, "Dolt L case is not linked to effective L.")
        require(identifier_cases["L_plus_1"]["measured_value"] == limit_l + 1, "Dolt L+1 case is not linked to effective L.")
        require(column_cases["source_N"]["measured_value"] == limit_n, "Dolt N case is not linked to effective N.")
        require(column_cases["source_N_plus_1"]["measured_value"] == limit_n + 1, "Dolt N+1 case is not linked to effective N.")
        require(column_cases["physical_N_plus_1"]["measured_value"] == limit_physical, "Dolt physical N+1 case is not linked to the effective column limit.")
        require(column_cases["physical_N_plus_2"]["measured_value"] == limit_physical + 1, "Dolt physical N+2 case is not linked to the effective column limit.")
        require(value_cases["encoded_65535_bytes"]["measured_value"] == 65535, "Dolt 65535-byte case has the wrong measured value.")
        require(value_cases["encoded_65536_bytes"]["measured_value"] == 65536, "Dolt 65536-byte case has the wrong measured value.")
        require(value_cases["V_minus_1"]["measured_value"] == limit_v - 1, "Dolt V-1 case is not linked to effective V.")
        require(value_cases["V"]["measured_value"] == limit_v, "Dolt V case is not linked to effective V.")
        require(value_cases["V_plus_1"]["measured_value"] == limit_v + 1, "Dolt V+1 case is not linked to effective V.")
        require(statement_cases["S_minus_1"]["measured_value"] == limit_s - 1, "Dolt S-1 case is not linked to effective S.")
        require(statement_cases["S"]["measured_value"] == limit_s, "Dolt S case is not linked to effective S.")
        require(statement_cases["S_plus_1"]["measured_value"] == limit_s + 1, "Dolt S+1 case is not linked to effective S.")

        structural_limit = records_by_dimension["structural_row"]["effective"]
        if selected_structural["kind"] == "numeric_boundary":
            require(isinstance(structural_limit["value"], int) and not isinstance(structural_limit["value"], bool), "Dolt numeric structural branch requires a numeric effective R.")
            require(structural_limit["unit"] in {"bytes", "characters"}, "Dolt numeric structural branch requires a numeric effective R unit.")
            structural_cases = indexed_cases(selected_structural["cases"])
            limit_r = structural_limit["value"]
            require(structural_cases["R_minus_1"]["measured_value"] == limit_r - 1, "Dolt R-1 case is not linked to effective R.")
            require(structural_cases["R"]["measured_value"] == limit_r, "Dolt R case is not linked to effective R.")
            require(structural_cases["R_plus_1"]["measured_value"] == limit_r + 1, "Dolt R+1 case is not linked to effective R.")
        else:
            applicable_structural_records = [
                record
                for record in limits["structural_row"]
                if record["applicable"]
            ]
            for structural_record in applicable_structural_records:
                require(structural_record["unit"] == "not_applicable", f"Dolt structural N/A {structural_record['basis']} layer requires the not_applicable unit.")
                require(isinstance(structural_record["value"], dict) and structural_record["value"].get("kind") == "not_applicable_proof", f"Dolt structural N/A {structural_record['basis']} layer requires a structured proof.")
                require(structural_record["value"]["reason"] == selected_structural["reason"], f"Dolt structural N/A {structural_record['basis']} reason differs from the selected proof.")
                require(structural_record["value"]["inspected_structures"] == selected_structural["inspected_structures"], f"Dolt structural N/A {structural_record['basis']} inspected structures differ from the selected proof.")

    fault = boundary["fault_conformance"]
    require(isinstance(fault, dict), "Dolt fault-conformance declaration must be an object.")
    require(
        set(fault) == {
            "diagnostic_code",
            "injection_inventory",
            "fault_cases",
            "verification",
            "cleanup_failed_detail_json_required_fields",
            "success_status_forbidden_on_cleanup_failure",
        },
        "Dolt fault-conformance fields are incomplete.",
    )
    require(fault["diagnostic_code"] == "cleanup_failed", "Dolt cleanup-failure diagnostic code is incorrect.")
    injection_inventory = fault["injection_inventory"]
    require(isinstance(injection_inventory, list), "Dolt fault injection inventory must be an array.")
    require(all(isinstance(item, dict) for item in injection_inventory), "Dolt fault injection inventory entries must be objects.")
    injection_ids = [item.get("injection_id") for item in injection_inventory]
    require(all(isinstance(injection_id, str) and injection_id for injection_id in injection_ids), "Dolt fault injection IDs must be nonempty strings.")
    require(len(injection_ids) == len(set(injection_ids)), "Dolt fault injection IDs must be unique.")
    if declaration_kind == "symbolic_template":
        require(injection_inventory == [], "The pending Dolt template must not claim a fault inventory.")
    else:
        require(bool(injection_inventory), "A concrete Dolt declaration needs a fault injection inventory.")
        for index, item in enumerate(injection_inventory):
            inventory_context = f"Dolt fault injection inventory[{index}]"
            require(set(item) == {"injection_id", "phase", "mutation", "evidence_id", "exact_versions", "observed"}, f"{inventory_context} fields are incomplete.")
            require(item["phase"] in {"catalog_or_data_mutation", "compensating_cleanup"}, f"{inventory_context}.phase is invalid.")
            require_string(item["mutation"], inventory_context + ".mutation")
            inventory_evidence_id = require_string(item["evidence_id"], inventory_context + ".evidence_id")
            require(inventory_evidence_id in evidence_by_id, f"{inventory_context} evidence does not resolve.")
            inventory_evidence = evidence_by_id[inventory_evidence_id]
            require(inventory_evidence["kind"] == "fault", f"{inventory_context} evidence kind is invalid.")
            inventory_versions = validate_exact_versions(item["exact_versions"], inventory_context + ".exact_versions", True)
            require(active_product_version in inventory_versions and set(inventory_versions) <= set(tested_versions), f"{inventory_context} versions do not cover the active tested version.")
            require(set(inventory_versions) <= set(inventory_evidence["exact_versions"]), f"{inventory_context} evidence does not cover declared versions.")
            require(item["observed"] == "fault_injected", f"{inventory_context}.observed is invalid.")
            require(inventory_evidence["measurement"] == item["mutation"] and inventory_evidence["observed"] == item["observed"], f"{inventory_context} is not linked to evidence.")

    validate_boundary_cases(
        fault["fault_cases"],
        {
            "mutation_fault_cleanup_succeeds": (
                "after_each_catalog_and_data_ddl_dml_mutation",
                "fault_injection_point",
                "operation_failed_zero_residuals",
            ),
            "compensating_cleanup_fault": (
                "during_compensating_cleanup",
                "fault_injection_point",
                "operation_failed_cleanup_failed_diagnostic_with_residual_inventory",
            ),
        },
        "Dolt fault cases",
        evidence_kind="fault",
    )
    if concrete_declaration:
        fault_cases = {case["id"]: case for case in fault["fault_cases"]}
        mutation_ids = [item["injection_id"] for item in injection_inventory if item["phase"] == "catalog_or_data_mutation"]
        cleanup_ids = [item["injection_id"] for item in injection_inventory if item["phase"] == "compensating_cleanup"]
        require(bool(mutation_ids) and bool(cleanup_ids), "Dolt fault inventory must cover mutation and cleanup phases.")
        require(fault_cases["mutation_fault_cleanup_succeeds"]["measured_value"] == {"covered_injection_ids": mutation_ids, "coverage_count": len(mutation_ids)}, "Dolt mutation-fault case is not linked to its injection inventory.")
        require(fault_cases["compensating_cleanup_fault"]["measured_value"] == {"covered_injection_ids": cleanup_ids, "coverage_count": len(cleanup_ids)}, "Dolt cleanup-fault case is not linked to its injection inventory.")
    require(
        fault["verification"] == [
            "catalog_relations",
            "physical_data_table",
            "residual_objects",
            "dolt_status_diff",
            "branch",
            "commit_head",
        ],
        "Dolt fault verification inventory is incomplete.",
    )
    require(fault["verification"] == catalog_boundary["post_failure_verification"], "Dolt fault and catalog post-failure inventories diverge.")
    require(
        fault["cleanup_failed_detail_json_required_fields"] == cleanup_failure["detail_json_required_fields"],
        "Dolt cleanup-failure detail fields diverge from the core audit contract.",
    )
    require(
        fault["diagnostic_code"] == cleanup_failure["diagnostic_code"]
        and fault["success_status_forbidden_on_cleanup_failure"] is True,
        "Dolt cleanup-failure diagnostics diverge from the core audit contract.",
    )
    return dolt


def _json_from_resource(resource: Traversable, context: str) -> Any:
    try:
        return json.loads(resource.read_bytes().decode("utf-8"))
    except OSError as error:
        raise DoltDeclarationError(
            context + " could not be read.", code="resource_io_error",
        ) from None
    except UnicodeDecodeError as error:
        raise DoltDeclarationError(
            context + " is not UTF-8.", code="resource_not_utf8",
        ) from error
    except json.JSONDecodeError as error:
        raise DoltDeclarationError(
            context + " is not valid JSON.", code="resource_invalid_json",
        ) from error


def load_validated_dolt_declarations(
    source: DoltDeclarationSource | None = None,
) -> tuple[Mapping[str, Any], ...]:
    """Load the authoritative schema/template and every concrete declaration."""

    declaration_source = source or DoltDeclarationSource.packaged()
    baseline = declaration_source.read_json("sql/dialect-profile-baseline.json")
    require(isinstance(baseline, dict), "SQL dialect baseline must be an object.")
    profiles = baseline.get("profiles")
    require(isinstance(profiles, dict), "SQL dialect profiles are missing.")
    symbolic = profiles.get("dolt")
    require(
        isinstance(symbolic, dict)
        and symbolic.get("declaration_kind") == "symbolic_template",
        "Dolt repository baseline must remain a symbolic template.",
    )
    validate_dolt_declaration(
        symbolic, "Dolt symbolic baseline", source=declaration_source,
    )

    schema = declaration_source.read_json(
        "sql/dolt-adapter-declaration-schema.json",
    )
    expected_schema = {
        "schema_id": "openstatspec-dolt-adapter-declaration-v1",
        "schema_version": 1,
        "artifact_glob": "sql/dolt-adapter-declarations/*.json",
        "evidence_artifact_root": "sql/dolt-adapter-declarations/evidence",
        "declaration_root_type": "full_dolt_profile_declaration",
        "required_declaration_kind": "concrete_adapter",
        "required_conformance_status": "tested",
        "required_import_enabled": True,
        "evidence_required": True,
        "required_binding_fields": [
            "declaration_id",
            "adapter_implementation_id",
            "adapter_version",
            "specification_commit",
            "conformance_run_id",
        ],
        "required_top_level_fields": sorted(symbolic),
        "validator_entrypoint": (
            "openstatspec_specification.dolt::validate_dolt_declaration"
        ),
    }
    require(schema == expected_schema, "Dolt adapter declaration schema is incomplete.")

    declarations: list[Mapping[str, Any]] = []
    declaration_ids: set[str] = set()
    conformance_run_ids: set[str] = set()
    for resource in declaration_source.declaration_resources():
        declaration = _json_from_resource(
            resource, "Dolt declaration " + resource.name,
        )
        require(
            isinstance(declaration, dict),
            "Dolt declaration " + resource.name + " must be an object.",
        )
        require(
            declaration.get("declaration_kind") == "concrete_adapter",
            "Dolt declaration " + resource.name
            + " must be a concrete adapter declaration.",
        )
        validated = validate_dolt_declaration(
            declaration,
            "Dolt declaration " + resource.name,
            source=declaration_source,
        )
        declaration_id = str(validated["declaration_id"])
        conformance_run_id = str(validated["conformance_run_id"])
        require(
            declaration_id not in declaration_ids,
            "Dolt declaration_id is duplicated: " + declaration_id,
        )
        require(
            conformance_run_id not in conformance_run_ids,
            "Dolt conformance_run_id is duplicated: " + conformance_run_id,
        )
        declaration_ids.add(declaration_id)
        conformance_run_ids.add(conformance_run_id)
        declarations.append(validated)
    return tuple(declarations)


def select_dolt_declaration(
    declarations: tuple[Mapping[str, Any], ...],
    *,
    active_product_version: str,
    adapter_implementation_id: str,
    adapter_version: str,
    specification_commit: str,
) -> Mapping[str, Any]:
    """Require one exact product/adapter/specification binding."""

    matches = tuple(
        declaration
        for declaration in declarations
        if declaration.get("active_product_version") == active_product_version
        and declaration.get("adapter_implementation_id")
        == adapter_implementation_id
        and declaration.get("adapter_version") == adapter_version
        and declaration.get("specification_commit") == specification_commit
    )
    if len(matches) != 1:
        raise DoltDeclarationError(
            "Expected exactly one Dolt declaration for the active product, "
            "adapter version, and specification commit; found "
            + str(len(matches))
            + ".",
            code=(
                "dolt_declaration_missing"
                if not matches
                else "dolt_declaration_ambiguous"
            ),
        )
    return matches[0]


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
    require(version_policy["claim_scope"] == "maintained_release_series", "Server claims must remain conservative release-series claims.")
    require(version_policy["ci_evidence"] == "exact_patch_version", "Server CI evidence must name exact patch versions.")
    require(
        version_policy["reference_adapter_targets"]
        == {
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
        },
        "SQL server version targets are unexpected.",
    )
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

    load_validated_dolt_declarations(
        DoltDeclarationSource.from_directory(ROOT),
    )



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
    validate_dialect_baseline()
    json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"Validated {len(identifiers) - 1} binary fixtures and one generated preflight fixture.")


if __name__ == "__main__":
    main()
