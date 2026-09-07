"""Validate the source repository with the installable shared implementation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openstatspec_specification.dolt import (  # noqa: E402
    DoltDeclarationError,
    main,
)
from openstatspec_specification.artifacts import (  # noqa: E402
    ArtifactValidationError,
    validate_contract_artifacts,
    validate_release_metadata,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DoltDeclarationError(message, code="repository_validation_failed")


def require_phrases(text: str, phrases: tuple[str, ...], context: str) -> None:
    for phrase in phrases:
        require(phrase in text, f"{context} is missing: {phrase}")


def validate_repository_controls() -> None:
    """Keep source-repository release controls outside the reusable package."""

    schema = (ROOT / "sql/schema-outline.sql").read_text(encoding="utf-8")
    identity_marker = "CREATE TABLE catalog_identity ("
    require(identity_marker in schema, "Catalog identity table is missing.")
    identity_ddl = schema.split(identity_marker, 1)[1].split(");", 1)[0]
    for field in ("catalog_identity_key", "contract_id", "schema_version", "created_at"):
        require(field in identity_ddl, f"Catalog identity field is missing: {field}")
    require(
        "CHECK (contract_id = 'openstatspec-strict-wide-table-v1')" in identity_ddl,
        "Catalog identity contract is not enforced by the logical schema.",
    )
    for forbidden in ("specification_status", "specification_release", "specification_commit"):
        require(
            forbidden not in identity_ddl,
            f"Catalog identity must not duplicate capability field: {forbidden}",
        )

    dialects = (ROOT / "sql/dialect-profiles.md").read_text(encoding="utf-8")
    require_phrases(
        dialects,
        (
            "fixed single-schema `search_path`",
            "connection fixed to that selected database",
            "## Dolt profile",
            "Dolt is an independent profile.",
            "MySQL wire compatibility is a transport",
            "The repository baseline is a `symbolic_template`",
            "separate full-profile artifact under",
            "trim and case-fold `@@version_comment`",
            "`DOLT_VERSION()`",
            "rejects before mutation",
            "A Dolt repository commit is not an SQL transaction",
        ),
        "Dialect profile invariant",
    )

    capabilities = (ROOT / "sql/profile-capabilities.md").read_text(encoding="utf-8")
    require_phrases(
        capabilities,
        (
            "selected profile and database engine separately from transport and driver",
            "separate list of exact CI-tested server versions",
            "maximum value, row-size and per-statement limits",
            "transport selection is not product identity",
            "zero database mutation",
        ),
        "Dolt capability requirement",
    )
    require("row-count" not in capabilities, "Capabilities must not invent an unsupported row-count limit.")

    server_policy = (ROOT / "sql/server-version-policy.md").read_text(encoding="utf-8")
    require_phrases(
        server_policy,
        (
            "A floating major, minor or",
            "MySQL 26.7 is excluded",
            "Dolt remains an independent, essential profile",
            "`>=3.24.0,<4.0.0`",
            "`>=3.35.0,<4.0.0`",
            "roadmap-only; see the",
        ),
        "SQL server version policy",
    )

    mssql_roadmap = (ROOT / "docs/mssql-dialect-roadmap.md").read_text(encoding="utf-8")
    require_phrases(
        mssql_roadmap,
        (
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
        ),
        "MSSQL roadmap",
    )

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

    io_policy = (ROOT / "docs/database-io-policy-v1.md").read_text(encoding="utf-8")
    require_phrases(
        io_policy,
        (
            '"database_io_policy": "openstatspec-database-io-v1"',
            "Adapters not selecting this policy retain every existing requirement.",
            "MUST NOT issue database writes",
            "temporary tables",
            "`allow_loss`",
            "2.2.2 and 2.2.3",
            "release CI",
            "Unknown or untested versions MUST fail before mutation.",
            "user-supplied declaration or evidence files",
            "expected branch and HEAD",
            "conformance/spss-sav-zsav-1.0.json",
        ),
        "Optional database I/O policy",
    )

    validate_release_metadata(ROOT)


if __name__ == "__main__":
    try:
        main()
        inventory = validate_contract_artifacts(ROOT)
        validate_repository_controls()
        print(
            "Validated contract artifacts: "
            f"Plan {dict(inventory.plan_cases)}, "
            f"Frontend {dict(inventory.frontend_effective_cases)}, "
            f"Binding {dict(inventory.binding_cases)}."
        )
    except (DoltDeclarationError, ArtifactValidationError) as error:
        raise SystemExit(str(error)) from error
