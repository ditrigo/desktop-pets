#!/usr/bin/env python3
"""Render the editable Blender master and pack cropped modular sprite atlases.

uv run --with pillow python integration/build_blender_assets.py
Use --pack-only to reuse raw renders while iterating on QML/packing.
"""

import argparse
import hashlib
import sys
from collections import defaultdict
import json
import math
from pathlib import Path
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
from asset_hulls import alpha_hull

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--raw", type=Path, default=ROOT / "art/blender/renders")
parser.add_argument("--pack-only", action="store_true")
parser.add_argument(
    "--blend",
    type=Path,
    help="Export this edited master without rebuilding or saving it",
)
parser.add_argument(
    "--check-only", action="store_true", help="Validate a selected blend and exit"
)
parser.add_argument(
    "--sample-only",
    action="store_true",
    help="Render one selected-blend body frame without packing",
)
parser.add_argument(
    "--output",
    type=Path,
    help="Pack into an isolated model folder without changing built-in assets or JS",
)
args = parser.parse_args()
args.raw = args.raw.resolve()
if (args.check_only or args.sample_only) and not args.blend:
    parser.error("--check-only/--sample-only require --blend")
if args.blend and args.pack_only:
    parser.error("--blend and --pack-only are exclusive")
if args.blend:
    chosen = args.blend.resolve(strict=True)
    before = hashlib.sha256(chosen.read_bytes()).hexdigest()
    command = [
        "blender",
        "--background",
        "--disable-autoexec",
        str(chosen),
        "--python-exit-code",
        "1",
        "--python",
        str(ROOT / "art/blender/render_existing.py"),
        "--",
        "--output",
        str(args.raw),
    ]
    if args.check_only:
        command.append("--check-only")
    if args.sample_only:
        command.append("--sample-only")
    if args.output:
        command.append("--assets-only")
    try:
        subprocess.run(command, check=True)
    finally:
        if hashlib.sha256(chosen.read_bytes()).hexdigest() != before:
            raise RuntimeError("Blender source changed during export")
    if args.check_only or args.sample_only:
        sys.exit(0)
elif not args.pack_only:
    subprocess.run(
        [
            "blender",
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "art/blender/build_duck.py"),
            "--",
            "--output",
            str(args.raw),
        ],
        check=True,
    )
raw = json.loads((args.raw / "manifest.json").read_text())
views = list(raw["views"])
out = args.output.resolve() if args.output else ROOT / "src/assets/duck3d"
out.mkdir(parents=True, exist_ok=True)
groups = defaultdict(list)
for item in raw["renders"]:
    groups[item["part"]].append(item)
manifest = {
    "contractVersion": 1,
    "version": 1,
    "width": 120,
    "height": 112,
    "renderScale": 3,
    "views": raw["views"],
    "parts": {},
    "actions": raw["actions"],
    "blender": raw["blender"],
    "wingAngles": raw["wingAngles"],
}
if raw.get("partLabels"):
    manifest["labels"] = raw["partLabels"]
for name, items in groups.items():
    poses = items[0]["poses"]
    frames = [None] * (len(views) * poses)
    bounds = []
    hit_bounds = [None] * len(frames)
    for item in items:
        im = Image.open(args.raw / item["file"]).convert("RGBA")
        assert im.size == (360, 336)
        bbox = im.getchannel("A").getbbox()
        # A far wing can be completely hidden behind the body in a side view.
        if bbox:
            bounds.append(bbox)
        index = views.index(item["view"]) * poses + item["pose"]
        frames[index] = im
        hit_bounds[index] = [round(v / 3, 3) for v in bbox] if bbox else None
    assert all(im is not None for im in frames), name
    x0 = max(0, min(b[0] for b in bounds) - 2)
    y0 = max(0, min(b[1] for b in bounds) - 2)
    x1 = min(360, max(b[2] for b in bounds) + 2)
    y1 = min(336, max(b[3] for b in bounds) + 2)
    w = x1 - x0
    h = y1 - y0
    cols = min(6, len(frames))
    rows = math.ceil(len(frames) / cols)
    atlas = Image.new("RGBA", (w * cols, h * rows))
    for i, im in enumerate(frames):
        atlas.paste(im.crop((x0, y0, x1, y1)), ((i % cols) * w, (i // cols) * h))
    file = name + ".png"
    atlas.save(out / file, optimize=True)
    manifest["parts"][name] = {
        "file": file,
        "x": x0 / 3,
        "y": y0 / 3,
        "width": w / 3,
        "height": h / 3,
        "cellWidth": w,
        "cellHeight": h,
        "columns": cols,
        "rows": rows,
        "poses": poses,
        "frames": len(frames),
    }
    if "wing." in name:
        manifest["parts"][name]["hitBounds"] = hit_bounds
    manifest["parts"][name]["hulls"] = [alpha_hull(im, 1 / 3) for im in frames]
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
if args.output:
    print("PACKED", len(manifest["parts"]), "atlases into", out)
    sys.exit(0)
(ROOT / "src/DuckAtlas.js").write_text(
    "// Generated by integration/build_blender_assets.py; do not edit by hand.\nvar data = "
    + json.dumps(manifest, separators=(",", ":"))
    + ";\n"
)
review = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
review.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.raw / "preview.png", review / "blender-preview.png")
# A short animation reference and a readable contact sheet, independent of Qt.
font = (
    ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 18)
    if Path("/usr/share/fonts/TTF/DejaVuSans.ttf").exists()
    else ImageFont.load_default(size=18)
)
contact = Image.new("RGB", (1080, 760), "#202a36")
draw = ImageDraw.Draw(contact)
for i, name in enumerate(("walk", "fly", "wave", "dance", "sleep", "eat")):
    frames = []
    for path in sorted((args.raw / "animation").glob(name + "-*.png")):
        canvas = Image.new("RGBA", (360, 336), "#202a36")
        canvas.alpha_composite(Image.open(path).convert("RGBA"))
        frames.append(canvas.convert("RGB"))
    contact.paste(frames[2], ((i % 3) * 360, (i // 3) * 380))
    draw.text(
        ((i % 3) * 360 + 22, (i // 3) * 380 + 340), name, fill="#ead4a3", font=font
    )
    frames[0].save(
        review / (name + ".webp"),
        save_all=True,
        append_images=frames[1:],
        duration=125,
        loop=0,
        lossless=True,
    )
contact.save(review / "animations.png")
print(
    "PACKED",
    len(manifest["parts"]),
    "atlases;",
    sum(p.stat().st_size for p in out.glob("*.png")),
    "PNG bytes",
)
