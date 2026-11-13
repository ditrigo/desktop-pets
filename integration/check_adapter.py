#!/usr/bin/env python3
"""Exercise the actual Hyprland adapter's independent error channels offscreen."""

from pathlib import Path
from qml_support import dependencies
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FAKE = """import Quickshell
Scope {
 property int count:0
 property int failures:0
 signal completed(var values)
 signal failed(string message)
 function send(command,expected){count++;return true;}
}
"""
TEST = """import QtQuick
import Quickshell
ShellRoot {
 property int checks:0
 property int failed:0
 function check(value,message){checks++;if(!value){failed++;console.error("ASSERT "+message);}}
 HyprlandAdapter{id:adapter;}
 Timer{interval:100;running:true;onTriggered:{
  adapter.testPointer.failed("pointer failure");parent.check(adapter.error==="pointer failure","pointer error exposed");
  adapter.testEnvironment.completed([[],{locked:false}]);parent.check(adapter.error==="pointer failure","environment success cannot clear pointer failure");
  adapter.testEnvironment.failed("environment failure");parent.check(adapter.error==="environment failure","environment error has priority");
  adapter.testPointer.completed([{x:10,y:20}]);parent.check(adapter.pointerError===""&&adapter.error==="environment failure","pointer recovery clears only its channel");
  adapter.testEnvironment.completed([[],{locked:false}]);parent.check(adapter.error==="","both channels recovered");
  adapter.testEnvironment.completed([[],null]);parent.check(adapter.error!=="","null lock response handled");
  adapter.testEnvironment.completed([[],{locked:false}]);parent.check(adapter.error==="","environment payload recovery");
  adapter.testPointer.completed([null]);parent.check(adapter.error!=="","null pointer response handled");
  adapter.testPointer.completed([{x:30,y:40}]);parent.check(adapter.error===""&&adapter.cursor.x===30,"valid pointer recovers");
  parent.check(adapter.errors===2,"payload validation errors counted");
  parent.check(adapter.requests===adapter.environmentRequests+adapter.pointerRequests,"request counts split without losing total");
  adapter.fast=false;adapter.economy=true;adapter.tracking=true;parent.check(adapter.clientInterval===300,"static economy support bound");
  parent.check(adapter.pointerInterval===1200,"distant economy pointer");adapter.interacting=true;parent.check(adapter.clientInterval===80&&adapter.pointerInterval===180,"interaction boost");
  adapter.fast=true;parent.check(adapter.clientInterval===67,"moving support boost");
  adapter.interacting=false;adapter.fast=false;adapter.pointerNear=true;parent.check(adapter.pointerInterval===180,"near pointer accelerates");
  console.log("RESULT "+JSON.stringify({checks:parent.checks,failed:parent.failed}));Qt.quit();
 }}
 Timer{interval:5000;running:true;onTriggered:{console.error("ASSERT timeout");Qt.quit()}}
}
"""
with tempfile.TemporaryDirectory(prefix="duck-adapter-") as tmp:
    p = Path(tmp)
    dependencies(p)
    source = (
        (ROOT / "src/HyprlandAdapter.qml")
        .read_text()
        .replace(
            "    id: adapter",
            "    id: adapter\n    readonly property alias testEnvironment:environment\n    readonly property alias testPointer:pointer",
            1,
        )
    )
    (p / "PetTranslations.qml").symlink_to(ROOT / "src/PetTranslations.qml")
    (p / "HyprlandAdapter.qml").write_text(source)
    shutil.copy2(ROOT / "src/WorldModel.js", p / "WorldModel.js")
    (p / "HyprRequest.qml").write_text(FAKE)
    (p / "shell.qml").write_text(TEST)
    r = subprocess.run(
        ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
        env=dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"),
        capture_output=True,
        text=True,
        timeout=10,
    )
    log = r.stdout + r.stderr
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
            s in log for s in ("ASSERT", "TypeError", "ReferenceError", "ERROR")
        )
    ), log
    print(json.dumps(values[-1]))
