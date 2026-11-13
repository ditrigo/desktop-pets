#!/usr/bin/env python3
"""Verify catalog parity and live language changes without touching user config."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from check_settings import QML
from qml_support import ROOT, dependencies


def validate_catalogs():
    catalogs = {
        code: json.loads((ROOT / "src/i18n" / (code + ".json")).read_text())
        for code in ("en", "ru")
    }
    assert catalogs["en"].keys() == catalogs["ru"].keys(), "Translation keys differ"
    for key, english in catalogs["en"].items():
        russian = catalogs["ru"][key]
        assert isinstance(english, str) == isinstance(russian, str), key
        values = [english] if isinstance(english, str) else list(english.values())
        translated = [russian] if isinstance(russian, str) else list(russian.values())
        expected = set(re.findall(r"%\d+", values[0]))
        assert all(
            set(re.findall(r"%\d+", value)) == expected for value in values + translated
        ), key
        assert all(value.strip() for value in values + translated), key
    for path in (ROOT / "src").glob("*.qml"):
        for key in re.findall(r'strings\.(?:t|tn|format)\("([^"]+)"', path.read_text()):
            assert key in catalogs["en"] or key.endswith("."), (path.name, key)
    source = json.loads((ROOT / "art/catalog.json").read_text())
    for group in ("models", "hats", "outfits", "looks"):
        for item in source[group]:
            assert item["labelKey"] in catalogs["en"], item["key"]
    print("CATALOGS OK", len(catalogs["en"]), "keys, English and Russian")


def live_test():
    out = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
    out.mkdir(parents=True, exist_ok=True)
    source = QML.replace('mood:"Вам доверяет"', 'mood:"trusting"')
    start = source.index(" Timer{interval:200;")
    source = (
        source[:start]
        + """
 FileView{id:languageFile;path:Qt.resolvedUrl("language").toString().replace(/^file:\\/\\//,"");}
 PetTranslations{id:strings;}
 PetSettingsStore{id:errorStore;}
 Timer{interval:250;running:true;repeat:true;onTriggered:{
  if(test.busy)return;
  var items=test.descendants(settings,[]);
  function has(value){return items.some(function(item){return item.text===value;});}
  if(test.stage===0){
   test.check(has("Appearance")&&has("Behavior")&&has("Wizard"),"English UI and built-in clothes");
   test.check(strings.tn("rest.remaining",1).arg(1)==="Resting · 1 minute left","English singular");
   test.check(strings.tn("rest.remaining",2).arg(2)==="Resting · 2 minutes left","English plural");
   errorStore.apply({hat:"wizard"});test.check(errorStore.error==="Settings are currently unavailable","English error");
   test.capture("appearance-en");
  }else if(test.stage===1){languageFile.setText("ru\\n");test.stage++;
  }else if(test.stage===2&&strings.language==="ru"){
   test.check(has("Внешность")&&has("Поведение")&&has("Волшебник"),"Russian UI updates in place");
   test.check(strings.tn("rest.remaining",2).arg(2)==="Отдых ещё 2 минуты","Russian few form");
   test.check(strings.tn("rest.remaining",5).arg(5)==="Отдых ещё 5 минут","Russian many form");
   test.check(errorStore.error==="Настройки сейчас недоступны","Existing error updates in place");
   test.capture("appearance-ru");
  }else if(test.stage===3){languageFile.setText("de\\n");test.stage++;
  }else if(test.stage===4&&strings.language==="de"){
   test.check(has("Appearance")&&has("Wizard"),"Missing locale falls back to English");
   test.check(host.config.artStyle==="pixel"&&host.config.hat==="chef","Language change preserves settings");
   console.log("RESULT "+JSON.stringify({checks:test.checks,failed:test.failed}));Qt.quit();
  }
 }}
 Timer{interval:10000;running:true;onTriggered:{console.error("ASSERT i18n timeout "+test.stage);Qt.quit();}}
}
"""
    )
    source = source.replace(
        "import Quickshell\n", "import Quickshell\nimport Quickshell.Io\n", 1
    )
    with tempfile.TemporaryDirectory(prefix="duck-i18n-") as temp:
        folder = Path(temp)
        dependencies(folder, language=None)
        for path in (ROOT / "src").iterdir():
            if path.suffix in (".qml", ".js"):
                (folder / path.name).symlink_to(path)
        (folder / "assets").symlink_to(ROOT / "src/assets")
        (folder / "language").write_text("en\n")
        (folder / "shell.qml").write_text(
            source.replace("OUTPUT", json.dumps(str(out)))
        )
        env = dict(
            os.environ,
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            OMARCHY_LANGUAGE_FILE=str(folder / "language"),
        )
        result = subprocess.run(
            ["quickshell", "-p", str(folder / "shell.qml"), "--no-color"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        log = result.stdout + result.stderr
        (out / "i18n-tests.log").write_text(log)
        values = [
            json.loads(line.split("RESULT ", 1)[1])
            for line in log.splitlines()
            if "RESULT " in line
        ]
        assert result.returncode == 0 and values and values[-1]["failed"] == 0, log
        assert not any(
            term in log
            for term in (
                "ASSERT",
                "TypeError",
                "ReferenceError",
                "Cannot open",
                "ERROR",
                "Binding loop",
            )
        ), log
        print("LIVE I18N OK", values[-1])


if __name__ == "__main__":
    validate_catalogs()
    live_test()
