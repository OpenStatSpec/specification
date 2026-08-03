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


if __name__ == "__main__":
    try:
        main()
    except DoltDeclarationError as error:
        raise SystemExit(str(error)) from error
