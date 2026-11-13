#!/usr/bin/env python3
"""One entry point for Desktop Duck models, clothing and visual review."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

import artlib as lib


def models(value):
    keys = value.split(",")
    if not keys or any(not lib.KEY.fullmatch(key) for key in keys):
        raise argparse.ArgumentTypeError(
            "Comma-separated keys, for example: vector,pixel"
        )
    return keys


def report(data, stats):
    print(
        f"Catalogue: {len(data['models'])} models, {len(data['hats'])} hats, {len(data['outfits'])} garments, {len(data['looks'])} looks."
    )
    print(
        f"Unchanged: {stats['unchanged']}. Cached: {stats['cached']}; processed: {stats['processed']}."
    )


def install(root):
    sys.path.insert(0, str(root))
    from install import install as update

    config = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy"
    )
    state = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "omarchy-desktop-duck"
    )
    target, backup = update(root, config, state, enable=False)
    print(f"Installed: {target}\nBackup: {backup}")


def infer_kind(root, data, key, explicit=None):
    if explicit:
        return explicit
    path = root / "art/packs" / key / "pack.json"
    if path.exists():
        return lib.read_json(path)["kind"]
    for kind, group in [
        ("look", "looks"),
        ("model", "models"),
        ("hat", "hats"),
        ("outfit", "outfits"),
    ]:
        if any(item["key"] == key for item in data[group]):
            return kind
    raise lib.ArtError(f"Missing asset: {key}")


def unpack(source, destination):
    if source.is_dir():
        lib.files_in(source)
        shutil.copytree(source, destination, dirs_exist_ok=True)
        return
    lib.require(
        source.is_file() and source.stat().st_size <= lib.MAX_PACK,
        "Missing pack directory or ZIP",
    )
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        seen = set()
        total = 0
        lib.require(len(members) <= 1024, "Too many files ZIP")
        for member in members:
            lib.require(member.filename not in seen, "Duplicate ZIP path")
            seen.add(member.filename)
            path = lib.safe_path(destination, member.filename)
            lib.require(
                not stat.S_ISLNK(member.external_attr >> 16),
                "ZIP symlinks are not allowed",
            )
            total += member.file_size
            lib.require(
                member.file_size <= lib.MAX_FILE and total <= lib.MAX_PACK,
                "ZIP is too large",
            )
            if member.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as stream, path.open("wb") as target:
                    shutil.copyfileobj(stream, target)


def rebuild_flat(root):
    """Old artist scripts run in an isolated copy, then publish together."""
    import fcntl

    cache = root / ".cache/duck-art"
    cache.mkdir(parents=True, exist_ok=True)
    with (
        (cache / "build.lock").open("a") as lock,
        tempfile.TemporaryDirectory(prefix="flat-", dir=cache) as temp,
    ):
        fcntl.flock(lock, fcntl.LOCK_EX)
        staged = Path(temp)
        for path in root.iterdir():
            if path.is_file():
                shutil.copy2(path, staged / path.name)
        for name in ("art", "src", "integration", "tools"):
            shutil.copytree(
                root / name,
                staged / name,
                ignore=shutil.ignore_patterns("__pycache__", "renders"),
            )
        subprocess.run(
            [sys.executable, str(staged / "art/flat/build_skins.py")],
            cwd=staged,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(staged / "integration/check_assets.py"), "--generate"],
            cwd=staged,
            check=True,
        )
        shutil.rmtree(staged / "src/assets/custom", ignore_errors=True)
        data, cache = lib.compile_catalog(staged, staged)
        outputs = lib.generated_files(staged, data)
        for name in (
            "src/assets/duck-contract.json",
            "src/DuckGeometry.js",
            "src/assets/duck2d/manifest.json",
        ):
            outputs[name] = (staged / name).read_bytes()
        for path in (staged / "src/assets/duck2d").rglob("*"):
            if path.is_file():
                outputs[str(path.relative_to(staged))] = path.read_bytes()
        lib.commit(root, staged, outputs)
        return data, dict(unchanged=False, cached=cache.hits, processed=cache.misses)


def parser():
    result = argparse.ArgumentParser(
        prog="duck-art",
        description="Desktop Duck art studio: template → artwork → check → preview → install.",
    )
    result.add_argument("--root", type=Path, default=lib.ROOT, help=argparse.SUPPRESS)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check available tools")
    commands.add_parser("list", help="List catalogue entries and compatibility")
    new = commands.add_parser("new", help="Create an editable template")
    new.add_argument("kind", choices=["model", "hat", "outfit", "look"])
    new.add_argument("key")
    new.add_argument("--label", required=True)
    new.add_argument(
        "--base",
        default="vector",
        help="Base model: vector, pixel, voxel or a custom model",
    )
    new.add_argument("--models", type=models, default=["vector", "pixel"])
    new.add_argument("--template", help="Hat or garment to copy")
    new.add_argument("--hat", default="none")
    new.add_argument("--outfit", default="none")
    for name, help_text in [
        ("build", "Build the catalogue and cache changed asset contours"),
        ("install", "Check, build and install with a backup"),
    ]:
        command = commands.add_parser(name, help=help_text)
        if name == "build":
            command.add_argument("--install", action="store_true")
            command.add_argument(
                "--rebuild-flat",
                action="store_true",
                help="Also rebuild built-in vector and pixel artwork",
            )
    check = commands.add_parser(
        "check", help="Check the library or a pack before import"
    )
    check.add_argument("source", nargs="?", type=Path)
    preview = commands.add_parser(
        "preview", help="Preview models and clothes using the actual QML renderer"
    )
    preview.add_argument("key")
    preview.add_argument("--kind", choices=["model", "hat", "outfit", "look"])
    preview.add_argument("--models", type=models)
    preview.add_argument(
        "--guides", action="store_true", help="Show interaction contours"
    )
    preview.add_argument("--live", action="store_true", help="Open a preview window")
    preview.add_argument("--output", type=Path)
    fit = commands.add_parser("fit", help="Adjust placement in the pack descriptor")
    fit.add_argument("key")
    fit.add_argument("--model", required=True)
    fit.add_argument("--part", choices=["hat", "neck", "body", "sleeve"], required=True)
    fit.add_argument("--view", choices=[*lib.VIEWS, "all"], default="all")
    fit.add_argument(
        "--rect", nargs=4, type=float, required=True, metavar=("X", "Y", "W", "H")
    )
    imported = commands.add_parser("import", help="Import a pack directory or ZIP")
    imported.add_argument("source", type=Path)
    exported = commands.add_parser("export", help="Export an editable pack")
    exported.add_argument("key")
    exported.add_argument("--output", type=Path, required=True)
    remove = commands.add_parser("remove", help="Remove a custom pack with a backup")
    remove.add_argument("key")
    blend = commands.add_parser(
        "blender", help="Import a compatible Blender model into a new pack"
    )
    blend.add_argument("source", type=Path)
    blend.add_argument("--key", required=True)
    blend.add_argument("--label", required=True)
    blend.add_argument(
        "--update",
        action="store_true",
        help="Update an existing pack, restoring the previous version on failure",
    )
    watch = commands.add_parser(
        "watch", help="Rebuild and refresh previews when pack files change"
    )
    watch.add_argument("key")
    watch.add_argument("--models", type=models)
    watch.add_argument("--install", action="store_true")
    watch.add_argument("--guides", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    root = args.root.resolve()
    command = args.command
    if hasattr(args, "key"):
        lib.require(
            isinstance(args.key, str) and lib.KEY.fullmatch(args.key),
            "Invalid asset key",
        )
    if command == "doctor":
        for name in ("uv", "rsvg-convert", "quickshell", "blender"):
            print(f"{name}: {shutil.which(name) or 'not found'}")
        print("Python:", sys.version.split()[0])
        return 0
    if command == "check":
        if args.source:
            with tempfile.TemporaryDirectory(prefix="duck-art-import-check-") as temp:
                unpack(args.source.resolve(), Path(temp))
                data, cache = lib.check(root, Path(temp))
        else:
            data, cache = lib.check(root)
            sys.path.insert(0, str(root))
            from install import validate_package

            validate_package(root)
        print(f"Checks passed. Cached: {cache.hits}; processed: {cache.misses}.")
        return 0
    if command in ("new", "import", "blender"):
        previous = None
        if command == "new":
            created = lib.new_pack(
                root,
                args.kind,
                args.key,
                args.label,
                base=args.base,
                targets=args.models,
                template=args.template,
                hat=args.hat,
                outfit=args.outfit,
            )
        elif command == "import":
            with tempfile.TemporaryDirectory(prefix="duck-art-import-") as temp:
                staged = Path(temp)
                unpack(args.source.resolve(), staged)
                data, cache = lib.check(root, staged)
                spec = lib.read_json(staged / "pack.json")
                created = root / "art/packs" / spec["key"]
                lib.require(not created.exists(), f"Pack already exists: {created}")
                shutil.copytree(staged, created)
        else:
            source = args.source.resolve(strict=True)
            created = root / "art/packs" / args.key
            if args.update:
                spec = lib.read_json(created / "pack.json")
                lib.identity(spec, created)
                lib.require(
                    spec["kind"] == "model", "Blender can only update model packs"
                )
                data, _ = lib.build(root)
                lib.require(
                    lib.find_model(data, args.key)["renderer"] == "atlas",
                    "An atlas model is required",
                )
                previous = Path(tempfile.mkdtemp(prefix="duck-art-blender-backup-"))
                shutil.copytree(created, previous / "pack")
                spec["label"] = args.label
                lib.atomic_write(created / "pack.json", lib.encoded(spec))
            else:
                created = lib.new_pack(
                    root, "model", args.key, args.label, base="voxel"
                )
            try:
                spec = lib.read_json(created / "pack.json")
                subprocess.run(
                    [
                        sys.executable,
                        str(root / "integration/build_blender_assets.py"),
                        "--blend",
                        str(source),
                        "--output",
                        str(lib.safe_path(created, spec.get("directory", "model"))),
                        "--raw",
                        str(root / ".cache/duck-art/blender" / args.key),
                    ],
                    check=True,
                )
            except BaseException:
                shutil.rmtree(created)
                if previous:
                    shutil.copytree(previous / "pack", created)
                    shutil.rmtree(previous)
                raise
        try:
            data, stats = lib.build(root)
        except BaseException:
            shutil.rmtree(created)
            if previous:
                shutil.copytree(previous / "pack", created)
                shutil.rmtree(previous)
            raise
        if previous:
            shutil.rmtree(previous)
        print(
            f"Created: {created}\nEdit the artwork and pack.json, then run duck-art preview {created.name}"
        )
        report(data, stats)
        return 0
    if command == "fit":
        path = root / "art/packs" / args.key / "pack.json"
        spec = lib.read_json(path)
        lib.identity(spec, path)
        lib.require(
            spec["kind"] in ("hat", "outfit"), "fit applies to hats and garments"
        )
        lib.require(
            args.model in spec["variants"], "This pack has no variant for that model"
        )
        variant = spec["variants"][args.model]
        placement = variant.setdefault("placement", {}).setdefault(args.part, {})
        lib.require(
            args.part != "sleeve" or args.view != "threeQuarter",
            "Sleeves use side and front views",
        )
        projections = ("side", "front") if args.part == "sleeve" else lib.VIEWS
        for view in projections if args.view == "all" else [args.view]:
            placement[view] = args.rect
        lib.check_placement(variant["placement"])
        before = path.read_bytes()
        lib.atomic_write(path, lib.encoded(spec))
        try:
            data, stats = lib.build(root)
        except BaseException:
            lib.atomic_write(path, before)
            raise
        print(f"Placement saved: {path}")
        report(data, stats)
        return 0
    if command == "export":
        folder = root / "art/packs" / args.key
        lib.files_in(folder)
        lib.identity(lib.read_json(folder / "pack.json"), folder)
        with tempfile.TemporaryDirectory(prefix="duck-art-export-check-") as temp:
            lib.compile_catalog(root, Path(temp))
        target = args.output.resolve()
        lib.require(not target.exists(), f"File already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in lib.files_in(folder):
                archive.write(path, path.relative_to(folder))
        print(target)
        return 0
    if command == "remove":
        lib.require(lib.KEY.fullmatch(args.key), "Invalid key")
        folder = root / "art/packs" / args.key
        lib.require(folder.is_dir(), "Only custom packs can be removed")
        backup = (
            root
            / ".cache/duck-art/removed"
            / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{args.key}"
        )
        backup.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(backup)
        try:
            data, stats = lib.build(root)
        except BaseException:
            backup.rename(folder)
            raise
        print(f"Backup: {backup}")
        report(data, stats)
        return 0
    if command == "build" and args.rebuild_flat:
        data, stats = rebuild_flat(root)
    else:
        data, stats = lib.build(root)
    if command in ("build", "install"):
        report(data, stats)
        if command == "install" or args.install:
            install(root)
    elif command == "list":
        for group in ("models", "hats", "outfits", "looks"):
            print(group + ":")
            for item in data[group]:
                print(
                    "  "
                    + item["key"]
                    + " — "
                    + item["label"]
                    + (
                        " [" + ", ".join(item["models"]) + "]"
                        if "models" in item
                        else ""
                    )
                )
    elif command in ("preview", "watch"):
        from art_preview import render

        kind = infer_kind(root, data, args.key, getattr(args, "kind", None))
        output = (
            getattr(args, "output", None)
            or root / "review/art-tool" / f"{args.key}.png"
        )
        if command == "preview":
            print(
                render(
                    root,
                    data,
                    args.key,
                    kind,
                    output,
                    targets=args.models,
                    guides=args.guides,
                    live=args.live,
                )
            )
        else:
            (root / "art/packs").mkdir(parents=True, exist_ok=True)
            last = None
            last_error = None
            print("Watching art/packs. Press Ctrl+C to stop.", flush=True)
            while True:
                try:
                    digest = {
                        p.name: lib.pack_digest(p)
                        for p in sorted((root / "art/packs").iterdir())
                    }
                    if digest != last:
                        data, stats = lib.build(root)
                        report(data, stats)
                        print(
                            render(
                                root,
                                data,
                                args.key,
                                kind,
                                output,
                                targets=args.models,
                                guides=args.guides,
                            ),
                            flush=True,
                        )
                        if args.install:
                            install(root)
                        last = digest
                        last_error = None
                except (lib.ArtError, subprocess.SubprocessError, OSError) as error:
                    if str(error) != last_error:
                        print(
                            f"Error; the last working catalogue was preserved: {error}",
                            file=sys.stderr,
                            flush=True,
                        )
                    last_error = str(error)
                time.sleep(1)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (
        lib.ArtError,
        OSError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        print(f"duck-art: {error}", file=sys.stderr)
        sys.exit(1)
