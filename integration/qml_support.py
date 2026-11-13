"""Shared local dependencies for isolated Quickshell test configurations."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dependencies(folder, *, language="ru"):
    shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
    for name in ("Commons", "Ui"):
        target = folder / name
        if not target.exists():
            target.symlink_to(shell / name)
    if not (folder / "i18n").exists():
        (folder / "i18n").symlink_to(ROOT / "src/i18n")
    if language:
        os.environ.setdefault(
            "OMARCHY_LANGUAGE_FILE",
            str(ROOT / "tests/fixtures" / ("language-" + language)),
        )
