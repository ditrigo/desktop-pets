#!/usr/bin/env python3
"""Run the real model, scene and service offscreen with a deterministic compositor.

Only the PanelWindow platform wrapper and Hyprland adapter are replaced. All
fixtures live in a temporary directory; the installed shell is never modified.
"""

import json
import os
from pathlib import Path
from qml_support import dependencies
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / "src"
FAKE_ADAPTER = """import QtQuick
import Quickshell
Scope {
 property bool enabled:false
 property bool economy:false
 property bool interacting:false
 property bool pointerNear:false
 property int clientInterval:300
 property int pointerInterval:1200
 property bool tracking:false
 property bool sceneVisible:false
 property bool paused:false
 property bool pointerEnabled:false
 property bool followingCursor:false
 property var monitors:[{id:0,name:Quickshell.screens[0].name,x:0,y:0,width:800,height:800,scale:1,transform:0,reserved:[0,26,0,0],activeWorkspace:{id:1},specialWorkspace:{id:0},dpmsStatus:true,disabled:false}]
 property var clients:[]
 property var cursor:({x:300,y:600,dt:.3,sequence:1})
 property bool locked:false
 property string error:""
 property string focusedMonitor:Quickshell.screens[0].name
 property int environmentRequests:0
 property int pointerRequests:0
 property int requests:0
 property int errors:0
 property int refreshes:0
 property int geometryRevision:0
 signal pointerReady()
 function queryPointer(){pointerTimer.start();return true;}
 Timer {id:pointerTimer;interval:1;onTriggered:parent.pointerReady();}
}
"""
WORKFLOW = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 id:test
 property int stage:0
 property int checks:0
 property int failed:0
 property double since:Date.now()
 property int paints:0
 property int appearancePaints:-1
 property double deadline:0
 function check(value,message){checks++;if(!value){failed++;console.error("ASSERT "+message);}}
 function next(){stage++;since=Date.now();}
 QtObject {id:host;property int writes:0;property bool reject:false;function updateEntryInline(id,settings){if(reject)return false;writes++;testSettings.setText(JSON.stringify({bar:{layout:{right:[settings]}}}));return true;}}
 FileView{id:testSettings;path:Qt.resolvedUrl("settings.json").toString().replace(/^file:\\/\\//,"");}
 Service {id:duck;shell:host;settingsPath:Qt.resolvedUrl("settings.json").toString().replace(/^file:\\/\\//,"");stateDirectory:Qt.resolvedUrl("state").toString().replace(/^file:\\/\\//,"");}
 Timer {
  interval:100;running:true;repeat:true
  onTriggered: {
   if(!duck.ready||!duck.activeScene||!duck.activeScene.bird)return;
   var s=duck.activeScene,a=duck.testAdapter;
   if(stage===0&&Date.now()-since>500) {
    check(duck.runState==="active","ready");check(!s.framesWanted,"reduced motion has no frame loop");
    var writes=host.writes;check(duck.setSetting("size",76),"idempotent setting acknowledged");check(host.writes===writes,"unchanged setting does not write configuration");
    check(duck.profile.fed===9,"memory migration/recovery preserves feed count");
    check(s.testSprite.artStyle==="pixel"&&s.testSprite.hat==="wizard"&&s.testSprite.outfit==="cape","stored wardrobe reaches renderer");
    var oldStyle=duck.config.artStyle,oldPalette=duck.config.palette,count=host.writes;
    check(duck.applyLook("explorer"),"look accepted");check(host.writes===count+1,"outfit is one configuration write");
    check(duck.config.hat==="explorer"&&duck.config.outfit==="scarf","whole look applied");
    check(duck.config.artStyle===oldStyle&&duck.config.palette===oldPalette,"look preserves style and palette");
    check(duck.applyLook("explorer")&&host.writes===count+1,"reapplying a look does not write");
    check(!duck.applyLook("missing")&&host.writes===count+1,"unknown look cannot alter settings");
    check(duck.storeLook("Память образа","full"),"save named full look");
    var lookId=duck.profile.looks[0].id;duck.renameLook(lookId,"Новое имя");check(duck.profile.looks[0].name==="Новое имя","rename local look");
    check(duck.applySavedLook(lookId),"apply saved look");duck.removeLook(lookId);check(duck.profile.looks.length===0,"remove only requested look");
    for(var n=0;n<12;n++)check(duck.storeLook("Комплект "+n,"wardrobe"),"collection slot "+n);
    check(!duck.storeLook("Лишний","full")&&duck.profile.looks.length===12,"collection limit exposed");
    var ids=duck.profile.looks.map(function(l){return l.id;});ids.forEach(function(id){duck.removeLook(id);});
    host.reject=true;check(!duck.applyLook("chef"),"failed host write reported");
    check(duck.config.hat==="explorer"&&duck.config.outfit==="scarf"&&duck.settingsError!=="","write failure preserves look and reports error");
    host.reject=false;check(duck.applyLook("wizard")&&duck.settingsError==="","retry clears setting error");
    check(JSON.parse(duck.diagnostics()).uptimeSeconds>=0,"diagnostic uptime available");
    paints=s.metrics().paints;next();
   }else if(stage===1&&Date.now()-since>1500) {
    check(s.metrics().paints===paints,"static dressed pixel duck does not repaint");
    check(duck.action("pause")==="ok","pause accepted");
    check(duck.action("remember")==="ok","remember while paused");
    check(duck.action("clear")==="ok","clear while paused");
    check(duck.paused,"maintenance preserves pause");
    check(!duck.canAction("dance")&&duck.canAction("pause")&&duck.canAction("clear"),"UI availability shares the IPC policy");
    check(duck.action("dance")==="blocked: paused","blocked actions report reason");
    duck.action("pause");duck.action("rest");deadline=duck.profile.restUntil;next();
   }else if(stage===2&&s.birdMode==="sleep") {
    check(deadline>Date.now()+1700000,"rest is scheduled for 30 minutes");
    duck.action("head");duck.action("clear");duck.action("remember");
    check(duck.profile.restUntil===deadline,"pet and maintenance preserve rest deadline");
    check(s.birdMode==="sleep","pet does not wake scheduled sleep");
    check(duck.profile.trust===44,"pet trust survives geometry callbacks");
    duck.action("treat");check(s.items.length===1,"manual food during rest");
    s.bird.manualUntil=s.bird.age+.1;next();
   }else if(stage===3&&s.birdMode==="sleep") {
    check(duck.resting,"manual play returned to rest");duck.action("clear");
    duck.action("wake");check(!duck.resting,"explicit wake cancels rest");
    check(duck.action("feed")==="ok","placement starts");
    check(duck.placement==="pea","placement active");a.locked=true;next();
   }else if(stage===4&&Date.now()-since>200) {
    check(duck.runState==="locked","lock suspends service");check(!s.visible,"lock hides scene");
    check(duck.placement==="","lock releases placement input");check(duck.action("dance")==="blocked: locked","command rejected while locked");
    s.implicitWidth=1;s.implicitHeight=1;
    check(duck.setSettings({artStyle:"voxel",hat:"explorer",outfit:"space"}),"wardrobe update accepted while hidden");next();
   }else if(stage===5&&Date.now()-since>200&&appearancePaints===-1) {
    check(s.testSprite.artStyle==="voxel"&&s.testSprite.hat==="explorer"&&s.testSprite.outfit==="space","wardrobe update reaches hidden renderer");appearancePaints=s.metrics().paints;since=Date.now();
   }else if(stage===5&&Date.now()-since>1200) {
    check(s.metrics().paints===appearancePaints,"locked dressed voxel duck does not paint");
    duck.saveMemory();check(Math.abs(duck.profile.positions[duck.monitorName].x-s.bird.x/800)<.0001,"hidden surface dimensions cannot corrupt saved position");
    s.implicitWidth=800;s.implicitHeight=800;a.locked=false;
    var monitors=JSON.parse(JSON.stringify(a.monitors));monitors[0].dpmsStatus=false;a.monitors=monitors;next();
   }else if(stage===6&&Date.now()-since>200) {
    check(duck.runState==="display-off","DPMS stops scene");check(!s.visible,"DPMS hides scene");
    var monitors=JSON.parse(JSON.stringify(a.monitors));monitors[0].dpmsStatus=true;a.monitors=monitors;
    a.clients=[{address:"test",monitor:0,workspace:{id:1},mapped:true,hidden:false,at:[50,100],size:[700,600],fullscreen:1}];next();
   }else if(stage===7&&Date.now()-since>200) {
    check(duck.runState==="fullscreen","fullscreen blocks scene");check(!s.visible,"fullscreen hides scene");
    check(duck.action("feed")==="blocked: hidden","hidden command not silently dropped");a.clients=[];next();
   }else if(stage===8&&Date.now()-since>200) {
    s.dragging=true;check(duck.action("dance")==="blocked: dragging","drag has priority");s.dragging=false;
    check(duck.action("come")==="queued","cursor command is acknowledged as queued");next();
   }else if(stage===9&&Date.now()-since>300) {
    check(duck.lastCommand.name==="come"&&duck.lastCommand.result==="ok","queued cursor command eventually executes");
    duck.action("rest");duck.updateProfile({restUntil:Date.now()-10},true);next();
   }else if(stage===10&&!duck.profile.restUntil&&Date.now()-since>1200) {
    check(!duck.resting,"rest deadline expires");duck.action("clear");duck.action("sleep");next();
   }else if(stage===11&&s.birdMode==="sleep") {
    duck.action("pause");duck.updateProfile({restUntil:Date.now()-10},true);next();
   }else if(stage===12&&!duck.profile.restUntil&&Date.now()-since>1200) {
    check(duck.paused&&s.birdMode==="sleep","deadline does not animate a paused duck");duck.action("pause");next();
   }else if(stage===13&&Date.now()-since>200) {
    check(s.birdMode!=="sleep","expired rest wakes after resume");duck.action("pause");duck.saveMemory();next();
   }else if(stage===14&&Date.now()-since>1800) {
    check(!duck.dirtyMemory,"memory save confirmed");
    console.log("RESULT "+JSON.stringify({checks:checks,failed:failed,diagnostics:JSON.parse(duck.diagnostics())}));Qt.quit();
   }
  }
 }
 Timer {interval:20000;running:true;onTriggered:{console.error("ASSERT workflow timed out at "+test.stage+" "+duck.status());console.log("RESULT "+JSON.stringify({failed:test.failed+1,checks:test.checks}));Qt.quit();}}
}
"""
FIRST_RUN = """import QtQuick
import Quickshell
ShellRoot {
 id:test
 property int checks:0
 property int failed:0
 property int stage:0
 function check(value,message){checks++;if(!value){failed++;console.error("ASSERT "+message);}}
 Service {id:duck;settingsPath:Qt.resolvedUrl("settings.json").toString().replace(/^file:\\/\\//,"");stateDirectory:Qt.resolvedUrl("state").toString().replace(/^file:\\/\\//,"");}
 Timer {interval:500;running:true;repeat:true;onTriggered:{
  if(!duck.ready||!duck.activeScene||!duck.activeScene.bird)return;
  const scene=duck.activeScene;
  if(test.stage===0){
  test.check(duck.runState==="active","first launch becomes active without saved files");
  test.check(duck.config.artStyle==="vector"&&duck.config.palette==="yellow","classic yellow duck is the default");
  test.check(duck.config.hat==="none"&&duck.config.outfit==="none","first launch starts without clothing");
  test.check(duck.config.sound===false,"sound starts disabled");
  test.check(duck.config.name==="Ducky","default name is available");
  test.check(duck.profile.fed===0&&duck.profile.looks.length===0,"no personal state is bundled");
  test.check(duck.lastError==="","no first launch errors");
  duck.action("pause");scene.spawn("ball",100,150,0,0);
  scene.ball.x=100;scene.ball.y=150;scene.ball.rotation=45;scene.itemRevision++;test.stage++;
  }else if(test.stage===1){
   test.check(scene.testBall.visible,"ball becomes visible");
   test.check(scene.testBall.x===87&&scene.testBall.y===137&&scene.testBall.rotation===45,"ball pose uses its initial snapshot");
   scene.ball.x=200;scene.ball.y=220;scene.ball.rotation=90;scene.itemRevision++;test.stage++;
  }else if(test.stage===2){
   test.check(scene.testBall.x===187&&scene.testBall.y===207&&scene.testBall.rotation===90,"revision refreshes a mutated item's rendered pose");
   scene.clearItems();test.stage++;
  }else{
  test.check(!scene.testBall.visible,"removing the ball hides its visual");
  duck.saveMemory();
  console.log("RESULT "+JSON.stringify({checks:test.checks,failed:test.failed}));Qt.quit();
  }
 }}
 Timer {interval:10000;running:true;onTriggered:{console.error("ASSERT first launch timed out");Qt.quit();}}
}
"""
MEMORY_FAILURE = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 property int failures:0
 MemoryStore {id:memory;directory:Qt.resolvedUrl("state").toString().replace(/^file:\\/\\//,"");}
 Timer {interval:300;running:true;onTriggered:{memory.directory=Qt.resolvedUrl("not-a-directory").toString().replace(/^file:\\/\\//,"");memory.update({fed:10},true);}}
 Timer {interval:2300;running:true;onTriggered:{if(!memory.dirty||memory.failures<1||memory.profile.fed!==10)parent.failures++;memory.directory=Qt.resolvedUrl("state").toString().replace(/^file:\\/\\//,"");}}
 Timer {interval:8000;running:true;onTriggered:{console.log("RESULT "+JSON.stringify({failed:parent.failures+(memory.dirty||memory.writes<1||memory.profile.fed!==10||memory.error?1:0),checks:7,writes:memory.writes,error:memory.error}));Qt.quit();}}
}
"""


def run_case(case):
    with tempfile.TemporaryDirectory(prefix="duck-qml-test-") as temporary:
        p = Path(temporary)
        dependencies(p)
        for source in SOURCE.iterdir():
            if source.suffix in (".qml", ".js") and source.name not in (
                "BarWidget.qml",
                "PetSettings.qml",
                "PetAppearancePicker.qml",
                "PetLabel.qml",
                "PetSettingRow.qml",
            ):
                shutil.copy2(source, p / source.name)
        shutil.copytree(SOURCE / "assets", p / "assets")
        scene = (
            (p / "PetScene.qml")
            .read_text()
            .replace(
                "PanelWindow {",
                "FloatingWindow {\n    readonly property alias testSprite:sprite\n    readonly property alias testBall:ballItem\n    implicitWidth:800\n    implicitHeight:800",
                1,
            )
        )
        scene = (
            "\n".join(
                line
                for line in scene.splitlines()
                if not line.strip().startswith(
                    ("anchors {left:true", "exclusionMode:", "WlrLayershell.")
                )
            )
            + "\n"
        )
        (p / "PetScene.qml").write_text(scene)
        service = (
            (p / "Service.qml")
            .read_text()
            .replace(
                "    id: root",
                "    id: root\n    readonly property var testAdapter: world",
                1,
            )
        )
        (p / "Service.qml").write_text(service)
        (p / "HyprlandAdapter.qml").write_text(FAKE_ADAPTER)
        (p / "PetWindow.qml").write_text(
            "import Quickshell\nScope {property var controller:null;}\n"
        )
        (p / "settings.json").write_text(
            json.dumps(
                {
                    "bar": {
                        "layout": {
                            "right": [
                                {
                                    "id": "ditrigo.desktop-pets",
                                    "enabled": True,
                                    "reducedMotion": True,
                                    "artStyle": "pixel",
                                    "hat": "wizard",
                                    "outfit": "cape",
                                }
                            ]
                        }
                    }
                }
            )
        )
        (p / "state").mkdir()
        memory = {
            "version": 2,
            "trust": 42,
            "fed": 9,
            "energy": 80,
            "satiety": 60,
            "positions": {},
            "favorites": {},
        }
        (p / "state/memory.json").write_text(
            "corrupt" if case == "recovery" else json.dumps(memory)
        )
        (p / "state/memory.previous.json").write_text(json.dumps(memory))
        (p / "not-a-directory").write_text("fixture")
        if case == "first_run":
            (p / "settings.json").unlink()
            shutil.rmtree(p / "state")
        (p / "shell.qml").write_text(
            FIRST_RUN
            if case == "first_run"
            else MEMORY_FAILURE
            if case == "write_failure"
            else WORKFLOW
        )
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        result = subprocess.run(
            ["quickshell", "-p", str(p / "shell.qml"), "--no-color"],
            env=env,
            capture_output=True,
            text=True,
            timeout=25,
        )
        log = result.stdout + result.stderr
        results = [
            json.loads(line.split("RESULT ", 1)[1])
            for line in log.splitlines()
            if "RESULT " in line
        ]
        errors = [
            line
            for line in log.splitlines()
            if "ASSERT " in line
            or "TypeError:" in line
            or "ReferenceError:" in line
            or "Binding loop" in line
            or "Cannot open:" in line
            or "Error decoding" in line
            or "ERROR:" in line
        ]
        if not results or result.returncode or results[-1]["failed"] or errors:
            raise AssertionError(case + "\n" + log)
        if case == "first_run":
            saved = json.loads((p / "state/memory.json").read_text())
            assert saved["fed"] == 0 and saved["looks"] == [], saved
        elif case != "write_failure":
            saved = json.loads((p / "state/memory.json").read_text())
            assert (
                saved["version"] == 3 and saved["fed"] == 9 and saved["trust"] == 44
            ), saved
            json.loads((p / "state/memory.previous.json").read_text())
        print(case, json.dumps(results[-1], ensure_ascii=False), flush=True)
        return results[-1]


if __name__ == "__main__":
    for scenario in ("first_run", "normal", "recovery", "write_failure"):
        run_case(scenario)
