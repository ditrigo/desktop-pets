#!/usr/bin/env python3
"""Render an artist-edited copy and reject an incompatible rig, preserving source bytes."""

import hashlib
import subprocess
import tempfile
import sys
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
master = ROOT / "art/blender/desktop-duck.blend"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def export(blend, out, *options):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "integration/build_blender_assets.py"),
            "--blend",
            str(blend),
            "--raw",
            str(out),
            *options,
        ],
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory(prefix="pet-artist-") as tmp:
    p = Path(tmp)
    before = sha(master)
    script = p / "edit.py"
    script.write_text(
        "import bpy\nfor o in bpy.data.collections['body'].objects:o.scale.x*=1.3\nbpy.ops.wm.save_as_mainfile(filepath="
        + repr(str(p / "edited.blend"))
        + ")\nbpy.data.objects['DuckRig'].data.bones['head'].name='incompatible-head'\nbpy.ops.wm.save_as_mainfile(filepath="
        + repr(str(p / "bad.blend"))
        + ")\n"
    )
    subprocess.run(
        [
            "blender",
            "--background",
            str(master),
            "--python-exit-code",
            "1",
            "--python",
            str(script),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    sourcehash = sha(p / "edited.blend")
    for name, blend in [("original", master), ("edited", p / "edited.blend")]:
        result = export(blend, p / name, "--sample-only")
        assert result.returncode == 0, result.stdout + result.stderr
    a = Image.open(p / "original/side--yellow-body--0.png").convert("RGBA")
    b = Image.open(p / "edited/side--yellow-body--0.png").convert("RGBA")
    assert ImageChops.difference(a, b).getbbox() is not None, (
        "manual geometry was regenerated"
    )
    result = export(p / "bad.blend", p / "bad", "--check-only")
    assert (
        result.returncode != 0 and "Missing bone head" in result.stdout + result.stderr
    ), "incompatible rig accepted"
    assert sha(master) == before and sha(p / "edited.blend") == sourcehash, (
        "source overwritten"
    )
    print(
        "BLEND EXPORT OK: edited geometry rendered, source hashes retained, missing bone rejected"
    )
