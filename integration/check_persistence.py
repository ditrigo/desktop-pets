#!/usr/bin/env python3
"""Disk confirmation, delayed/stale writes, retry and external config changes."""

from pathlib import Path
from qml_support import dependencies
import os
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
QML = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 id:test
 property int stage:0
 property int checks:0
 property int failed:0
 property int ticks:0
 property bool drop:false
 property var writes:[]
 function check(v,label){checks++;if(!v){failed++;console.error("ASSERT "+label);}}
 FileView{id:disk;path:Qt.resolvedUrl("settings.json");watchChanges:true;onFileChanged:reload();}
 QtObject{id:host;function updateEntryInline(id,settings){if(!test.drop)test.writes.push(JSON.parse(JSON.stringify(settings)));return true;}}
 PetSettingsStore{id:store;shell:host;path:Qt.resolvedUrl("settings.json").toString();timeoutMs:800;}
 function persist(entry){var d=JSON.parse(disk.text());d.bar.layout.right[0]=entry;disk.setText(JSON.stringify(d));}
 Timer{interval:120;running:true;repeat:true;onTriggered:{
  test.ticks++;
  if(test.stage===0&&store.disk.hat==="chef"){
   test.check(store.apply({hat:"wizard"}),"accepted");test.check(store.applying,"applying before disk");test.stage++;
  }else if(test.stage===1){
   test.check(store.applying,"delayed write not falsely saved");store.apply({hat:"pirate"});store.apply({hat:"santa"});test.persist(test.writes[0]);test.stage++;
  }else if(test.stage===2){
   test.check(store.applying&&store.settings.hat==="santa","stale acknowledgement retains last choice");
   var d=JSON.parse(disk.text());d.other={preserved:17};d.bar.layout.left=[{id:"external.widget",value:42}];disk.setText(JSON.stringify(d));test.stage++;
  }else if(test.stage===3){test.persist(test.writes[test.writes.length-1]);test.stage++;
  }else if(test.stage===4&&store.state==="saved"){
   test.check(store.disk.hat==="santa","latest choice persisted");var d=JSON.parse(disk.text());test.check(d.other.preserved===17&&d.bar.layout.left[0].value===42,"other widgets and settings preserved");
   test.drop=true;store.apply({hat:"crown"});test.stage++;
  }else if(test.stage===5&&store.state==="failed"){
   test.check(store.error!==""&&!store.applying,"bounded failed write");test.check(store.settings.hat==="crown","last choice retained for explicit retry");test.drop=false;test.check(store.retry(),"retry available");test.stage++;
  }else if(test.stage===6&&test.writes.length>3){test.persist(test.writes[test.writes.length-1]);test.stage++;
  }else if(test.stage===7&&store.state==="saved"){
   test.check(store.settings.hat==="crown"&&store.error==="","retry confirmed");
   var d=JSON.parse(disk.text());d.bar.layout.right[0].outfit="scarf";disk.setText(JSON.stringify(d));test.stage++;
  }else if(test.stage===8&&store.settings.outfit==="scarf"){
   test.check(store.state==="saved","idle external edit adopted");console.log("RESULT "+JSON.stringify({checks:test.checks,failed:test.failed}));Qt.quit();
  }
  if(test.ticks>50){console.error("ASSERT timeout "+test.stage+" "+store.state);Qt.quit();}
 }}
}
"""
with tempfile.TemporaryDirectory(prefix="duck-persist-") as tmp:
    p = Path(tmp)
    dependencies(p)
    for name in ["PetSettingsStore.qml", "PetModel.js", "PetTranslations.qml"]:
        (p / name).symlink_to(ROOT / "src" / name)
    (p / "settings.json").write_text(
        json.dumps(
            {
                "bar": {
                    "layout": {"right": [{"id": "ditrigo.desktop-pets", "hat": "chef"}]}
                }
            }
        )
    )
    (p / "shell.qml").write_text(QML)
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
            s in log for s in ("ASSERT", "ERROR", "TypeError", "ReferenceError")
        )
    ), log
    print(values[-1])
