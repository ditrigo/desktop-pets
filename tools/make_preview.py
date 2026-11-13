#!/usr/bin/env python3
"""Render the public preview from bundled art without capturing the desktop."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
QML = """import QtQuick
import Quickshell
ShellRoot {
 FloatingWindow {visible:true;implicitWidth:1080;implicitHeight:730;color:"#202a36"
 Rectangle{id:sheet;anchors.fill:parent;color:"#202a36"
 Text{x:36;y:26;text:"Desktop Pets";textFormat:Text.PlainText;color:"#f4e8ce";font.pixelSize:36;font.bold:true}
 Text{x:37;y:79;text:"A little company for your Omarchy desktop";textFormat:Text.PlainText;color:"#b6c1ce";font.pixelSize:19}
 Repeater{model:[{key:"vector",label:"CLASSIC"},{key:"pixel",label:"PIXEL"},{key:"voxel",label:"VOXEL"}]
 delegate:Item{required property var modelData;required property int index;x:index*360;y:123;width:360;height:276
 PetSprite{x:45;y:0;width:270;height:252;artStyle:parent.modelData.key;view:"threeQuarter";animate:false;}
 Text{y:258;width:360;text:parent.modelData.label;textFormat:Text.PlainText;color:"#e5d7ba";font.pixelSize:16;horizontalAlignment:Text.AlignHCenter}
 }}
 Text{x:37;y:431;text:"Mix, match and play";textFormat:Text.PlainText;color:"#f4e8ce";font.pixelSize:24;font.bold:true}
 Repeater{model:[{hat:"santa",outfit:"scarf",label:"Winter"},{hat:"beret",outfit:"apron",label:"Artist"},{hat:"rainhat",outfit:"raincoat",label:"Rainy day"},{hat:"straw",outfit:"overalls",label:"Gardener"},{hat:"tophat",outfit:"tuxedo",label:"Tuxedo"},{hat:"nightcap",outfit:"pajamas",label:"Bedtime"}]
 delegate:Item{required property var modelData;required property int index;x:index*180;y:479;width:180;height:200
 PetSprite{x:9;y:0;width:162;height:151.2;artStyle:parent.index%2?"pixel":"vector";hat:parent.modelData.hat;outfit:parent.modelData.outfit;view:"threeQuarter";animate:false;}
 Text{y:165;width:180;text:parent.modelData.label;textFormat:Text.PlainText;color:"#e5d7ba";font.pixelSize:14;horizontalAlignment:Text.AlignHCenter}
 }}
 Text{x:37;y:690;text:"EN / RU   ·   Window walks   ·   Toys & petting   ·   Custom models and clothes";textFormat:Text.PlainText;color:"#b6c1ce";font.pixelSize:14}
 }
 Timer{interval:1400;running:true;onTriggered:sheet.grabToImage(function(result){if(!result.saveToFile(OUTPUT))console.error("ASSERT preview");Qt.quit();})}
 }
}
"""


def main():
    with tempfile.TemporaryDirectory(prefix="duck-public-preview-") as temp:
        folder = Path(temp)
        for path in (ROOT / "src").iterdir():
            if path.suffix in (".qml", ".js"):
                (folder / path.name).symlink_to(path)
        (folder / "assets").symlink_to(ROOT / "src/assets")
        (folder / "shell.qml").write_text(
            QML.replace("OUTPUT", json.dumps(str(ROOT / "preview.png")))
        )
        process = subprocess.run(
            ["quickshell", "-p", str(folder / "shell.qml"), "--no-color"],
            env=dict(
                os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"
            ),
            capture_output=True,
            text=True,
            timeout=15,
        )
        log = process.stdout + process.stderr
        assert process.returncode == 0 and not any(
            term in log
            for term in (
                "ASSERT",
                "TypeError",
                "ReferenceError",
                "Cannot open",
                "ERROR",
            )
        ), log
    print(ROOT / "preview.png")


if __name__ == "__main__":
    main()
