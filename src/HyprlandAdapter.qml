pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Hyprland
import "WorldModel.js" as World

Scope {
    id: adapter
    DuckTranslations { id: strings }
    property bool enabled: false
    property bool economy:false
    property bool interacting:false
    property bool pointerNear:false
    readonly property int clientInterval:fast?67:interacting?80:tracking?(economy?300:125):(economy?2500:1000)
    readonly property int pointerInterval:interacting||pointerNear?180:followingCursor?(economy?350:180):(economy?1200:350)
    readonly property int environmentInterval:sceneVisible&&!economy?1000:2000
    property bool tracking: false
    property bool sceneVisible: false
    property bool paused: false
    property bool pointerEnabled: false
    property bool followingCursor: false
    property var monitors: []
    property var clients: []
    property var cursor: null
    property bool locked: false
    property string environmentError: ""
    property string pointerError: ""
    readonly property string error: {var message=environmentError||pointerError;return message.indexOf("error.")===0?strings.t(message):message;}
    property string clientSignature: ""
    property string monitorSignature: ""
    property bool fast: false
    property int geometryRevision: 0
    property int refreshes: 0
    property double pointerTime: 0
    property int pointerSequence: 0
    readonly property string focusedMonitor: Hyprland.focusedMonitor?Hyprland.focusedMonitor.name:""
    readonly property int environmentRequests: environment.count
    readonly property int pointerRequests: pointer.count
    readonly property int requests: environmentRequests+pointerRequests
    property int validationErrors: 0
    readonly property int errors: environment.failures+pointer.failures+validationErrors
    signal pointerReady()

    function collectClients() {
        var list=World.clients(Hyprland.toplevels.values.map(function(t){return t.lastIpcObject;}));
        var signature=JSON.stringify(list);
        if(signature===clientSignature)return;
        if(clientSignature){fast=true;fastExpiry.restart();}
        clientSignature=signature;clients=list;geometryRevision++;
    }
    function refreshClients() {
        if(!enabled)return;
        Hyprland.refreshToplevels();refreshes++;
    }
    function refreshEnvironment() {
        environment.send("[[BATCH]]j/monitors ; j/locked",2);
    }
    function queryPointer() {return pointer.send("j/cursorpos",1);}
    function refresh() {refreshClients();refreshEnvironment();}
    Component.onCompleted: {collectClients();refreshEnvironment();}
    onEnabledChanged: if(enabled)refresh()
    Connections {target:Hyprland.toplevels;function onValuesChanged(){collect.restart();}}
    Variants {
        model:Hyprland.toplevels.values
        delegate:Connections {
            required property var modelData
            target:modelData
            function onLastIpcObjectChanged(){collect.restart();}
        }
    }
    Connections {
        target:Hyprland
        function onRawEvent(event) {
            if(/^(workspace|focusedmon|openwindow|closewindow|movewindow|activewindow|fullscreen|changefloatingmode|monitor|activespecial|pin|configreloaded|minimized)/.test(event.name))events.restart();
        }
    }
    Timer {id:collect;interval:1;onTriggered:adapter.collectClients();}
    Timer {id:events;interval:40;onTriggered:adapter.refresh();}
    Timer {id:fastExpiry;interval:900;onTriggered:adapter.fast=false;}
    Timer {
        interval:adapter.clientInterval
        running:adapter.enabled&&adapter.sceneVisible&&!adapter.paused&&!adapter.locked
        repeat:true;onTriggered:adapter.refreshClients()
    }
    // Recovery must continue through lock and DPMS, independently of rendering.
    Timer {interval:adapter.environmentInterval;running:adapter.enabled;repeat:true;onTriggered:adapter.refreshEnvironment();}
    Timer {
        interval:adapter.pointerInterval
        running:adapter.enabled&&adapter.pointerEnabled&&!adapter.paused&&!adapter.locked
        repeat:true;onTriggered:adapter.queryPointer()
    }
    HyprRequest {
        id:environment
        onCompleted:function(values) {
            // signal var crosses Qt's QVariant boundary; a JSON array can
            // arrive as a QML sequence (Array.isArray is false for it).
            if(!values[0]||typeof values[0].length!=="number"||!values[1]||typeof values[1].locked!=="boolean"){adapter.validationErrors++;adapter.environmentError="error.hyprland-response";return;}
            var list=World.monitors(values[0]),signature=JSON.stringify(list);
            if(signature!==adapter.monitorSignature){adapter.monitorSignature=signature;adapter.monitors=list;adapter.geometryRevision++;}
            adapter.locked=values[1].locked;adapter.environmentError="";
        }
        onFailed:function(message){adapter.environmentError=message;}
    }
    HyprRequest {
        id:pointer
        onCompleted:function(values) {
            var p=values[0],now=Date.now();
            if(!p||!isFinite(p.x)||!isFinite(p.y)){adapter.validationErrors++;adapter.pointerError="error.cursor-response";return;}
            adapter.pointerError="";
            adapter.cursor={x:Number(p.x),y:Number(p.y),dt:adapter.pointerTime?Math.max(.01,(now-adapter.pointerTime)/1000):.35,sequence:++adapter.pointerSequence};
            adapter.pointerTime=now;adapter.pointerReady();
        }
        onFailed:function(message){adapter.pointerError=message;}
    }
}
