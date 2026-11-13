#!/usr/bin/env python3
"""Prove that incomplete/incompatible packages fail before installation."""

import json
import shutil
import tempfile
from pathlib import Path
from check_assets import ROOT, validate

with tempfile.TemporaryDirectory(prefix="duck-corrupt-assets-") as tmp:
    p = Path(tmp)
    (p / "src").mkdir()
    shutil.copytree(ROOT / "src/assets", p / "src/assets")
    for name in ["PetGeometry.js", "PetAtlas.js"]:
        shutil.copy2(ROOT / "src" / name, p / "src" / name)
    path = p / "src/assets/duck3d/manifest.json"
    original = path.read_text()
    js = (p / "src/PetAtlas.js").read_text()

    def reject(label):
        try:
            validate(p)
        except (AssertionError, FileNotFoundError):
            print("REJECTED", label)
            return
        raise AssertionError("accepted " + label)

    m = json.loads(original)
    m["contractVersion"] = 99
    path.write_text(json.dumps(m))
    reject("incompatible ABI")
    path.write_text(original)
    m = json.loads(original)
    m["parts"]["yellow-head"]["frames"] -= 1
    path.write_text(json.dumps(m))
    (p / "src/PetAtlas.js").write_text("var data = " + json.dumps(m) + ";")
    reject("missing pose frame")
    path.write_text(original)
    (p / "src/PetAtlas.js").write_text(js)
    (p / "src/assets/duck2d/pixel/foot.png").unlink()
    reject("missing flat resource")
