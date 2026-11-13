#!/usr/bin/env python3
"""Mandatory release checks; logs fail on the first unsuccessful command."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    manifest = json.loads((ROOT / "manifest.json").read_text())
    version = manifest["version"]
    assert (ROOT / "src/Service.qml").read_text().count(
        'version:"' + version + '"'
    ) == 2, "service/manifest version mismatch"
    env = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        OMARCHY_LANGUAGE_FILE=str(ROOT / "tests/fixtures/language-ru"),
    )
    env.setdefault(
        "UV_PROJECT_ENVIRONMENT",
        str(
            Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            / "desktop-pets-art"
            / hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
        ),
    )
    commands = [
        ["node", "--test", "tests/model.test.cjs"],
        [
            "uv",
            "run",
            "--frozen",
            "--project",
            str(ROOT),
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ],
    ]
    commands += [["./pet-art", "check"]]
    commands += [
        ["python", "integration/" + name + ".py"]
        for name in [
            "check_lint",
            "check_qml",
            "check_adapter",
            "check_settings",
            "check_window",
            "check_persistence",
            "check_i18n",
        ]
    ]
    commands += [
        ["/usr/lib/qt6/bin/qmltestrunner", "-input", "integration/" + name + ".qml"]
        for name in ["tst_input", "tst_flat", "tst_blender"]
    ]
    commands += [
        [
            "uv",
            "run",
            "--offline",
            "--with",
            "pillow",
            "--no-project",
            "python",
            "integration/check_assets.py",
        ]
    ]
    commands += [
        ["uv", "run", "--offline", "--with", "pillow", "--no-project", "python", name]
        for name in [
            "integration/check_asset_failures.py",
            "integration/check_blend_export.py",
        ]
    ]
    if "--live" in sys.argv:
        commands.append(["python", "integration/check_passthrough.py"])
    for cmd in commands:
        print("CHECK", *cmd, flush=True)
        checkenv = dict(os.environ) if cmd[-1].endswith("check_passthrough.py") else env
        subprocess.run(cmd, env=checkenv, check=True)
    print("ALL CHECKS PASSED", version)


if __name__ == "__main__":
    main()
