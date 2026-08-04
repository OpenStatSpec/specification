"""Validate the repository's concrete Dolt adapter declarations."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openstatspec_specification.dolt import (  # noqa: E402
    DoltDeclarationSource,
    load_validated_dolt_declarations,
)


def main() -> None:
    declarations = load_validated_dolt_declarations(
        DoltDeclarationSource.from_directory(ROOT)
    )
    print(f"Validated {len(declarations)} concrete Dolt adapter declarations.")


if __name__ == "__main__":
    main()
