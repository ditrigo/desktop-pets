"""Data-only asset packs, deterministic catalogue compilation and authoring."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integration"))
from asset_hulls import alpha_hull  # noqa: E402 - import from the working tree

VIEWS = ("side", "threeQuarter", "front")
PALETTES = ("yellow", "mallard", "white")
KEY = re.compile(r"^[a-z][a-z0-9-]{0,47}$")
MAX_FILE = 32 * 1024 * 1024
MAX_PACK = 128 * 1024 * 1024
GEOMETRY_KEYS = (
    "canvas",
    "head",
    "hat",
    "neckwear",
    "headAnchors",
    "hatOffset",
    "neckwearOffset",
    "nearWing",
    "farWing",
    "headOffset",
    "wingPartSide",
    "wingPartFront",
    "feetX",
    "feetY",
    "legTop",
    "footSize",
)


class ArtError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ArtError(message)


def read_json(path):
    require(
        path.is_file() and path.stat().st_size <= 2 * 1024 * 1024,
        f"Missing or invalid JSON: {path}",
    )
    try:
        return json.loads(path.read_text())
    except (ValueError, UnicodeError) as error:
        raise ArtError(f"{path}: {error}") from error


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def atomic_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == contents:
        return False
    fd, temp = tempfile.mkstemp(prefix=".duck-art-", dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
    return True


def safe_path(base, relative):
    require(
        isinstance(relative, str) and relative and "\\" not in relative,
        f"Invalid path: {relative!r}",
    )
    rel = Path(relative)
    require(
        not rel.is_absolute() and ".." not in rel.parts,
        f"Path escapes pack: {relative}",
    )
    current = base
    for component in rel.parts:
        current /= component
        require(not current.is_symlink(), f"Symlinks are not allowed: {current}")
    require(
        current.resolve().is_relative_to(base.resolve()),
        f"Path escapes pack: {relative}",
    )
    return current


def files_in(folder):
    require(folder.is_dir() and not folder.is_symlink(), f"Missing directory: {folder}")
    files = []
    total = 0
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), f"Symlinks are not allowed: {path}")
        if path.is_file():
            total += path.stat().st_size
            require(
                path.stat().st_size <= MAX_FILE and total <= MAX_PACK,
                f"Pack is too large: {folder}",
            )
            files.append(path)
    require(len(files) <= 1024, f"Too many files: {folder}")
    return files


def identity(spec, where):
    require(
        isinstance(spec, dict) and spec.get("schemaVersion") == 1,
        f"{where}: schemaVersion: 1 is required",
    )
    require(
        isinstance(spec.get("key"), str)
        and KEY.fullmatch(spec["key"])
        and spec["key"] not in ("none", "constructor", "prototype"),
        f"{where}: invalid key",
    )
    require(
        isinstance(spec.get("label"), str) and 0 < len(spec["label"].strip()) <= 80,
        f"{where}: label must contain 1 to 80 characters",
    )
    require(
        spec.get("kind") in ("model", "hat", "outfit", "look"), f"{where}: unknown kind"
    )
    allowed = {"schemaVersion", "kind", "key", "label"} | {
        "model": {"base", "directory", "geometry", "wardrobeBase"},
        "hat": {"variants"},
        "outfit": {"variants", "layer"},
        "look": {"hat", "outfit"},
    }[spec["kind"]]
    require(set(spec) <= allowed, f"{where}: unknown fields {set(spec) - allowed}")
    if spec["kind"] == "look":
        require(
            all(isinstance(spec.get(k), str) for k in ("hat", "outfit")),
            f"{where}: hat and outfit are required",
        )


def model_parts(geometry):
    result = {"foot": geometry["footSize"]}
    for palette in PALETTES:
        for view in VIEWS:
            for suffix in ("", "-sleep"):
                result[f"{palette}-body-{view}{suffix}"] = geometry["canvas"]
            for suffix in ("", "-covered"):
                result[f"{palette}-head-{view}{suffix}"] = geometry["head"]
        for view in ("side", "front"):
            result[f"{palette}-wing-{view}"] = [40, 30]
    for view in VIEWS:
        for state in ("open", "closed", "wide"):
            result[f"eyes-{view}-{state}"] = geometry["head"]
    return result


def clothing_parts(kind, key, layer, geometry):
    if kind == "hat":
        return {f"hat-{key}-{v}": geometry["hat"] for v in VIEWS}
    result = {f"neck-{key}-{v}": geometry["neckwear"] for v in VIEWS}
    if layer != "neck":
        result.update(
            {
                f"outfit-{key}-{v}{s}": geometry["canvas"]
                for v in VIEWS
                for s in ("", "-sleep")
            }
        )
    if layer == "uniform":
        result.update({f"sleeve-{key}-{v}": [40, 30] for v in ("side", "front")})
    return result


def check_geometry(geometry):
    require(
        isinstance(geometry, dict) and set(GEOMETRY_KEYS) <= geometry.keys(),
        "Incomplete model geometry",
    )
    require(geometry["canvas"] == [120, 112], "Model must use a 120×112 logical canvas")

    def finite_numbers(value):
        if isinstance(value, dict):
            return all(finite_numbers(v) for v in value.values())
        if isinstance(value, list):
            return all(finite_numbers(v) for v in value)
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and abs(value) <= 512
        )

    require(finite_numbers(geometry), "Coordinates must be finite numbers within ±512")
    for name in ("head", "hat", "neckwear", "footSize"):
        require(
            len(geometry[name]) == 2 and all(0 < v <= 256 for v in geometry[name]),
            f"Invalid size {name}",
        )
    for name in ("headAnchors", "nearWing", "farWing"):
        require(
            set(geometry[name]) == set(VIEWS)
            and all(len(v) == 2 for v in geometry[name].values()),
            f"Invalid anchors {name}",
        )
    for name in ("headOffset", "hatOffset", "neckwearOffset", "feetX"):
        require(
            isinstance(geometry[name], list) and len(geometry[name]) == 2,
            f"Invalid {name}",
        )
    for name in ("wingPartSide", "wingPartFront"):
        require(
            len(geometry[name]) == 4 and geometry[name][2:] == [40, 30],
            f"Invalid {name}",
        )


def check_placement(value):
    require(
        isinstance(value, dict) and set(value) <= {"hat", "neck", "body", "sleeve"},
        "Unknown placement role",
    )
    for role, views in value.items():
        require(
            isinstance(views, dict) and set(views) <= set(VIEWS),
            f"Invalid views placement.{role}",
        )
        for rect in views.values():
            require(
                isinstance(rect, list)
                and len(rect) == 4
                and all(
                    isinstance(n, (int, float))
                    and not isinstance(n, bool)
                    and math.isfinite(n)
                    and abs(n) <= 512
                    for n in rect
                )
                and rect[2] > 0
                and rect[3] > 0,
                f"Invalid rectangle placement.{role}",
            )


def svg_image(path):
    raw = path.read_bytes()
    require(
        b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
        f"{path}: DTD is not allowed",
    )
    try:
        element = ET.fromstring(raw)
    except ET.ParseError as error:
        raise ArtError(f"{path}: {error}") from error
    allowed = {
        "svg",
        "g",
        "defs",
        "path",
        "rect",
        "ellipse",
        "circle",
        "polygon",
        "polyline",
        "line",
        "linearGradient",
        "radialGradient",
        "stop",
        "title",
        "desc",
    }
    for node in element.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        require(
            tag in allowed, f"{path}: unsupported SVG element {tag}; use plain paths"
        )
        for attr, value in node.attrib.items():
            key = attr.rsplit("}", 1)[-1]
            require(
                not key.lower().startswith("on") and key != "style",
                f"{path}: use explicit SVG attributes",
            )
            require(
                "url(" not in value or re.fullmatch(r"url\(#[A-Za-z0-9_-]+\)", value),
                f"{path}: external references are not allowed",
            )
            require(
                key != "href" or value.startswith("#"),
                f"{path}: external references are not allowed",
            )
    try:
        box = [float(x) for x in element.attrib["viewBox"].replace(",", " ").split()]
    except (ValueError, KeyError) as error:
        raise ArtError(f'{path}: viewBox="0 0 width height" is required') from error
    require(
        len(box) == 4
        and box[:2] == [0, 0]
        and all(math.isfinite(n) for n in box)
        and 0 < box[2] <= 512
        and 0 < box[3] <= 512,
        f"{path}: invalid viewBox",
    )
    result = subprocess.run(
        [
            "rsvg-convert",
            "--width",
            str(math.ceil(box[2])),
            "--height",
            str(math.ceil(box[3])),
            str(path),
        ],
        capture_output=True,
        timeout=15,
    )
    require(
        result.returncode == 0,
        f"{path}: SVG error: {result.stderr.decode(errors='replace')[:300]}",
    )
    return Image.open(io.BytesIO(result.stdout)).convert("RGBA"), box[2:]


class HullCache:
    def __init__(self, root):
        self.folder = root / ".cache/duck-art/hulls"
        self.hits = 0
        self.misses = 0

    def image(self, path, format, size, pixel=False):
        require(
            path.is_file() and path.stat().st_size <= MAX_FILE, f"Missing asset: {path}"
        )
        digest = hashlib.sha256(
            path.read_bytes() + encoded([format, size, pixel, 1])
        ).hexdigest()
        cached = self.folder / (digest + ".json")
        if cached.exists():
            self.hits += 1
            return read_json(cached)
        self.misses += 1
        if format == "svg":
            image, dimensions = svg_image(path)
            require(
                dimensions == size,
                f"{path}: expected viewBox 0 0 {size[0]} {size[1]}, got {dimensions}",
            )
            scale = 1
        else:
            with Image.open(path) as source:
                require(
                    source.format == "PNG" and source.mode == "RGBA",
                    f"{path}: PNG RGBA is required",
                )
                require(
                    source.size == tuple(int(v / 2) if pixel else v for v in size),
                    f"{path}: invalid PNG dimensions, logical size {size}",
                )
                image = source.copy()
            if pixel:
                require(
                    set(image.getchannel("A").tobytes()) <= {0, 255},
                    f"{path}: pixel alpha must be 0 or 255",
                )
            scale = 2 if pixel else 1
        hull = alpha_hull(image, scale)
        require(len(hull) >= 3, f"{path}: empty part")
        atomic_write(cached, encoded(hull))
        return hull

    def atlas(self, path, spec):
        metadata = {k: v for k, v in spec.items() if k not in ("hulls", "hitBounds")}
        digest = hashlib.sha256(
            b"atlas-v1" + path.read_bytes() + encoded(metadata)
        ).hexdigest()
        cached = self.folder / (digest + ".json")
        if cached.exists():
            self.hits += 1
            return read_json(cached)
        self.misses += 1
        with Image.open(path) as image:
            require(
                image.mode == "RGBA"
                and image.format == "PNG"
                and image.size
                == (
                    spec["columns"] * spec["cellWidth"],
                    spec["rows"] * spec["cellHeight"],
                )
                and image.width * image.height <= 32_000_000,
                f"Invalid atlas image {path}",
            )
            hulls = []
            for index in range(spec["frames"]):
                x = index % spec["columns"] * spec["cellWidth"]
                y = index // spec["columns"] * spec["cellHeight"]
                frame = image.crop(
                    (x, y, x + spec["cellWidth"], y + spec["cellHeight"])
                )
                points = alpha_hull(frame, 1)
                hulls.append(
                    [
                        [
                            round(
                                spec["x"] + px * spec["width"] / spec["cellWidth"], 3
                            ),
                            round(
                                spec["y"] + py * spec["height"] / spec["cellHeight"], 3
                            ),
                        ]
                        for px, py in points
                    ]
                )
        require(any(hulls), f"Empty atlas {path}")
        atomic_write(cached, encoded(hulls))
        return hulls


def atlas(folder, cache, *, single=None):
    manifest = read_json(safe_path(folder, "manifest.json"))
    require(
        manifest.get("contractVersion") == 1
        and [manifest.get("width"), manifest.get("height")] == [120, 112],
        "Incompatible atlas format",
    )
    require(
        isinstance(manifest.get("views"), dict)
        and list(manifest["views"]) == list(VIEWS),
        "Atlas must contain three views",
    )
    require(
        isinstance(manifest.get("wingAngles"), list)
        and len(manifest["wingAngles"]) == 8
        and all(
            type(n) in (int, float) and math.isfinite(n) and abs(n) <= math.pi
            for n in manifest["wingAngles"]
        ),
        "Eight numeric wing angles are required",
    )
    for view in manifest["views"].values():
        require(
            isinstance(view, dict)
            and isinstance(view.get("pivots"), dict)
            and set(view["pivots"])
            == {
                "root",
                "body",
                "head",
                "wing.near",
                "wing.far",
                "foot.near",
                "foot.far",
            },
            "Incomplete atlas rig",
        )
        require(
            all(
                isinstance(p, list)
                and len(p) == 2
                and all(
                    isinstance(n, (int, float)) and math.isfinite(n) and abs(n) <= 512
                    for n in p
                )
                for p in view["pivots"].values()
            ),
            "Invalid rig coordinates",
        )
    parts = manifest.get("parts", {})
    require(
        isinstance(parts, dict) and 0 < len(parts) <= 128, "Invalid atlas part list"
    )
    require(
        isinstance(manifest.get("labels", {}), dict)
        and all(
            isinstance(k, str) and isinstance(v, str) and 0 < len(v.strip()) <= 80
            for k, v in manifest.get("labels", {}).items()
        ),
        "Invalid atlas labels",
    )
    if single:
        require(single in parts, f"Missing atlas part {single}")
        parts = {single: parts[single]}
    else:
        required = {
            f"{palette}-{role}"
            for palette in PALETTES
            for role in (
                "body",
                "head",
                "wing.near",
                "wing.far",
                "foot.near",
                "foot.far",
            )
        }
        require(required <= parts.keys(), "Incomplete atlas model")
    for name, spec in parts.items():
        require(
            isinstance(name, str) and isinstance(spec, dict),
            "Invalid atlas part descriptor",
        )
        path = safe_path(folder, spec.get("file"))
        require(
            path.is_file() and path.stat().st_size <= MAX_FILE,
            f"Missing atlas PNG {path}",
        )
        expected = (
            1
            if name.startswith(("hat.", "outfit."))
            else 8
            if "wing." in name
            else 4
            if "foot." in name
            else 3
            if name.endswith("-head")
            else 1
        )
        require(
            type(spec.get("poses")) is int
            and type(spec.get("frames")) is int
            and spec["poses"] == expected
            and spec["frames"] == 3 * expected,
            f"Incomplete atlas frames {name}",
        )
        for key in ("cellWidth", "cellHeight", "columns", "rows"):
            require(
                type(spec.get(key)) is int and 0 < spec[key] <= 4096,
                f"Invalid {key} of atlas {name}",
            )
        require(
            spec["columns"] * spec["rows"] >= spec["frames"], f"Not enough cells {name}"
        )
        for key in ("x", "y", "width", "height"):
            require(
                isinstance(spec.get(key), (int, float))
                and math.isfinite(spec[key])
                and abs(spec[key]) <= 512,
                f"Invalid geometry {name}",
            )
        require(spec["width"] > 0 and spec["height"] > 0, f"Empty dimensions {name}")
        spec["hulls"] = cache.atlas(path, spec)
    return manifest


def builtins(root):
    data = read_json(root / "art/catalog.json")
    require(data.get("schemaVersion") == 1, "Incompatible catalogue")
    geometry = read_json(root / "src/assets/duck-contract.json")["flat"]
    for model in data["models"]:
        if model["renderer"] == "flat":
            model["geometry"] = {k: copy.deepcopy(geometry[k]) for k in GEOMETRY_KEYS}
            if model["pixel"]:
                model["geometry"]["hatOffset"] = geometry["pixelHatOffset"]
            model["hulls"] = geometry["hulls" if model["pixel"] else "vectorHulls"]
            model["sizes"] = model_parts(model["geometry"])
        else:
            model["atlas"] = read_json(root / "src" / model["root"] / "manifest.json")
    for kind in ("hats", "outfits"):
        for entry in data[kind]:
            for target, variant in entry["variants"].items():
                variant["model"] = target
    return data


def find_model(data, key):
    model = next((m for m in data["models"] if m["key"] == key), None)
    require(model is not None, f"Unknown model: {key}")
    return model


def resolve_variant(data, kind, key, model):
    if key == "none":
        return None
    entry = next((item for item in data[kind + "s"] if item["key"] == key), None)
    if not entry:
        return None
    seen = set()
    while model["key"] not in seen:
        seen.add(model["key"])
        if model["key"] in entry["variants"]:
            return entry["variants"][model["key"]]
        if not model.get("wardrobeBase"):
            return None
        model = find_model(data, model["wardrobeBase"])
    raise ArtError("Cyclic wardrobe inheritance")


def pack_specs(root, extra=None):
    packs = []
    folder = root / "art/packs"
    if folder.exists():
        for path in sorted(folder.iterdir()):
            require(
                path.is_dir() and not path.is_symlink(),
                f"Only directories are allowed in art/packs: {path}",
            )
            files_in(path)
            spec = read_json(path / "pack.json")
            identity(spec, path)
            require(spec["key"] == path.name, f"Directory name must match key: {path}")
            packs.append((path, spec))
    if extra:
        files_in(extra)
        spec = read_json(extra / "pack.json")
        identity(spec, extra)
        packs.append((extra, spec))
    return packs


def compile_catalog(root, destination, *, extra=None):
    """Validate completely before any live/generated source is replaced."""
    data = builtins(root)
    cache = HullCache(root)
    for model in data["models"]:
        if model["renderer"] == "flat":
            sizes = model["sizes"]
            for kind in ("hat", "outfit"):
                for item in data[kind + "s"]:
                    if model["key"] in item["variants"]:
                        sizes.update(
                            clothing_parts(
                                kind, item["key"], item.get("layer"), model["geometry"]
                            )
                        )
            for name, size in sizes.items():
                hull = cache.image(
                    safe_path(
                        root / "src", model["root"] + "/" + name + "." + model["format"]
                    ),
                    model["format"],
                    size,
                    model["pixel"],
                )
                require(
                    hull == model["hulls"].get(name),
                    f"Stale contours {name}; run duck-art build --rebuild-flat",
                )
        else:
            checked = atlas(root / "src" / model["root"], cache)
            require(
                checked["parts"] == model["atlas"]["parts"],
                "Stale Blender atlas contours",
            )
    packs = pack_specs(root, extra)
    seen = {
        kind: {entry["key"] for entry in data[kind]}
        for kind in ("models", "hats", "outfits", "looks")
    }
    for folder, spec in packs:
        group = spec["kind"] + "s"
        require(
            spec["key"] not in seen[group], f"Duplicate {spec['kind']}: {spec['key']}"
        )
        seen[group].add(spec["key"])
    pending = [(folder, spec) for folder, spec in packs if spec["kind"] == "model"]
    while pending:
        ready = [
            (folder, spec)
            for folder, spec in pending
            if any(m["key"] == spec.get("base") for m in data["models"])
        ]
        require(ready, "Unknown or cyclic base model")
        for folder, spec in ready:
            base = find_model(data, spec["base"])
            model = copy.deepcopy(base)
            digest = pack_digest(folder)
            prefix = f"assets/custom/{spec['key']}/{digest}/model"
            source = safe_path(folder, spec.get("directory", "model"))
            target = destination / "src" / prefix
            target.mkdir(parents=True, exist_ok=True)
            model.update(
                key=spec["key"],
                label=spec["label"],
                root=prefix,
                wardrobeBase=spec.get(
                    "wardrobeBase", base.get("wardrobeBase") or base["key"]
                ),
                custom=True,
            )
            model.pop("labelKey", None)
            if model["renderer"] == "flat":
                require(
                    isinstance(spec.get("geometry", {}), dict)
                    and set(spec.get("geometry", {})) <= set(GEOMETRY_KEYS),
                    "Unknown geometry fields",
                )
                model["geometry"].update(spec.get("geometry", {}))
                check_geometry(model["geometry"])
                model["sizes"] = model_parts(model["geometry"])
                model["hulls"] = {}
                for name, size in model["sizes"].items():
                    path = safe_path(source, name + "." + model["format"])
                    model["hulls"][name] = cache.image(
                        path, model["format"], size, model["pixel"]
                    )
                    shutil.copy2(path, target / path.name)
            else:
                model["atlas"] = atlas(source, cache)
                for part in model["atlas"]["parts"].values():
                    path = safe_path(source, part["file"])
                    dest = target / part["file"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
                atomic_write(target / "manifest.json", encoded(model["atlas"]))
            data["models"].append(model)
            pending.remove((folder, spec))
    for model in data["models"]:
        visited = set()
        current = model
        while current.get("wardrobeBase"):
            require(current["key"] not in visited, "Cyclic wardrobe inheritance")
            visited.add(current["key"])
            parent = find_model(data, current["wardrobeBase"])
            require(
                parent["renderer"] == model["renderer"],
                "Cannot inherit clothes from a different renderer",
            )
            current = parent
    # An imported Blender master owns its exported wardrobe. Extra hat.* and
    # outfit.* collections become catalogue items without a second pack file.
    for model in data["models"]:
        if not model.get("custom") or model["renderer"] != "atlas":
            continue
        for name in model["atlas"]["parts"]:
            if not name.startswith(("hat.", "outfit.")):
                continue
            kind, key = name.split(".", 1)
            group = kind + "s"
            require(
                KEY.fullmatch(key) and key not in ("none", "constructor", "prototype"),
                f"Invalid part name of atlas: {name}",
            )
            entry = next((item for item in data[group] if item["key"] == key), None)
            if not entry:
                if key in seen[group]:
                    continue
                label = model["atlas"].get("labels", {}).get(name, key)
                require(
                    isinstance(label, str) and 0 < len(label.strip()) <= 80,
                    f"Invalid part label {name}",
                )
                entry = {"key": key, "label": label, "variants": {}, "custom": True}
                if kind == "outfit":
                    entry["layer"] = "uniform"
                data[group].append(entry)
                seen[group].add(key)
            entry["variants"][model["key"]] = {
                "model": model["key"],
                "root": model["root"],
                "format": "atlas",
                "part": name,
            }
    for folder, spec in packs:
        kind = spec["kind"]
        if kind in ("model", "look"):
            continue
        layer = spec.get("layer", "uniform") if kind == "outfit" else "hat"
        require(
            layer in ("hat", "uniform", "neck", "back")
            and (kind != "outfit" or layer != "hat"),
            f"Invalid layer: {layer}",
        )
        variants = spec.get("variants", {})
        require(isinstance(variants, dict) and variants, f"{folder}: missing variants")
        item = {
            "key": spec["key"],
            "label": spec["label"],
            "variants": {},
            "custom": True,
        }
        if kind == "outfit":
            item["layer"] = layer
        digest = pack_digest(folder)
        for key, variant in variants.items():
            model = find_model(data, key)
            require(
                isinstance(variant, dict)
                and set(variant) <= {"directory", "placement", "part"},
                f"{folder}: unknown variant fields {key}",
            )
            check_placement(variant.get("placement", {}))
            roles = (
                {"hat"}
                if kind == "hat"
                else {"neck"}
                if layer == "neck"
                else {"neck", "body"}
                if layer == "back"
                else {"neck", "body", "sleeve"}
            )
            require(
                set(variant.get("placement", {})) <= roles,
                f"{folder}: placement refers to a missing part",
            )
            require(
                "threeQuarter" not in variant.get("placement", {}).get("sleeve", {}),
                "Sleeves use side and front parts",
            )
            source = safe_path(folder, variant.get("directory", key))
            prefix = f"assets/custom/{spec['key']}/{digest}/{key}"
            target = destination / "src" / prefix
            target.mkdir(parents=True, exist_ok=True)
            result = {
                "model": key,
                "root": prefix,
                "format": model["format"],
                "prefix": spec["key"],
                "placement": variant.get("placement", {}),
            }
            if model["renderer"] == "flat":
                require("part" not in variant, "part is only supported for atlases")
                result["sizes"] = clothing_parts(
                    kind, spec["key"], layer, model["geometry"]
                )
                result["hulls"] = {}
                for name, size in result["sizes"].items():
                    path = safe_path(source, name + "." + model["format"])
                    result["hulls"][name] = cache.image(
                        path, model["format"], size, model["pixel"]
                    )
                    shutil.copy2(path, target / path.name)
            else:
                require(
                    not result["placement"],
                    "For atlases, edit x/y/width/height in manifest.json",
                )
                part = variant.get("part", kind + "." + spec["key"])
                manifest = atlas(source, cache, single=part)
                result["part"] = part
                result["spec"] = manifest["parts"][part]
                path = safe_path(source, result["spec"]["file"])
                dest = target / result["spec"]["file"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            item["variants"][key] = result
        data[kind + "s"].append(item)
    for folder, spec in packs:
        if spec["kind"] == "look":
            data["looks"].append(
                {k: spec[k] for k in ("key", "label", "hat", "outfit")}
            )
    for look in data["looks"]:
        require(
            look["hat"] in seen["hats"] | {"none"}
            and look["outfit"] in seen["outfits"] | {"none"},
            f"Unknown accessories in look {look['key']}",
        )
        look["models"] = [
            model["key"]
            for model in data["models"]
            if (
                look["hat"] == "none"
                or resolve_variant(data, "hat", look["hat"], model)
            )
            and (
                look["outfit"] == "none"
                or resolve_variant(data, "outfit", look["outfit"], model)
            )
        ]
        require(look["models"], f"Look {look['key']} has no compatible model")
    for group in ("hats", "outfits"):
        for item in data[group]:
            item["models"] = [
                model["key"]
                for model in data["models"]
                if resolve_variant(data, group[:-1], item["key"], model)
            ]
    data["packDigests"] = {spec["key"]: pack_digest(folder) for folder, spec in packs}
    return data, cache


def pack_digest(folder):
    digest = hashlib.sha256()
    for path in files_in(folder):
        digest.update(str(path.relative_to(folder)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def generated_files(root, data):
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    runtime = (root / "tools/catalog_runtime.js").read_text()
    outputs = {
        "src/DuckCatalog.js": (
            "// Generated by duck-art build. Edit art/catalog.json or art/packs.\nvar data = "
            + compact
            + ";\n"
            + runtime
        ).encode(),
        "src/assets/custom/catalog.json": encoded(data),
    }
    hats = [{"key": "none", "label": "No hat", "labelKey": "catalog.hats.none"}] + [
        {k: item[k] for k in ("key", "label", "models", "labelKey") if k in item}
        for item in data["hats"]
    ]
    outfits = [
        {"key": "none", "label": "No clothes", "labelKey": "catalog.outfits.none"}
    ] + [
        {k: item[k] for k in ("key", "label", "models", "labelKey") if k in item}
        for item in data["outfits"]
    ]
    looks = data["looks"]
    body = "// Generated by duck-art build. Presets change wardrobe keys only.\n"
    for name, value in [("options", looks), ("hats", hats), ("outfits", outfits)]:
        body += (
            "var "
            + name
            + " = "
            + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            + ";\n"
        )
    body += """function available(items,style) {return items.filter(function(item){return !item.models||item.models.indexOf(style)>=0;});}
function find(key) {for(var i=0;i<options.length;i++)if(options[i].key===key)return options[i];return null;}
function patch(key) {var look=find(key);return look?{hat:look.hat,outfit:look.outfit}:null;}
function matches(config,look) {return !!config&&config.hat===look.hat&&config.outfit===look.outfit;}
"""
    outputs["src/DuckLooks.js"] = body.encode()
    model = (root / "src/DuckModel.js").read_text()
    start = "// duck-art:keys:start"
    end = "// duck-art:keys:end"
    require(
        start in model and end in model, "DuckModel.js is missing catalogue markers"
    )
    keys = {
        field: [entry["key"] for entry in data[group]]
        for field, group in [
            ("artStyle", "models"),
            ("hat", "hats"),
            ("outfit", "outfits"),
        ]
    }
    keys["hat"].insert(0, "none")
    keys["outfit"].insert(0, "none")
    block = (
        start
        + "\nvar wardrobeKeys = "
        + json.dumps(keys, separators=(",", ":"))
        + ";\n"
    )
    outputs["src/DuckModel.js"] = (
        model.split(start)[0] + block + end + model.split(end, 1)[1]
    ).encode()
    return outputs


def commit(root, stage, outputs):
    """Roll back every changed output if a filesystem operation fails."""
    custom = root / "src/assets/custom"
    custom.mkdir(parents=True, exist_ok=True)
    pending = stage / "src/assets/custom"
    pending.mkdir(parents=True, exist_ok=True)
    atomic_write(
        pending / "catalog.json", outputs.pop("src/assets/custom/catalog.json")
    )
    with tempfile.TemporaryDirectory(
        prefix="duck-art-backup-", dir=root / ".cache/duck-art"
    ) as temp:
        backup = Path(temp)
        old = {}
        for name in outputs:
            path = root / name
            old[name] = path.read_bytes() if path.exists() else None
        custom.rename(backup / "custom")
        try:
            pending.rename(custom)
            for name, content in outputs.items():
                atomic_write(root / name, content)
        except BaseException:
            if custom.exists():
                shutil.rmtree(custom)
            (backup / "custom").rename(custom)
            for name, content in old.items():
                if content is None:
                    (root / name).unlink(missing_ok=True)
                else:
                    atomic_write(root / name, content)
            raise


def build(root):
    import fcntl

    folder = root / ".cache/duck-art"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(prefix="build-", dir=folder) as temp:
            stage = Path(temp)
            data, cache = compile_catalog(root, stage)
            outputs = generated_files(root, data)
            unchanged = all(
                (root / name).exists() and (root / name).read_bytes() == content
                for name, content in outputs.items()
            )
            if unchanged and (stage / "src/assets/custom").exists():
                unchanged = all(
                    (root / p.relative_to(stage)).is_file()
                    and (root / p.relative_to(stage)).read_bytes() == p.read_bytes()
                    for p in (stage / "src/assets/custom").rglob("*")
                    if p.is_file()
                )
            if not unchanged:
                commit(root, stage, outputs)
            return data, {
                "unchanged": unchanged,
                "cached": cache.hits,
                "processed": cache.misses,
            }


def check(root, extra=None):
    with tempfile.TemporaryDirectory(prefix="duck-art-check-") as temp:
        data, cache = compile_catalog(root, Path(temp), extra=extra)
        if not extra:
            for name, content in generated_files(root, data).items():
                require(
                    (root / name).is_file() and (root / name).read_bytes() == content,
                    f"Stale catalogue: {name}. Run duck-art build",
                )
            for path in (
                (Path(temp) / "src/assets/custom").rglob("*")
                if (Path(temp) / "src/assets/custom").exists()
                else []
            ):
                if path.is_file():
                    dest = root / path.relative_to(temp)
                    require(
                        dest.is_file() and dest.read_bytes() == path.read_bytes(),
                        f"Stale asset {dest}; run duck-art build",
                    )
        return data, cache


def new_pack(
    root,
    kind,
    key,
    label,
    *,
    base="vector",
    targets=None,
    template=None,
    hat="none",
    outfit="none",
):
    require(
        KEY.fullmatch(key) and key != "none",
        "key: lowercase ASCII letters, digits and hyphens; up to 48 characters",
    )
    data = builtins(root)
    # Use the compiled registry when it is available, including custom bases.
    if (root / "src/assets/custom/catalog.json").exists():
        data = read_json(root / "src/assets/custom/catalog.json")
    require(
        not any(entry["key"] == key for entry in data[kind + "s"]),
        f"Already exists {kind}: {key}",
    )
    target = root / "art/packs" / key
    require(not target.exists(), f"Directory already exists: {target}")
    spec = {"schemaVersion": 1, "kind": kind, "key": key, "label": label}
    if kind == "look":
        spec.update(hat=hat, outfit=outfit)
    identity(spec, target)
    (root / "art/packs").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="duck-art-new-") as temp:
        stage = Path(temp)
        if kind == "model":
            model = find_model(data, base)
            spec.update(
                base=base,
                wardrobeBase=model.get("wardrobeBase") or base,
                directory="model",
                geometry={},
            )
            source = root / "src" / model["root"]
            folder = stage / "model"
            folder.mkdir()
            if model["renderer"] == "flat":
                for name in model_parts(model["geometry"]):
                    shutil.copy2(source / (name + "." + model["format"]), folder)
            else:
                atomic_write(folder / "manifest.json", encoded(model["atlas"]))
                for part in model["atlas"]["parts"].values():
                    destination = folder / part["file"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / part["file"], destination)
        elif kind == "look":
            spec.update(hat=hat, outfit=outfit)
        else:
            entries = data[kind + "s"]
            template = template or ("wizard" if kind == "hat" else "sailor")
            entry = next((e for e in entries if e["key"] == template), None)
            require(entry is not None, f"Missing template {kind}: {template}")
            if kind == "outfit":
                spec["layer"] = entry["layer"]
            spec["variants"] = {}
            for model_key in targets or ["vector", "pixel"]:
                model = find_model(data, model_key)
                variant = resolve_variant(data, kind, template, model)
                require(
                    variant is not None,
                    f"Template {template} has no variant {model_key}",
                )
                folder = stage / model_key
                folder.mkdir()
                spec["variants"][model_key] = {
                    "directory": model_key,
                    "placement": copy.deepcopy(variant.get("placement", {})),
                }
                source = root / "src" / variant["root"]
                if model["renderer"] == "flat":
                    prefix = variant["prefix"]
                    sizes = clothing_parts(
                        kind,
                        prefix,
                        entry.get("layer"),
                        find_model(data, variant["model"])["geometry"],
                    )
                    for name in sizes:
                        new_name = (
                            name.replace("-" + prefix + "-", "-" + key + "-", 1)
                            + "."
                            + model["format"]
                        )
                        shutil.copy2(
                            source / (name + "." + model["format"]), folder / new_name
                        )
                else:
                    source_spec = (
                        variant.get("spec")
                        or find_model(data, variant["model"])["atlas"]["parts"][
                            variant["part"]
                        ]
                    )
                    part_key = kind + "." + key
                    metadata = copy.deepcopy(
                        find_model(data, variant["model"])["atlas"]
                    )
                    metadata["parts"] = {part_key: copy.deepcopy(source_spec)}
                    atomic_write(folder / "manifest.json", encoded(metadata))
                    destination = folder / source_spec["file"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / source_spec["file"], destination)
                    spec["variants"][model_key]["part"] = part_key
        atomic_write(stage / "pack.json", encoded(spec))
        # A new pack is validated together with the whole library before import.
        with tempfile.TemporaryDirectory(prefix="duck-art-new-check-") as verify:
            compile_catalog(root, Path(verify), extra=stage)
        shutil.copytree(stage, target)
    return target
