#!/usr/bin/env python3
"""Real compositor routing into a dedicated window under a masked sprite."""

import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = """import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
ShellRoot {id:probeRoot;
 property int under:0
 property int duck:0
 PanelWindow {id:bottom;anchors{left:true;top:true;}margins{left:100;top:100;}implicitWidth:400;implicitHeight:300;color:"#243240";exclusionMode:ExclusionMode.Ignore;WlrLayershell.layer:WlrLayer.Top;WlrLayershell.namespace:"duck-click-test-under"
 Text{anchors.centerIn:parent;text:"Desktop Duck · click routing test";color:"white"}
 MouseArea{anchors.fill:parent;onClicked:probeRoot.under++;}
 }
 PanelWindow {id:top;anchors{left:true;top:true;}margins{left:100;top:100;}implicitWidth:400;implicitHeight:300;color:"transparent";exclusionMode:ExclusionMode.Ignore;WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.namespace:"duck-click-test"
 mask:DuckSilhouette{id:shape;birdSprite:bird;target:top.contentItem;}
 DuckSprite{id:bird;x:100;y:60;width:200;height:186.67;artStyle:"pixel";hat:"wizard";view:"front";animate:false;}
 MouseArea{anchors.fill:parent;onClicked:probeRoot.duck++;}
 Timer{interval:100;running:true;onTriggered:shape.update();}
 }
 IpcHandler{target:"probe";function counts():string{return JSON.stringify({under:probeRoot.under,duck:probeRoot.duck});}}
}
"""


def run():
    out = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="duck-routing-") as tmp:
        p = Path(tmp)
        xml = ROOT / "integration/protocols/duck-virtual-pointer.xml"
        subprocess.run(
            ["wayland-scanner", "client-header", str(xml), str(p / "pointer.h")],
            check=True,
        )
        subprocess.run(
            ["wayland-scanner", "private-code", str(xml), str(p / "pointer.c")],
            check=True,
        )
        flags = subprocess.check_output(
            ["pkg-config", "--cflags", "--libs", "wayland-client"], text=True
        ).split()
        subprocess.run(
            [
                "gcc",
                "-I",
                str(p),
                str(ROOT / "integration/pointer.c"),
                str(p / "pointer.c"),
                "-o",
                str(p / "pointer"),
                *flags,
            ],
            check=True,
        )
        for f in (ROOT / "src").iterdir():
            if f.suffix in (".qml", ".js"):
                (p / f.name).symlink_to(f)
        (p / "assets").symlink_to(ROOT / "src/assets")
        (p / "shell.qml").write_text(QML)
        with (out / "routing.log").open("w") as log:
            proc = subprocess.Popen(
                ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
                stdout=log,
                stderr=log,
            )
            try:
                time.sleep(1)
                monitors = json.loads(
                    subprocess.check_output(["hyprctl", "-j", "monitors"], text=True)
                )
                w = max(m["x"] + m["width"] / m["scale"] for m in monitors)
                h = max(m["y"] + m["height"] / m["scale"] for m in monitors) - min(
                    m["y"] for m in monitors
                )
                for x, y in [(201, 161), (300, 225)]:
                    subprocess.run(
                        [
                            str(p / "pointer"),
                            str(x),
                            str(y),
                            str(int(w)),
                            str(int(h)),
                            "click",
                        ],
                        check=True,
                    )
                    time.sleep(0.15)
                r = subprocess.check_output(
                    [
                        "quickshell",
                        "-p",
                        str(p / "shell.qml"),
                        "ipc",
                        "call",
                        "probe",
                        "counts",
                    ],
                    text=True,
                )
                data = json.loads(r)
                subprocess.run(["grim", str(out / "routing.png")], check=True)
                (out / "routing-layers.json").write_text(
                    subprocess.check_output(["hyprctl", "-j", "layers"], text=True)
                )
                assert data == {"under": 1, "duck": 1}, data
                subprocess.run(["grim", str(out / "routing.png")], check=True)
                (out / "routing-result.json").write_text(json.dumps(data))
                print(data)
            finally:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    run()
