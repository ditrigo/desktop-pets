#!/usr/bin/env python3
"""Render classic/pixel wardrobe and motion contact sheets through real QML."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--new-outfits", action="store_true")
args = parser.parse_args()
OUT = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
OUT.mkdir(parents=True, exist_ok=True)
cases = []
for palette, view, label in [
    ("yellow", "side", "Утёнок · профиль"),
    ("yellow", "threeQuarter", "Утёнок · ¾"),
    ("yellow", "front", "Утёнок · анфас"),
    ("mallard", "threeQuarter", "Кряква"),
    ("white", "threeQuarter", "Белая утка"),
    ("white", "front", "Белая · анфас"),
]:
    cases.append(dict(palette=palette, view=view, label=label))
for hat, outfit, label in [
    ("wizard", "cape", "Волшебник"),
    ("pirate", "sailor", "Пират"),
    ("santa", "scarf", "Новогодняя"),
    ("explorer", "scarf", "Исследователь"),
    ("chef", "none", "Повар"),
    ("crown", "cape", "Корона"),
]:
    cases.append(dict(hat=hat, outfit=outfit, label=label))
new_sets = [
    ("rainhat", "raincoat", "Под дождём"),
    ("detective", "trench", "Детектив"),
    ("beret", "apron", "Художник"),
    ("straw", "overalls", "Садовник"),
    ("tophat", "tuxedo", "Смокинг"),
    ("nightcap", "pajamas", "Пижама"),
]
for hat, outfit, label in new_sets:
    cases.append(dict(hat=hat, outfit=outfit, label=label))
for outfit, label in [
    ("scarf", "Шарф"),
    ("sailor", "Матроска"),
    ("space", "Космический"),
    ("cape", "Накидка"),
]:
    for view, suffix in [
        ("side", "профиль"),
        ("threeQuarter", "¾"),
        ("front", "анфас"),
    ]:
        cases.append(dict(outfit=outfit, view=view, label=label + " · " + suffix))
for mode, outfit, label in [
    ("walk", "sailor", "Шаг"),
    ("fly", "space", "Полёт"),
    ("sleep", "scarf", "Сон"),
    ("eat", "scarf", "Кормление"),
    ("preen", "cape", "Чистит пёрышки"),
    ("drag", "scarf", "Перенос"),
]:
    cases.append(dict(mode=mode, hat="wizard", outfit=outfit, label=label))
if args.new_outfits:
    cases = []
    for view, suffix in [
        ("side", "профиль"),
        ("threeQuarter", "¾"),
        ("front", "анфас"),
    ]:
        for hat, outfit, label in new_sets:
            cases.append(
                dict(hat=hat, outfit=outfit, view=view, label=label + " · " + suffix)
            )
    for (hat, outfit, label), mode in zip(
        new_sets, ["walk", "preen", "wave", "fly", "drag", "sleep"]
    ):
        cases.append(
            dict(hat=hat, outfit=outfit, mode=mode, label=label + " · " + mode)
        )
QML = """import QtQuick
import Quickshell
ShellRoot {
 FloatingWindow {visible:true;implicitWidth:1080;implicitHeight:SHEET_HEIGHT;color:"#202a36"
 Rectangle {id:sheet;anchors.fill:parent;color:"#202a36"
 Text{x:22;y:18;text:TITLE;textFormat:Text.PlainText;color:"#f4e8ce";font.pixelSize:25;font.bold:true}
 Repeater{model:CASES
 delegate:Item {required property var modelData;required property int index;x:(index%6)*180;y:65+Math.floor(index/6)*192;width:180;height:185
 PetSprite{x:9;y:0;width:162;height:151.2;artStyle:STYLE;plumage:parent.modelData.palette||"yellow";view:parent.modelData.view||"threeQuarter";hat:parent.modelData.hat||"none";outfit:parent.modelData.outfit||"none";mode:parent.modelData.mode||"idle";clock:.17;stride:.8;modeTime:.4;}
 Text{anchors.horizontalCenter:parent.horizontalCenter;y:160;text:parent.modelData.label;textFormat:Text.PlainText;color:"#e5d7ba";font.pixelSize:13}
 }
 }
 }
 Timer{interval:1500;running:true;onTriggered:sheet.grabToImage(function(result){if(!result.saveToFile(OUTPUT))console.error("ASSERT save");Qt.quit()})}
 }
 Timer{interval:10000;running:true;onTriggered:{console.error("ASSERT timeout");Qt.quit()}}
}
"""
with tempfile.TemporaryDirectory(prefix="duck-flat-preview-") as temp:
    p = Path(temp)
    for file in (ROOT / "src").iterdir():
        if file.suffix in (".qml", ".js"):
            (p / file.name).symlink_to(file)
    (p / "assets").symlink_to(ROOT / "src/assets")
    for style, title, file in [
        ("vector", "КЛАССИЧЕСКАЯ · ГАРДЕРОБ И ПОЗЫ", "classic.png"),
        ("pixel", "ПИКСЕЛЬНАЯ · ГАРДЕРОБ И ПОЗЫ", "pixel.png"),
        ("voxel", "ВОКСЕЛЬНАЯ · ГАРДЕРОБ И ПОЗЫ", "voxel.png"),
    ]:
        if args.new_outfits and style == "voxel":
            continue
        file = ("new-outfits-" if args.new_outfits else "") + file
        style_cases = [
            case
            for case in cases
            if style != "voxel"
            or case.get("outfit")
            not in ["raincoat", "trench", "apron", "overalls", "tuxedo", "pajamas"]
        ]
        source = (
            QML.replace("SHEET_HEIGHT", str(65 + ((len(style_cases) + 5) // 6) * 192))
            .replace("TITLE", json.dumps(title))
            .replace("CASES", json.dumps(style_cases))
            .replace("STYLE", json.dumps(style))
            .replace("OUTPUT", json.dumps(str(OUT / file)))
        )
        (p / "shell.qml").write_text(source)
        result = subprocess.run(
            ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
            env=dict(
                os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"
            ),
            text=True,
            capture_output=True,
            timeout=15,
        )
        log = result.stdout + result.stderr
        (OUT / (style + "-preview.log")).write_text(log)
        assert result.returncode == 0 and not any(
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
        print(OUT / file)
