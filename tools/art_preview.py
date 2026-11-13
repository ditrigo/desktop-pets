"""Review exactly the QML renderer used by the desktop pet."""

import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

from artlib import find_model, require

QML = """import QtQuick
import Quickshell
import "DuckHit.js" as Hit
import "DuckCatalog.js" as Catalog
ShellRoot {
 FloatingWindow {visible:true;implicitWidth:1080;implicitHeight:HEIGHT;color:"#202a36"
 Rectangle {id:sheet;anchors.fill:parent;color:"#202a36"
 Text{x:20;y:15;text:TITLE;textFormat:Text.PlainText;color:"#f4e8ce";font.pixelSize:24;font.bold:true}
 Repeater {model:CASES
 delegate:Item {id:cell;required property var modelData;required property int index
 x:index%6*180;y:60+Math.floor(index/6)*182;width:180;height:182
 DuckSprite {id:bird;x:9;y:0;width:162;height:151.2;artStyle:cell.modelData.model;hat:cell.modelData.hat;outfit:cell.modelData.outfit;plumage:cell.modelData.palette;view:cell.modelData.view;mode:cell.modelData.mode;clock:.17;stride:.8;modeTime:.4;direction:cell.modelData.direction;}
 property var bands:[]
 Repeater {model:cell.bands;delegate:Rectangle {required property var modelData;x:modelData.x;y:modelData.y;width:modelData.width;height:modelData.height;color:"#e88a91";opacity:.15;}}
 Timer{interval:200;running:GUIDES;onTriggered:cell.bands=Hit.bands(bird.inputPolygons(cell),2);}
 Text{y:155;width:180;text:cell.modelData.label;textFormat:Text.PlainText;horizontalAlignment:Text.AlignHCenter;color:"#e5d7ba";font.pixelSize:11}
 }}
 }
 Timer {interval:1400;running:true;onTriggered:sheet.grabToImage(function(result){if(!result.saveToFile(OUTPUT))console.error("ASSERT preview save");if(!LIVE)Qt.quit();})}
 }
 Timer{interval:20000;running:!LIVE;onTriggered:{console.error("ASSERT preview timeout");Qt.quit();}}
}
"""


def render(root, data, key, kind, output, *, targets=None, guides=False, live=False):
    if kind == "model":
        chosen = [find_model(data, key)]
        label = chosen[0]["label"]
        hat = outfit = "none"
    else:
        group = "looks" if kind == "look" else kind + "s"
        entry = next((item for item in data[group] if item["key"] == key), None)
        require(entry is not None, f"Missing {kind}: {key}")
        label = entry["label"]
        chosen = [m for m in data["models"] if m["key"] in entry["models"]]
        hat = entry.get("hat", key if kind == "hat" else "none")
        outfit = entry.get("outfit", key if kind == "outfit" else "none")
    if targets:
        chosen = [m for m in chosen if m["key"] in targets]
        require(
            {m["key"] for m in chosen} == set(targets),
            "A selected model is incompatible with this asset",
        )
    require(chosen, "No compatible models to preview")
    cases = []
    for mode in ["idle", "walk", "sleep", "eat", "fly", "drag"]:
        for model in chosen:
            for index, view in enumerate(["side", "threeQuarter", "front"]):
                cases.append(
                    dict(
                        model=model["key"],
                        hat=hat,
                        outfit=outfit,
                        palette=["yellow", "mallard", "white"][index],
                        view=view,
                        mode=mode,
                        direction=-1 if mode == "walk" else 1,
                        label=model["label"] + " · " + view + " · " + mode,
                    )
                )
    require(
        len(cases) <= 180,
        "Use --models for large libraries: up to ten models per sheet",
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="duck-art-preview-") as temp:
        folder = Path(temp)
        for file in (root / "src").iterdir():
            if file.suffix in (".qml", ".js"):
                (folder / file.name).symlink_to(file)
        (folder / "assets").symlink_to(root / "src/assets")
        replacements = {
            "HEIGHT": 60 + ((len(cases) + 5) // 6) * 182,
            "TITLE": label + " · preview",
            "CASES": cases,
            "GUIDES": guides,
            "OUTPUT": str(output),
            "LIVE": live,
        }
        text = re.sub(
            r"\b(" + "|".join(replacements) + r")\b",
            lambda match: json.dumps(replacements[match[0]], ensure_ascii=False),
            QML,
        )
        (folder / "shell.qml").write_text(text)
        environment = dict(os.environ)
        if not live:
            environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        process = subprocess.run(
            ["quickshell", "-p", str(folder / "shell.qml"), "--no-color"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=None if live else 25,
        )
        log = process.stdout + process.stderr
        output.with_suffix(".log").write_text(log)
        require(
            process.returncode == 0
            and output.is_file()
            and not any(
                term in log
                for term in [
                    "ASSERT",
                    "TypeError",
                    "ReferenceError",
                    "Cannot open",
                    "ERROR",
                    "Binding loop",
                ]
            ),
            "QML preview failed: " + log[-2000:],
        )
    return output
