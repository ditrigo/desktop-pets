"""Authoring regressions use isolated libraries and the real QML renderer."""

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import artlib as lib  # noqa: E402 - import from the working tree
import pet_art  # noqa: E402 - import from the working tree


class ArtToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pet-art-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in (ROOT / "src").iterdir():
            if path.is_file():
                shutil.copy2(path, self.root / path.name)
        for folder in ["src", "tools"]:
            shutil.copytree(
                ROOT / folder,
                self.root / folder,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        (self.root / "art/packs").mkdir(parents=True)
        shutil.copy2(ROOT / "art/catalog.json", self.root / "art/catalog.json")
        cached = ROOT / ".cache/pet-art/hulls"
        if cached.exists():
            shutil.copytree(cached, self.root / ".cache/pet-art/hulls")
        lib.build(self.root)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return pet_art.main(["--root", str(self.root), *map(str, args)])

    def custom(self, kind="hat", key="test-cap", **options):
        path = lib.new_pack(self.root, kind, key, "Мой " + key, **options)
        lib.build(self.root)
        return path

    def outputs(self):
        return {
            name: (self.root / name).read_bytes()
            for name in [
                "src/PetCatalog.js",
                "src/PetLooks.js",
                "src/PetModel.js",
                "src/assets/custom/catalog.json",
            ]
        }

    def test_model_clothes_and_look_are_registered_without_manual_js_edits(self):
        self.custom("model", "sunbird", base="vector")
        self.custom("hat", "sun-cap", targets=["vector", "pixel", "sunbird", "voxel"])
        self.custom("outfit", "sun-coat", targets=["sunbird", "pixel", "voxel"])
        self.custom("look", "sun-look", hat="sun-cap", outfit="sun-coat")
        data, cache = lib.check(self.root)
        self.assertEqual(
            next(x for x in data["looks"] if x["key"] == "sun-look")["models"],
            ["pixel", "voxel", "sunbird"],
        )
        self.assertIn("sunbird", (self.root / "src/PetModel.js").read_text())
        self.assertIn("sun-look", (self.root / "src/PetLooks.js").read_text())
        self.assertEqual(cache.misses, 0)

    def test_unchanged_build_uses_cache_and_keeps_generated_mtimes(self):
        self.custom()
        paths = [self.root / name for name in self.outputs()]
        stamps = [p.stat().st_mtime_ns for p in paths]
        data, stats = lib.build(self.root)
        self.assertTrue(stats["unchanged"])
        self.assertEqual(stats["processed"], 0)
        self.assertGreater(stats["cached"], 400)
        self.assertEqual(stamps, [p.stat().st_mtime_ns for p in paths])

    def test_missing_generated_resource_is_repaired_from_source(self):
        self.custom()
        data = lib.read_json(self.root / "src/assets/custom/catalog.json")
        variant = next(x for x in data["hats"] if x["key"] == "test-cap")["variants"][
            "pixel"
        ]
        path = self.root / "src" / variant["root"] / "hat-test-cap-side.png"
        before = path.read_bytes()
        path.unlink()
        _, stats = lib.build(self.root)
        self.assertFalse(stats["unchanged"])
        self.assertEqual(before, path.read_bytes())

    def test_invalid_asset_preserves_the_last_working_catalogue(self):
        path = self.custom()
        before = self.outputs()
        (path / "pixel/hat-test-cap-side.png").unlink()
        with self.assertRaisesRegex(lib.ArtError, "Missing asset"):
            lib.build(self.root)
        self.assertEqual(before, self.outputs())

    def test_failed_commit_rolls_back_all_generated_files_and_assets(self):
        self.custom()
        before = self.outputs()
        path = self.root / "art/packs/test-cap/pack.json"
        spec = lib.read_json(path)
        spec["label"] = "Другое имя"
        lib.atomic_write(path, lib.encoded(spec))
        original = lib.atomic_write
        failed = False

        def fail_once(path, contents):
            nonlocal failed
            if path == self.root / "src/PetLooks.js" and not failed:
                failed = True
                raise OSError("simulated filesystem failure")
            return original(path, contents)

        with patch.object(lib, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated"):
                lib.build(self.root)
        self.assertEqual(before, self.outputs())
        data = lib.read_json(self.root / "src/assets/custom/catalog.json")
        variant = next(x for x in data["hats"] if x["key"] == "test-cap")["variants"][
            "vector"
        ]
        self.assertTrue(
            (self.root / "src" / variant["root"] / "hat-test-cap-front.svg").exists()
        )

    def test_png_alpha_and_svg_resource_loads_are_validated(self):
        path = self.custom()
        png = path / "pixel/hat-test-cap-side.png"
        image = Image.open(png).copy()
        image.putpixel((10, 10), (255, 0, 0, 128))
        image.save(png)
        with self.assertRaisesRegex(lib.ArtError, "alpha"):
            lib.build(self.root)
        shutil.copy2(ROOT / "src/assets/duck2d/pixel/hat-wizard-side.png", png)
        svg = path / "vector/hat-test-cap-side.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><image href="https://example.invalid/pixel"/></svg>'
        )
        with self.assertRaisesRegex(lib.ArtError, "unsupported SVG element"):
            lib.build(self.root)

    def test_paths_symlinks_and_zip_traversal_are_rejected(self):
        path = self.custom()
        spec = lib.read_json(path / "pack.json")
        spec["variants"]["vector"]["directory"] = "../../.."
        lib.atomic_write(path / "pack.json", lib.encoded(spec))
        with self.assertRaisesRegex(lib.ArtError, "Path escapes pack"):
            lib.build(self.root)
        spec["variants"]["vector"]["directory"] = "vector"
        lib.atomic_write(path / "pack.json", lib.encoded(spec))
        (path / "link.svg").symlink_to(
            ROOT / "src/assets/duck2d/vector/hat-wizard-side.svg"
        )
        with self.assertRaisesRegex(lib.ArtError, "Symlink"):
            lib.build(self.root)
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as file:
            file.writestr("../escaped", "bad")
        with self.assertRaisesRegex(lib.ArtError, "escapes"):
            pet_art.unpack(archive, self.root / "extract")
        self.assertFalse((self.root / "escaped").exists())

    def test_export_import_and_remove_preserve_editable_sources(self):
        self.custom()
        archive = self.root / "cap.zip"
        self.cli("export", "test-cap", "--output", archive)
        self.cli("remove", "test-cap")
        self.assertFalse((self.root / "art/packs/test-cap").exists())
        self.cli("import", archive)
        lib.check(self.root)
        self.assertTrue(
            (self.root / "art/packs/test-cap/pixel/hat-test-cap-side.png").exists()
        )

    def test_referenced_model_cannot_be_removed_and_is_restored(self):
        self.custom("model", "sunbird")
        self.custom("hat", "sun-cap", targets=["sunbird"])
        before = self.outputs()
        with self.assertRaisesRegex(lib.ArtError, "Unknown model"):
            self.cli("remove", "sunbird")
        self.assertTrue((self.root / "art/packs/sunbird").is_dir())
        self.assertEqual(before, self.outputs())

    def test_invalid_fit_does_not_change_source_or_generated_output(self):
        path = self.custom()
        before = (path / "pack.json").read_bytes()
        outputs = self.outputs()
        with self.assertRaisesRegex(lib.ArtError, "rectangle"):
            self.cli(
                "fit",
                "test-cap",
                "--model",
                "pixel",
                "--part",
                "hat",
                "--rect",
                -30,
                -64,
                -2,
                32,
            )
        self.assertEqual(before, (path / "pack.json").read_bytes())
        self.assertEqual(outputs, self.outputs())

    def test_extra_blender_collections_are_registered_with_their_own_assets(self):
        path = self.custom("model", "blockbird", base="voxel")
        manifest = lib.read_json(path / "model/manifest.json")
        manifest["parts"]["hat.safety"] = dict(manifest["parts"]["hat.explorer"])
        manifest["labels"] = {"hat.safety": "Каска"}
        lib.atomic_write(path / "model/manifest.json", lib.encoded(manifest))
        data, _ = lib.build(self.root)
        hat = next(item for item in data["hats"] if item["key"] == "safety")
        self.assertEqual(hat["label"], "Каска")
        self.assertEqual(hat["models"], ["blockbird"])
        self.assertEqual(hat["variants"]["blockbird"]["part"], "hat.safety")
        wizard = next(item for item in data["hats"] if item["key"] == "wizard")
        self.assertEqual(wizard["variants"]["blockbird"]["model"], "blockbird")

    @unittest.skipUnless(
        shutil.which("quickshell") and Path("/usr/lib/qt6/bin/qmltestrunner").exists(),
        "Quickshell and Qt Test are required",
    )
    def test_real_renderer_loads_custom_models_clothes_and_moved_input_hulls(self):
        self.custom("model", "sunbird")
        self.custom("model", "blockbird", base="voxel")
        self.custom(
            "hat", "sun-cap", targets=["sunbird", "pixel", "voxel", "blockbird"]
        )
        self.custom(
            "outfit", "sun-coat", targets=["sunbird", "pixel", "voxel", "blockbird"]
        )
        self.cli(
            "fit",
            "sun-cap",
            "--model",
            "sunbird",
            "--part",
            "hat",
            "--rect",
            -26,
            -64,
            72,
            36,
        )
        test = self.root / "src/tst_custom.qml"
        test.write_text("""import QtQuick
import QtTest
import "." as Pet
import "PetModel.js" as Model
import "PetLooks.js" as Looks
import "PetCatalog.js" as Catalog
Rectangle {width:240;height:224;color:"#202a36"
 Pet.PetSprite{id:bird;width:240;height:224;hat:"sun-cap";outfit:"sun-coat";artStyle:"sunbird";}
 TestCase {name:"CustomAssets";when:windowShown
 function test_settings_and_all_renderers(){
  for(var key of ["sunbird","pixel","voxel","blockbird"]){
   bird.artStyle=key;wait(45);var cfg=Model.settings({artStyle:key,hat:"sun-cap",outfit:"sun-coat"});
   compare(cfg.artStyle,key);compare(cfg.hat,"sun-cap");compare(cfg.outfit,"sun-coat");
   verify(Looks.available(Looks.hats,key).some(function(h){return h.key==="sun-cap";}));
   for(var view of ["side","threeQuarter","front"])for(var mode of ["idle","walk","sleep","eat","fly","drag"]){
    bird.view=view;bird.mode=mode;bird.clock=.17;bird.modeTime=.4;wait(16);
    verify(bird.inputPolygons(bird).length>0);var image=grabImage(bird);verify(image.width>0);
   }
  }
 }
 function test_custom_fit_moves_art_and_input_together(){
  bird.artStyle="sunbird";bird.mode="idle";bird.view="side";wait(40);
  var cap=findChild(bird,"flat-hat");verify(cap);compare(cap.x,-26);compare(cap.y,-64);compare(cap.width,72);compare(cap.height,36);
  var point=cap.mapToItem(bird,36,25);compare(bird.hitRegion(point.x,point.y),"head");
 }
 }}""")
        result = subprocess.run(
            ["/usr/lib/qt6/bin/qmltestrunner", "-input", str(test)],
            env=dict(
                os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"
            ),
            capture_output=True,
            text=True,
            timeout=30,
        )
        log = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, log)
        for error in [
            "TypeError",
            "ReferenceError",
            "Cannot open",
            "FAIL!",
            "Binding loop",
        ]:
            self.assertNotIn(error, log)

    @unittest.skipUnless(shutil.which("quickshell"), "Quickshell is required")
    def test_preview_handles_markup_and_template_words_as_plain_labels(self):
        path = self.custom()
        spec = lib.read_json(path / "pack.json")
        spec["label"] = "TITLE CASES OUTPUT <b>мой</b>"
        lib.atomic_write(path / "pack.json", lib.encoded(spec))
        target = self.root / "preview.png"
        self.cli("preview", "test-cap", "--models", "pixel", "--output", target)
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
