import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("duck_release", ROOT / "tools/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_unbuilt_personal_packs_cannot_leak_into_source_release(self):
        with tempfile.TemporaryDirectory(prefix="duck-private-pack-") as temp:
            root = Path(temp)
            catalog = root / "src/assets/custom/catalog.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text('{"packDigests": {}}')
            pack = root / "art/packs/private/pack.json"
            pack.parent.mkdir(parents=True)
            pack.write_text("{}")
            with self.assertRaisesRegex(ValueError, "personal art packs"):
                release.build(root, host=False)

    def test_archives_are_reproducible_clean_and_installable(self):
        with tempfile.TemporaryDirectory(prefix="duck-release-test-") as temp:
            first = release.build(ROOT, Path(temp) / "first", host=False)
            second = release.build(ROOT, Path(temp) / "second", host=False)
            self.assertEqual(first, second)
            for item in first["artifacts"]:
                one = Path(temp) / "first" / item["name"]
                two = Path(temp) / "second" / item["name"]
                self.assertEqual(one.read_bytes(), two.read_bytes())
                with tarfile.open(one) as archive:
                    names = archive.getnames()
                    self.assertIn("manifest.json", names)
                    self.assertIn("src/i18n/en.json", names)
                    self.assertIn("src/i18n/ru.json", names)
                    self.assertTrue(
                        all(
                            not m.issym() and not m.islnk()
                            for m in archive.getmembers()
                        )
                    )
                    self.assertFalse(
                        any(set(Path(n).parts) & release.OMIT for n in names)
                    )
                    manifest = json.load(archive.extractfile("manifest.json"))
                    for entry in manifest["entryPoints"].values():
                        self.assertIn(entry, names)
                    if "-source" in item["name"]:
                        self.assertIn("pet-art", names)
                        self.assertIn("uv.lock", names)
                        self.assertIn("tools/artlib.py", names)
                    else:
                        self.assertNotIn("tools/artlib.py", names)
                        self.assertNotIn("art/blender/desktop-duck.blend", names)
