#!/usr/bin/env python3
"""Verify error visibility in the actual settings window while scrolled."""

from check_settings import QML
from pathlib import Path
from qml_support import dependencies
import os
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
OUT.mkdir(parents=True, exist_ok=True)
# Reuse the deterministic settings host, replacing only its window wrapper.

source = QML
start = source.index(" FloatingWindow {visible:true;")
end = source.index(" Timer{interval:200;", start)
source = (
    source[:start]
    + """ DuckWindow{id:window;controller:host;}
"""
    + source[end:]
)
start = source.index(" Timer{interval:200;")
end = source.index(" Timer{interval:10000;", start)
source = (
    source[:start]
    + """ Timer{interval:250;running:true;repeat:true;onTriggered:{
  if(test.busy)return;
  if(test.stage===0){window.testSettings.tab=1;test.stage++;
  }else if(test.stage===1){host.lastError="Не удалось применить настройки. Повторите изменение.";window.testFlick.contentY=window.testFlick.contentHeight-window.testFlick.height;test.stage++;
  }else if(test.stage===2){
   test.check(window.testFooter.visible,"error visible while scrolled");
   test.check(window.testFooter.y>=0&&window.testFooter.y+window.testFooter.height<=window.height,"error stays in viewport");
   test.check(window.testFlick.y+window.testFlick.height<=window.testFooter.y,"content cannot overlap error");
   test.busy=true;window.testSurface.grabToImage(function(result){test.check(result.saveToFile(OUTPUT+"/error-window.png"),"capture window");test.busy=false;test.stage++;});
  }else if(test.stage===3){host.lastError="";test.stage++;
  }else if(test.stage===4){test.check(!window.testFooter.visible,"recovery hides error");console.log("RESULT "+JSON.stringify({checks:test.checks,failed:test.failed}));Qt.quit();}
 }}
"""
    + source[end:]
)
source = source.replace(
    ' property string lastError:""',
    ' property bool opened:true\n  property string lastError:""',
).replace(
    "  function action(name){}",
    "  function hide(){opened=false;}\n  function action(name){}",
)
with tempfile.TemporaryDirectory(prefix="duck-window-") as tmp:
    p = Path(tmp)
    dependencies(p)
    for f in (ROOT / "src").iterdir():
        if f.suffix in (".qml", ".js") and f.name != "DuckWindow.qml":
            (p / f.name).symlink_to(f)
    window = (
        (ROOT / "src/DuckWindow.qml")
        .read_text()
        .replace("PanelWindow {", "FloatingWindow {", 1)
        .replace(
            "    id: window",
            "    id: window\n    readonly property alias testSurface:surface\n    readonly property alias testSettings:settings\n    readonly property alias testFlick:flick\n    readonly property alias testFooter:errorFooter",
            1,
        )
    )
    window = "\n".join(
        line
        for line in window.splitlines()
        if not line.strip().startswith(("exclusionMode:", "WlrLayershell."))
    )
    (p / "DuckWindow.qml").write_text(window)
    (p / "assets").symlink_to(ROOT / "src/assets")

    (p / "shell.qml").write_text(source.replace("OUTPUT", json.dumps(str(OUT))))
    r = subprocess.run(
        ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"),
        capture_output=True,
        text=True,
        timeout=15,
    )
    log = r.stdout + r.stderr
    (OUT / "window-tests.log").write_text(log)
    values = [
        json.loads(entry.split("RESULT ", 1)[1])
        for entry in log.splitlines()
        if "RESULT " in entry
    ]
    assert (
        r.returncode == 0
        and values
        and values[-1]["failed"] == 0
        and not any(
            s in log
            for s in (
                "ASSERT",
                "TypeError",
                "ReferenceError",
                "Cannot open",
                "ERROR",
                "Binding loop",
            )
        )
    ), log
    print(json.dumps(values[-1]))
