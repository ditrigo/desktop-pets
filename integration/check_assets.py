#!/usr/bin/env python3
"""Validate the graphics ABI and generated metadata, frame sets and pixel alpha."""

from pathlib import Path
import io
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops
from asset_hulls import alpha_hull

ROOT = Path(__file__).resolve().parents[1]


def svg_image(path):
    return Image.open(
        io.BytesIO(
            subprocess.run(
                ["rsvg-convert", str(path)], capture_output=True, check=True
            ).stdout
        )
    ).convert("RGBA")


def generated(contract):
    return (
        "// Generated from assets/duck-contract.json by integration/check_assets.py --generate\nvar data = "
        + json.dumps(contract, separators=(",", ":"))
        + ";\n"
    )


def validate(root=ROOT):
    c = json.loads((root / "src/assets/duck-contract.json").read_text())
    assert c["version"] == 1, "unsupported graphics contract"
    assert c["canvas"] == [120, 112] and len(set(c["modes"])) == len(c["modes"])
    assert (root / "src/DuckGeometry.js").read_text() == generated(c), (
        "stale geometry JS"
    )
    flat = json.loads((root / "src/assets/duck2d/manifest.json").read_text())
    for key, value in flat.items():
        assert c["flat"][key] == value, ("flat metadata drift", key)
    palettes = ["yellow", "mallard", "white"]
    hats = flat["hats"]
    outfits = flat["outfits"]
    uniforms = flat["uniforms"]
    parts = {"foot"}
    for view in c["views"]:
        for palette in palettes:
            parts.update(
                [
                    f"{palette}-body-{view}",
                    f"{palette}-body-{view}-sleep",
                    f"{palette}-head-{view}",
                    f"{palette}-head-{view}-covered",
                ]
            )
        for state in ["open", "closed", "wide"]:
            parts.add(f"eyes-{view}-{state}")
        for hat in hats:
            parts.add(f"hat-{hat}-{view}")
        for outfit in outfits:
            parts.add(f"neck-{outfit}-{view}")
        for outfit in uniforms + ["cape"]:
            for suffix in ["", "-sleep"]:
                parts.add(f"outfit-{outfit}-{view}{suffix}")
    for view in ["side", "front"]:
        for palette in palettes:
            parts.add(f"{palette}-wing-{view}")
        for outfit in uniforms:
            parts.add(f"sleeve-{outfit}-{view}")
    for name in parts:
        svg = root / "src/assets/duck2d/vector" / (name + ".svg")
        ET.parse(svg)
        assert "clipPath" not in svg.read_text(), (
            "unbaked SVG clipping unsupported by runtime",
            name,
        )
        im = Image.open(root / "src/assets/duck2d/pixel" / (name + ".png"))
        assert im.mode == "RGBA"
        assert set(im.getchannel("A").tobytes()) <= {0, 255}, (
            "nonbinary pixel alpha",
            name,
        )
        assert (
            len(c["flat"]["hulls"][name]) >= 3
            and len(c["flat"]["vectorHulls"][name]) >= 3
        ), ("missing interaction contour", name)
    # Fit against actual opaque pixels, rather than just checking rig anchors.
    flat = c["flat"]
    head_offset = flat["headOffset"]
    hat_offset = flat["pixelHatOffset"]
    dx, dy = [(hat_offset[i] - head_offset[i]) // 2 for i in range(2)]
    for view in c["views"]:
        head = Image.open(
            root / "src/assets/duck2d/pixel" / f"yellow-head-{view}-covered.png"
        ).getchannel("A")
        for hat in hats:
            cap = Image.open(
                root / "src/assets/duck2d/pixel" / f"hat-{hat}-{view}.png"
            ).getchannel("A")
            brim_y = cap.getbbox()[3] - 1
            head_row = [x for x in range(head.width) if head.getpixel((x, brim_y + dy))]
            assert len(head_row) >= 16, ("hat perched above crown", hat, view)
            if hat == "santa":
                brim = [x + dx for x in range(cap.width) if cap.getpixel((x, brim_y))]
                assert (
                    abs((min(brim) + max(brim) - min(head_row) - max(head_row)) / 2)
                    <= 0.5
                ), ("winter hat off center", view)
        for suffix in ["", "-sleep"]:
            torso = Image.open(
                root / "src/assets/duck2d/pixel" / f"yellow-body-{view}{suffix}.png"
            ).getchannel("A")
            for outfit in uniforms:
                cloth = Image.open(
                    root
                    / "src/assets/duck2d/pixel"
                    / f"outfit-{outfit}-{view}{suffix}.png"
                ).getchannel("A")
                assert ImageChops.subtract(cloth, torso).getbbox() is None, (
                    "uniform outside torso",
                    outfit,
                    view,
                    suffix,
                )
                assert (
                    cloth.getbbox() == torso.getbbox()
                    if view == "front"
                    else cloth.getbbox()[1:] == torso.getbbox()[1:]
                ), ("uniform does not cover torso", outfit, view, suffix)
    # The redesigned classic torso and wing masks must also fit their clothing.
    for view in c["views"]:
        for suffix in ["", "-sleep"]:
            torso = svg_image(
                root / "src/assets/duck2d/vector" / f"yellow-body-{view}{suffix}.svg"
            ).getchannel("A")
            for outfit in uniforms:
                cloth = svg_image(
                    root
                    / "src/assets/duck2d/vector"
                    / f"outfit-{outfit}-{view}{suffix}.svg"
                ).getchannel("A")
                assert ImageChops.subtract(cloth, torso).getextrema()[1] <= 8, (
                    "classic uniform outside torso",
                    outfit,
                    view,
                    suffix,
                )
    for style in ["vector", "pixel"]:
        for view in ["side", "front"]:
            load = (
                svg_image
                if style == "vector"
                else lambda p: Image.open(p).convert("RGBA")
            )
            ext = "svg" if style == "vector" else "png"
            wing = load(
                root / f"src/assets/duck2d/{style}" / f"yellow-wing-{view}.{ext}"
            ).getchannel("A")
            for outfit in uniforms:
                sleeve = load(
                    root
                    / f"src/assets/duck2d/{style}"
                    / f"sleeve-{outfit}-{view}.{ext}"
                ).getchannel("A")
                assert ImageChops.subtract(sleeve, wing).getextrema()[1] <= 8, (
                    "sleeve outside wing",
                    style,
                    outfit,
                    view,
                )
    m = json.loads((root / "src/assets/duck3d/manifest.json").read_text())
    assert m.get("contractVersion") == c["version"], "atlas ABI mismatch"
    assert (
        [m["width"], m["height"]] == c["canvas"]
        and list(m["views"]) == c["views"]
        and m["wingAngles"] == c["wingAngles"]
    )
    atlas_js = (root / "src/DuckAtlas.js").read_text()
    assert json.loads(atlas_js.split("var data = ", 1)[1].strip().rstrip(";")) == m, (
        "stale atlas JS"
    )
    expected = set()
    for palette in palettes:
        expected.update(
            [
                palette + "-body",
                palette + "-head",
                *[
                    palette + "-" + part
                    for part in ["wing.near", "wing.far", "foot.near", "foot.far"]
                ],
            ]
        )
    expected.update(
        ["hat." + x for x in ["wizard", "pirate", "santa", "explorer", "chef", "crown"]]
    )
    expected.update(["outfit." + x for x in ["scarf", "sailor", "space", "cape"]])
    assert set(m["parts"]) == expected, "missing atlas parts"
    for view in m["views"].values():
        assert set(view["pivots"]) == set(c["bones"])
    for name, d in m["parts"].items():
        poses = (
            8
            if "wing." in name
            else 4
            if "foot." in name
            else 3
            if name.endswith("-head")
            else 1
        )
        assert d["poses"] == poses and d["frames"] == 3 * poses, (
            name,
            "missing frames",
        )
        im = Image.open(root / "src/assets/duck3d" / d["file"])
        assert im.size == (d["columns"] * d["cellWidth"], d["rows"] * d["cellHeight"])
        assert d["rows"] * d["columns"] >= d["frames"]
        if "wing." in name:
            assert len(d["hitBounds"]) == d["frames"]
        assert len(d["hulls"]) == d["frames"], "missing contour frames"
    print(
        "ASSETS OK",
        len(parts),
        "flat parts × 2;",
        len(expected),
        "atlases; ABI",
        c["version"],
    )


if __name__ == "__main__":
    if "--generate" in sys.argv:
        c = json.loads((ROOT / "src/assets/duck-contract.json").read_text())
        c["flat"].update(
            json.loads((ROOT / "src/assets/duck2d/manifest.json").read_text())
        )
        c["flat"]["hulls"] = {
            p.stem: alpha_hull(Image.open(p).convert("RGBA"), 2)
            for p in sorted((ROOT / "src/assets/duck2d/pixel").glob("*.png"))
        }
        c["flat"]["vectorHulls"] = {
            p.stem: alpha_hull(svg_image(p))
            for p in sorted((ROOT / "src/assets/duck2d/vector").glob("*.svg"))
        }
        (ROOT / "src/assets/duck-contract.json").write_text(
            json.dumps(c, indent=2) + "\n"
        )
        (ROOT / "src/DuckGeometry.js").write_text(generated(c))
    validate()
