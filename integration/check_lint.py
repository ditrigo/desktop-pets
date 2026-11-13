#!/usr/bin/env python3
"""Lint each runtime QML file with isolated imports and no allowed warnings."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = [Path(name).resolve() for name in sys.argv[1:]] or sorted(
        (ROOT / "src").glob("*.qml")
    )
    shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
    with tempfile.TemporaryDirectory(prefix="duck-lint-") as temp:
        imports = Path(temp)
        (imports / "qs").mkdir()
        for name in ("Commons", "Ui"):
            (imports / "qs" / name).symlink_to(shell / name)
        for source in files:
            result = subprocess.run(
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "--ignore-settings",
                    "--max-warnings",
                    "0",
                    "--json",
                    "-",
                    "-I",
                    "/usr/lib/qt6/qml",
                    "-I",
                    str(imports),
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            # JSON preserves diagnostics that text output can omit when several
            # entry files share imports. A fresh process also isolates each file.
            report = json.loads(result.stdout)
            for entry in report["files"]:
                for warning in entry["warnings"]:
                    print(
                        f"{entry['filename']}:{warning['line']}:{warning['column']}: "
                        f"{warning['type']}: {warning['message'].strip()} [{warning['id']}]",
                        file=sys.stderr,
                    )
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            if result.returncode or not all(f["success"] for f in report["files"]):
                raise SystemExit(result.returncode or 1)
    print(f"QML LINT OK: {len(files)} files, zero warnings")


if __name__ == "__main__":
    main()
