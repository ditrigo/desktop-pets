#!/usr/bin/env python3
"""Review the same transformed contours used by reactions and the window mask."""

from pathlib import Path
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
OUT.mkdir(parents=True, exist_ok=True)
QML = """import QtQuick
import Quickshell
import "DuckHit.js" as Hit
ShellRoot{
 FloatingWindow{visible:true;implicitWidth:1080;implicitHeight:570;color:"#202a36"
 Rectangle{id:sheet;anchors.fill:parent;color:"#202a36"
 Repeater{model:18;delegate:Item{required property int index;x:index%6*180;y:Math.floor(index/6)*190;width:180;height:190
 DuckSprite{id:bird;x:20;y:12;width:140;height:131;artStyle:["vector","pixel","voxel"][Math.floor(parent.index/6)];view:["side","threeQuarter","front"][parent.index%3];hat:parent.index%2?"wizard":"chef";outfit:"scarf";mode:parent.index%6>=3?"fly":"idle";clock:.17;modeTime:.4;animate:true;direction:parent.index%2?-1:1;}
 property var bands:[]
 Timer{interval:100;running:true;onTriggered:parent.bands=Hit.bands(bird.inputPolygons(parent),2);}
 Repeater{model:parent.bands;delegate:Rectangle{required property var modelData;x:modelData.x;y:modelData.y;width:modelData.width;height:modelData.height;color:"#e98174";opacity:.3;}}
 Text{y:157;anchors.horizontalCenter:parent.horizontalCenter;text:bird.artStyle+" · "+bird.view;color:"white";font.pixelSize:11;}
 }}
 }
 Timer{interval:500;running:true;onTriggered:sheet.grabToImage(function(r){r.saveToFile(OUTPUT);Qt.quit();})}
 }
}"""
with tempfile.TemporaryDirectory(prefix="duck-mask-sheet-") as tmp:
    p = Path(tmp)
    for f in (ROOT / "src").iterdir():
        if f.suffix in [".qml", ".js"]:
            (p / f.name).symlink_to(f)
    (p / "assets").symlink_to(ROOT / "src/assets")
    (p / "shell.qml").write_text(
        QML.replace("OUTPUT", json.dumps(str(OUT / "silhouettes.png")))
    )
    result = subprocess.run(
        ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"),
        capture_output=True,
        text=True,
        timeout=10,
    )
    log = result.stdout + result.stderr
    (OUT / "silhouettes.log").write_text(log)
    assert result.returncode == 0 and not any(
        s in log for s in ["ERROR", "TypeError", "ReferenceError"]
    ), log
    print(OUT / "silhouettes.png")
