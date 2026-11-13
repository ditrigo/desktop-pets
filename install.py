#!/usr/bin/env python3
"""Install or update Desktop Duck, preserving configuration and rolling back failures."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

PLUGIN_ID = "ditrigo.desktop-duck"
SOURCE = Path(__file__).resolve().parent


def runtime_files(source):
    """Only ship files used by the plugin or its local installer."""
    files = [
        p
        for p in source.iterdir()
        if p.is_file()
        and (
            p.name
            in (
                "manifest.json",
                "README.md",
                "ART-TOOL.md",
                "CONTRIBUTING.md",
                "SECURITY.md",
                "CHANGELOG.md",
                "preview.png",
                "LICENSE",
                "install.py",
                "install.sh",
            )
        )
    ]
    runtime = source / "src"
    if runtime.exists():
        files.extend(
            p
            for p in runtime.rglob("*")
            if p.is_file()
            and not any(
                part.startswith(".") or part == "__pycache__"
                for part in p.relative_to(runtime).parts
            )
        )
    docs = source / "docs"
    if docs.exists():
        files.extend(
            p
            for p in docs.rglob("*")
            if p.is_file()
            and p.suffix in (".md", ".png", ".svg")
            and not any(part.startswith(".") for part in p.relative_to(docs).parts)
        )
    return sorted(files)


def atomic_bytes(path, contents):
    fd, temporary = tempfile.mkstemp(prefix=".duck-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def package(source, destination):
    """Give QML and its JS imports a fresh URL without restarting the shell."""
    files = runtime_files(source)
    code = [
        p
        for p in files
        if p.suffix in (".qml", ".js")
        or "assets" in p.relative_to(source).parts
        or p.relative_to(source).parts[0] == "src"
    ]
    digest = hashlib.sha256()
    for file in code:
        digest.update(str(file.relative_to(source)).encode())
        digest.update(file.read_bytes())
    prefix = Path("runtime") / digest.hexdigest()[:16]
    for file in files:
        relative = file.relative_to(source)
        if relative == Path("manifest.json"):
            continue
        output = destination / (prefix / relative if file in code else relative)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, output)
    manifest = json.loads((source / "manifest.json").read_text())
    manifest["entryPoints"] = {
        key: str(prefix / path) for key, path in manifest["entryPoints"].items()
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


def validate_package(source, run=subprocess.run):
    """Validate what will ship, excluding development venvs, caches and sources."""
    source = Path(source)
    manifest = json.loads((source / "manifest.json").read_text())
    entries = list(manifest.get("entryPoints", {}).values())
    if entries and all(
        Path(path).parts and Path(path).parts[0] == "runtime" for path in entries
    ):
        run(["omarchy", "plugin", "validate", str(source)], check=True)
        return
    with tempfile.TemporaryDirectory(prefix="duck-validate-") as temp:
        destination = Path(temp)
        package(source, destination)
        run(["omarchy", "plugin", "validate", str(destination)], check=True)


def restore_settings(path, original):
    """Undo our entry only, preserving simultaneous edits to other plugins."""
    previous = json.loads(original) if original is not None else {}
    current = json.loads(path.read_bytes()) if path.exists() else {}

    def restore_list(now, old):
        result = [entry for entry in now if entry.get("id") != PLUGIN_ID]
        for index, entry in enumerate(old):
            if entry.get("id") == PLUGIN_ID:
                result.insert(min(index, len(result)), entry)
        return result

    if "plugins" in current or "plugins" in previous:
        current["plugins"] = restore_list(
            current.get("plugins", []), previous.get("plugins", [])
        )
    old_layout = previous.get("bar", {}).get("layout", {})
    layout = current.get("bar", {}).get("layout", {})
    for section in ("left", "center", "right"):
        if section in layout or section in old_layout:
            layout[section] = restore_list(
                layout.get(section, []), old_layout.get(section, [])
            )
    if layout:
        current.setdefault("bar", {})["layout"] = layout
    if current:
        atomic_bytes(
            path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode()
        )


def install(
    source,
    config,
    state,
    *,
    enable=True,
    restart=False,
    run=subprocess.run,
    sleep=time.sleep,
):
    source, config, state = Path(source), Path(config), Path(state)
    version = json.loads((source / "manifest.json").read_text())["version"]
    existing = config / "plugins" / PLUGIN_ID
    if (existing / ".git").exists() and source.resolve() != existing.resolve():
        raise RuntimeError(
            "This plugin is managed by git. Update it with omarchy plugin update, or run duck-art from that checkout; a snapshot install cannot replace its git history."
        )
    validate_package(source, run)
    if restart:
        lock = run(
            ["omarchy-shell", "lock", "isLocked"], capture_output=True, text=True
        )
        if lock.returncode == 0 and lock.stdout.strip() == "true":
            raise RuntimeError(
                "Session is locked. Install without --restart; the plugin supports hot updates."
            )
    shell_file = config / "shell.json"
    original = shell_file.read_bytes() if shell_file.exists() else None
    if original is not None:
        json.loads(original)  # Reject malformed configuration before any mutation.
    plugins = config / "plugins"
    target = plugins / PLUGIN_ID
    backup = state / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    plugins.mkdir(parents=True, exist_ok=True)
    if original is not None:
        (backup / "shell.json").write_bytes(original)
    memory = state / "memory.json"
    if memory.exists():
        shutil.copy2(memory, backup / "memory.json")
    before = run(
        ["omarchy-shell", "desktop-duck", "status"], capture_output=True, text=True
    )
    try:
        live_before = json.loads(before.stdout) if before.returncode == 0 else None
    except (ValueError, TypeError):
        live_before = None
    if live_before:
        run(["omarchy-shell", "desktop-duck", "save"], capture_output=True, check=True)
    # Staging and rollback are on the same filesystem as the plugin directory.
    staging = Path(tempfile.mkdtemp(prefix=".duck-update-", dir=config))
    displaced = staging / "previous"
    replaced = False
    in_place = source.resolve() == target.resolve()
    try:
        if not in_place:
            packaged = staging / "plugin"
            packaged.mkdir()
            package(source, packaged)
            run(["omarchy", "plugin", "validate", str(packaged)], check=True)
            if target.exists():
                shutil.copytree(target, backup / "plugin", symlinks=True)
                target.rename(displaced)
            try:
                packaged.rename(target)
            except BaseException:
                if displaced.exists():
                    displaced.rename(target)
                raise
            replaced = True
        run(["omarchy-shell", "shell", "rescanPlugins"], check=True)
        for _ in range(40):
            catalog = run(
                ["omarchy", "plugin", "list", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
            if any(p.get("id") == PLUGIN_ID for p in json.loads(catalog.stdout)):
                break
            sleep(0.1)
        else:
            raise RuntimeError("Desktop Duck was not registered by the shell")
        if enable:
            run(["omarchy", "plugin", "enable", PLUGIN_ID], check=True)
        if restart:
            run(["omarchy", "restart", "shell"], check=True)
        if live_before or enable:
            for _ in range(60):
                probe = run(
                    ["omarchy-shell", "desktop-duck", "status"],
                    capture_output=True,
                    text=True,
                )
                try:
                    live = json.loads(probe.stdout) if probe.returncode == 0 else {}
                except ValueError:
                    live = {}
                if live.get("version") == version and live.get("runState") not in (
                    None,
                    "loading",
                ):
                    break
                sleep(0.1)
            else:
                raise RuntimeError(
                    "New service did not start; retry with --restart to clear the QML cache"
                )
            if live_before and live.get("paused") != live_before.get("paused"):
                run(["omarchy-shell", "desktop-duck", "action", "pause"], check=True)
            if live_before and live_before.get("opened"):
                run(["omarchy-shell", "desktop-duck", "show"], check=True)
        return target, backup
    except BaseException:
        if replaced:
            if target.exists():
                shutil.rmtree(target)
            if displaced.exists():
                displaced.rename(target)
            restore_settings(shell_file, original)
            run(["omarchy-shell", "shell", "rescanPlugins"], capture_output=True)
            if restart:
                run(["omarchy", "restart", "shell"], capture_output=True)
        print(f"Update failed; recovery files: {backup}")
        raise
    finally:
        shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-enable",
        action="store_true",
        help="Install without adding the widget to the bar",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart the shell to clear its compiled QML cache",
    )
    args = parser.parse_args()
    config = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy"
    )
    state = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "omarchy-desktop-duck"
    )
    target, backup = install(
        SOURCE, config, state, enable=not args.no_enable, restart=args.restart
    )
    print(f"Installed: {target}\nBackups: {backup}")


if __name__ == "__main__":
    main()
