#!/usr/bin/env python3
"""Build reproducible, validated Omarchy runtime and source releases."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install import runtime_files  # noqa: E402

ROOT_FILES = {
    "manifest.json",
    "README.md",
    "ART-TOOL.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "LICENSE",
    "preview.png",
    ".gitignore",
    "install.py",
    "install.sh",
    "pet-art",
    "pyproject.toml",
    "uv.lock",
}
SOURCE_DIRS = {"src", "art", "tools", "tests", "integration", "docs", ".github"}
OMIT = {
    "__pycache__",
    ".git",
    ".venv",
    ".cache",
    ".ruff_cache",
    ".pytest_cache",
    "review",
    "dist",
    "renders",
}


def validate(folder, *, host=True):
    manifest = json.loads((folder / "manifest.json").read_text())
    for key in (
        "schemaVersion",
        "id",
        "name",
        "version",
        "author",
        "description",
        "kinds",
        "entryPoints",
    ):
        if key not in manifest:
            raise ValueError(f"Manifest is missing {key}")
    if (
        manifest["schemaVersion"] != 1
        or not manifest["kinds"]
        or manifest["id"].startswith("omarchy.")
    ):
        raise ValueError("Invalid third-party plugin manifest")
    for relative in manifest["entryPoints"].values():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not (folder / path).is_file():
            raise ValueError(f"Invalid entry point: {relative}")
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Release contains a symlink: {path}")
    if host:
        subprocess.run(["omarchy", "plugin", "validate", str(folder)], check=True)
    return manifest


def source_files(root):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in OMIT for part in relative.parts) or path.name.endswith(
            (".pyc", ".blend1")
        ):
            continue
        if relative.parts[0] not in SOURCE_DIRS and str(relative) not in ROOT_FILES:
            continue
        if any(part.startswith(".") for part in relative.parts[1:]):
            continue
        if path.is_symlink():
            raise ValueError(f"Source contains a symlink: {relative}")
        if path.is_file():
            yield path


def copy_files(root, files, target):
    for path in files:
        relative = path.relative_to(root)
        if any(part in OMIT for part in relative.parts):
            raise ValueError(
                f"Private development state selected for release: {relative}"
            )
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, output)
        output.chmod(0o755 if path.name in ("pet-art", "install.sh") else 0o644)


def archive(folder, output):
    with (
        output.open("wb") as stream,
        gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as tar,
    ):
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            info = tar.gettarinfo(path, arcname=str(path.relative_to(folder)))
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if path.name in ("pet-art", "install.sh") else 0o644
            with path.open("rb") as content:
                tar.addfile(info, content)


def build(root=ROOT, output=None, *, host=True):
    output = output or root / "dist"
    catalog = json.loads((root / "src/assets/custom/catalog.json").read_text())
    packs = root / "art/packs"
    if catalog.get("packDigests") or any(
        path.is_file() or path.is_symlink() for path in packs.rglob("*")
    ):
        raise ValueError(
            "Export and remove personal art packs before building a public release"
        )
    manifest = json.loads((root / "manifest.json").read_text())
    if not (root / "preview.png").is_file():
        raise ValueError("Create preview.png with python tools/make_preview.py")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="duck-release-") as temp:
        for kind in ("runtime", "source"):
            stage = Path(temp) / kind
            stage.mkdir()
            files = (
                list(source_files(root)) if kind == "source" else runtime_files(root)
            )
            copy_files(root, files, stage)
            validate(stage, host=host)
            suffix = "-source" if kind == "source" else ""
            name = f"{manifest['id']}-{manifest['version']}{suffix}.tar.gz"
            target = output / name
            archive(stage, target)
            records.append(
                {
                    "name": name,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "bytes": target.stat().st_size,
                    "files": len(files),
                }
            )
    (output / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['name']}\n" for item in records)
    )
    report = {
        "id": manifest["id"],
        "version": manifest["version"],
        "hostValidated": host,
        "artifacts": records,
    }
    (output / "release.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--skip-host-validation",
        action="store_true",
        help="Portable CI only; still check manifest, paths and archive contents",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build(output=args.output.resolve(), host=not args.skip_host_validation),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
