"""Coverage for ``steward.__init__``'s ``PackageNotFoundError`` fallback.

When the `steward-cli` package isn't installed (e.g. someone copied
the source tree without ``pip install -e .``), ``importlib.metadata.version``
raises ``PackageNotFoundError`` and ``steward.__version__`` falls back to
``"0.0.0+local"``. The branch can't be exercised by an in-process pytest
import because the test environment always has the package installed,
so this test forks a clean Python subprocess that monkeypatches
``importlib.metadata.version`` *before* ``steward`` is imported.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_falls_back_when_package_metadata_missing() -> None:
    """Forcing ``PackageNotFoundError`` yields the documented fallback string."""
    src = (
        "import importlib.metadata\n"
        "def _raise(*_a, **_k):\n"
        "    raise importlib.metadata.PackageNotFoundError\n"
        "importlib.metadata.version = _raise\n"
        "import steward\n"
        "print(steward.__version__)\n"
    )
    out = subprocess.check_output(
        [sys.executable, "-c", src],
        cwd=REPO_ROOT,
        text=True,
    )
    assert out.strip() == "0.0.0+local"
