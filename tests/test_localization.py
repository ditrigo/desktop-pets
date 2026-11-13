import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalizationTests(unittest.TestCase):
    def test_catalog_keys_and_placeholders_match(self):
        english = json.loads((ROOT / "src/i18n/en.json").read_text())
        russian = json.loads((ROOT / "src/i18n/ru.json").read_text())
        self.assertEqual(english.keys(), russian.keys())
        for key, value in english.items():
            translated = russian[key]
            self.assertEqual(isinstance(value, str), isinstance(translated, str), key)
            values = [value] if isinstance(value, str) else list(value.values())
            translations = (
                [translated]
                if isinstance(translated, str)
                else list(translated.values())
            )
            expected = set(re.findall(r"%\d+", values[0]))
            for text in values + translations:
                self.assertTrue(text.strip(), key)
                self.assertEqual(set(re.findall(r"%\d+", text)), expected, key)

    def test_runtime_contains_no_hardcoded_russian_ui_strings(self):
        for path in [*(ROOT / "src").glob("*.qml"), *(ROOT / "src").glob("*.js")]:
            self.assertIsNone(re.search(r"[А-Яа-яЁё]", path.read_text()), path.name)

    def test_builtin_catalogue_has_fallback_labels_and_translation_keys(self):
        source = json.loads((ROOT / "art/catalog.json").read_text())
        english = json.loads((ROOT / "src/i18n/en.json").read_text())
        for group in ("models", "hats", "outfits", "looks"):
            for item in source[group]:
                self.assertIn(item["labelKey"], english)
                self.assertEqual(item["label"], english[item["labelKey"]])
