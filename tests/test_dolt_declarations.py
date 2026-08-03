from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.openstatspec_specification.dolt import (
    DoltDeclarationError,
    DoltDeclarationSource,
    load_validated_dolt_declarations,
    select_dolt_declaration,
    validate_dolt_declaration,
)


ROOT = Path(__file__).resolve().parents[1]


class DoltDeclarationTests(unittest.TestCase):
    def test_repository_schema_and_empty_declaration_set(self) -> None:
        self.assertEqual(
            load_validated_dolt_declarations(
                DoltDeclarationSource.from_directory(ROOT)
            ),
            (),
        )

    def test_concrete_declaration_binds_profile_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                "sql/dialect-profile-baseline.json",
                "sql/dolt-adapter-declaration-schema.json",
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            evidence = root / "sql/dolt-adapter-declarations/evidence/result.json"
            evidence.parent.mkdir(parents=True)
            payload = b"tested evidence\n"
            evidence.write_bytes(payload)
            baseline = json.loads(
                (ROOT / "sql/dialect-profile-baseline.json").read_text()
            )
            declaration = {
                "active_product_version": "2.2.2",
                "adapter_implementation_id": "openstatspec-python",
                "adapter_version": "0.5.0",
                "conformance_run_id": "run-20260803",
                "conformance_status": "tested",
                "declaration_id": "python-dolt-2.2.2",
                "declaration_schema_id": "openstatspec-dolt-adapter-declaration-v1",
                "evidence_records": [{
                    "artifact_ref": "sql/dolt-adapter-declarations/evidence/result.json",
                    "artifact_sha256": hashlib.sha256(payload).hexdigest(),
                    "evidence_id": "service-matrix",
                    "exact_versions": ["2.2.2"],
                }],
                "import_enabled": True,
                "profile": copy.deepcopy(baseline["profiles"]["dolt"]),
                "specification_commit": "a" * 40,
            }
            self.assertIs(
                validate_dolt_declaration(
                    declaration,
                    authoritative_profile=baseline["profiles"]["dolt"],
                    source=DoltDeclarationSource.from_directory(root),
                ),
                declaration,
            )

    def test_profile_drift_fails_closed_before_evidence(self) -> None:
        baseline = json.loads(
            (ROOT / "sql/dialect-profile-baseline.json").read_text()
        )
        profile = copy.deepcopy(baseline["profiles"]["dolt"])
        profile["maximum_columns_default"] += 1
        declaration = {
            "active_product_version": "2.2.2",
            "adapter_implementation_id": "openstatspec-python",
            "adapter_version": "0.5.0",
            "conformance_run_id": "run-20260803",
            "conformance_status": "tested",
            "declaration_id": "python-dolt-2.2.2",
            "declaration_schema_id": "openstatspec-dolt-adapter-declaration-v1",
            "evidence_records": [],
            "import_enabled": True,
            "profile": profile,
            "specification_commit": "a" * 40,
        }
        with self.assertRaisesRegex(DoltDeclarationError, "authoritative"):
            validate_dolt_declaration(
                declaration,
                authoritative_profile=baseline["profiles"]["dolt"],
                source=DoltDeclarationSource.from_directory(ROOT),
            )

    def test_exact_selection_rejects_zero_and_multiple_matches(self) -> None:
        binding = {
            "active_product_version": "2.2.2",
            "adapter_implementation_id": "openstatspec-python",
            "adapter_version": "0.5.0",
            "specification_commit": "a" * 40,
        }
        with self.assertRaises(DoltDeclarationError) as missing:
            select_dolt_declaration((), **binding)
        self.assertEqual(missing.exception.code, "dolt_declaration_missing")
        declaration = {**binding, "declaration_id": "one"}
        with self.assertRaises(DoltDeclarationError) as ambiguous:
            select_dolt_declaration((declaration, declaration), **binding)
        self.assertEqual(ambiguous.exception.code, "dolt_declaration_ambiguous")


if __name__ == "__main__":
    unittest.main()
