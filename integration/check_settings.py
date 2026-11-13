#!/usr/bin/env python3
"""Render and exercise real settings controls with a deterministic host."""

from pathlib import Path
from qml_support import dependencies
import os
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / json.loads((ROOT / "manifest.json").read_text())["version"]
OUT.mkdir(parents=True, exist_ok=True)
QML = """import QtQuick
import Quickshell
import "DuckModel.js" as Model
import "DuckPolicy.js" as Policy
import "DuckLooks.js" as Looks
import qs.Commons as Commons
ShellRoot {
 id:test
 property int stage:0
 property int checks:0
 property int failed:0
 property bool busy:false
 function check(value,label){checks++;if(!value){failed++;console.error("ASSERT "+label);}}
 function descendants(item,result){for(var child of item.children){result.push(child);descendants(child,result);}return result;}
 function capture(name){busy=true;settings.grabToImage(function(result){test.check(result.saveToFile(OUTPUT+"/"+name+".png"),"capture "+name);test.busy=false;test.stage++;});}
 QtObject {
  id:host
  property var config:Model.settings({artStyle:"pixel",palette:"white",hat:"chef",outfit:"none"})
  property var runtime:({mode:"idle",mood:"Вам доверяет"})
  property var profile:({trust:100,energy:100,satiety:50,favorites:{}})
  property var monitors:[]
  property string monitorName:""
  property bool paused:false
  property string runState:"active"
  property bool resting:false
  property int restMinutes:0
  property string settingsState:"idle"
  property string lastError:""
  property int writes:0
  function canAction(name){return Policy.blocked(name,{ready:true,enabled:config.enabled,visible:runState==="active"||runState==="paused",hasScene:true,locked:false,paused:paused,dragging:false})==="";}
  function setSettings(patch){var next=Model.settings(Object.assign({},config,patch));if(JSON.stringify(next)!==JSON.stringify(config)){config=next;writes++;}return true;}
  function setSetting(key,value){var patch={};patch[key]=value;return setSettings(patch);}
  function applyLook(key){var patch=Looks.patch(key);return patch&&setSettings(patch);}
  function storeLook(name,kind){profile=Object.assign({},profile,{looks:[{id:"preview",name:name||"Мой образ",kind:kind,hat:config.hat,outfit:config.outfit,artStyle:config.artStyle,palette:config.palette}]});}
  function renameLook(id,name){}
  function removeLook(id){profile=Object.assign({},profile,{looks:[]});}
  function applySavedLook(id){}
  function action(name){}
 }
 BarWidget {}
 FloatingWindow {visible:true;implicitWidth:540;implicitHeight:1700;color:Commons.Color.background
 DuckSettings{id:settings;x:20;y:20;width:500;tab:1;controller:host;}
 }
 Timer{interval:200;running:true;repeat:true;onTriggered:{
  if(test.busy)return;
  var items=test.descendants(settings,[]);
  if(test.stage===0){
   var buttons=items.filter(function(i){return typeof i.clicked==="function"&&i.text==="Волшебник";});test.check(buttons.length===1,"look button found");
   buttons[0].clicked();test.check(host.writes===1&&host.config.hat==="wizard"&&host.config.outfit==="cape","look button changes outfit in one call");
   test.check(host.config.artStyle==="pixel"&&host.config.palette==="white","look button preserves style and palette");
   buttons[0].clicked();test.check(host.writes===1,"look selection idempotent");
   items.filter(function(i){return typeof i.clicked==="function"&&i.text==="Повар";})[0].clicked();
   test.check(host.writes===2&&host.config.hat==="chef"&&host.config.outfit==="none","second look applied");
   items.filter(function(i){return typeof i.clicked==="function"&&i.text==="Сохранить полный образ";})[0].clicked();
   test.check(host.profile.looks.length===1,"named look preview added");
   host.setSetting("quietHours",true);
   var start=items.filter(function(i){return i.objectName==="quietStart";})[0];
   var end=items.filter(function(i){return i.objectName==="quietEnd";})[0];
   test.check(!!start&&!!end,"labelled time inputs exist");
   start.text="25:30";start.editingFinished();
   test.check(!start.acceptableInput&&host.config.quietStart==="22:00","invalid time does not overwrite quiet hours");
   start.text="23:15";start.editingFinished();
   test.check(start.acceptableInput&&host.config.quietStart==="23:15","valid local time saved");
   end.text="09:00";end.editingFinished();
   test.check(host.config.quietEnd==="09:00","end time saved independently");
   settings.previewView="front";test.stage++;
  }else if(test.stage===1){test.capture("appearance");
  }else if(test.stage===2){settings.tab=0;host.paused=true;host.runState="paused";test.stage++;
  }else if(test.stage===3){
   for(var item of items)if(item.actionName!==undefined){if(item.actionName==="dance"||item.actionName==="feed")test.check(!item.enabled,"unavailable "+item.actionName);if(item.actionName==="pause")test.check(item.enabled,"resume available");}
   test.check(items.some(function(i){return i.text==="На паузе";}),"pause status visible");test.capture("paused");
  }else if(test.stage===4){host.paused=false;host.runState="fullscreen";test.stage++;
  }else if(test.stage===5){
   test.check(items.some(function(i){return i.text==="Скрыта полноэкранным окном";}),"hidden status visible");
   test.check(items.filter(function(i){return i.actionName==="dance";}).every(function(i){return !i.enabled;}),"hidden action disabled");test.capture("fullscreen");
  }else if(test.stage===6){host.runState="active";test.stage++;
  }else if(test.stage===7){test.check(items.filter(function(i){return i.actionName==="dance";}).every(function(i){return i.enabled;}),"active actions restored");console.log("RESULT "+JSON.stringify({checks:test.checks,failed:test.failed}));Qt.quit();}
 }}
 Timer{interval:10000;running:true;onTriggered:{console.error("ASSERT timeout");Qt.quit()}}
}
"""


def run():
    with tempfile.TemporaryDirectory(prefix="duck-settings-") as tmp:
        p = Path(tmp)
        dependencies(p)
        for f in (ROOT / "src").iterdir():
            if f.suffix in (".qml", ".js"):
                (p / f.name).symlink_to(f)
        (p / "assets").symlink_to(ROOT / "src/assets")

        (p / "shell.qml").write_text(QML.replace("OUTPUT", json.dumps(str(OUT))))
        r = subprocess.run(
            ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
            env=dict(
                os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"
            ),
            capture_output=True,
            text=True,
            timeout=15,
        )
        log = r.stdout + r.stderr
        (OUT / "settings-tests.log").write_text(log)
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
                )
            )
        ), log
        print(json.dumps(values[-1]))


if __name__ == "__main__":
    run()
