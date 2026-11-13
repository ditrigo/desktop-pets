pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import "PetModel.js" as Model
import "WorldModel.js" as World
import "PetPolicy.js" as Policy
import "PetLooks.js" as Looks

Scope {
    id: root
    PetTranslations { id: strings }
    property var shell: null
    property var manifest: null
    property string omarchyPath: ""
    readonly property string pluginId: "ditrigo.desktop-pets"
    property string stateDirectory: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/desktop-pets"
    property string settingsPath: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/omarchy/shell.json"
    readonly property var inlineSettings: settingsStore.settings
    readonly property var userConfig:Model.settings(inlineSettings)
    readonly property bool quietNow:Model.quietAt(userConfig,new Date(clockNow).getHours()*60+new Date(clockNow).getMinutes())
    readonly property var config:Object.assign({},userConfig,quietNow?(userConfig.quietMode==="work"?{workMode:true}:{reducedMotion:true}):{})
    readonly property bool economy:config.powerProfile==="economy"||config.powerProfile==="auto"&&UPower.onBattery
    readonly property var profile: memory.profile
    readonly property bool ready: memory.ready
    readonly property bool dirtyMemory: memory.dirty
    property double clockNow: Date.now()
    readonly property bool resting: profile.restUntil > clockNow
    readonly property int restMinutes: resting ? Math.ceil((profile.restUntil-clockNow)/60000) : 0
    readonly property var monitors: world.monitors
    readonly property var clients: world.clients
    readonly property var cursor: world.cursor
    property var scenes: ({})
    property var favoriteHandles: ({})
    property string stableFocus: ""
    readonly property string monitorName: World.availableMonitor(monitors,config,stableFocus)
    readonly property var activeScene: scenes[monitorName] || null
    readonly property bool sceneVisible: !!activeScene && activeScene.visible
    readonly property bool sleeping: !!activeScene && activeScene.birdMode === "sleep"
    readonly property string runState: !ready ? "loading" : !config.enabled ? "disabled" : !activeScene ? "no-screen"
        : world.locked ? "locked" : activeScene.monitor && !activeScene.monitor.dpmsStatus ? "display-off"
        : config.hideFullscreen && activeScene.fullscreenApp ? "fullscreen" : paused ? "paused" : "active"
    property bool paused: false
    property bool opened: false
    property bool shuttingDown: false
    property bool wakePending: false
    property string placement: ""
    property string placementMonitor: ""
    property string queuedAction: ""
    property string speechKey: ""
    property var speechArgs: []
    property string speechText: ""
    readonly property string bubble:speechKey?strings.format(speechKey,speechArgs):speechText
    property string commandErrorKey: ""
    readonly property string commandError:commandErrorKey?strings.t(commandErrorKey):""
    readonly property string settingsError: settingsStore.error
    readonly property string settingsState: settingsStore.state
    readonly property double startedAt: Date.now()
    readonly property string lastError: memory.error || world.error || settingsError || commandError
    property var runtime: ({})
    property int lookSerial:0
    property int commandSerial: 0
    property var lastCommand: ({})

    function registerScene(name,item) {var next=Object.assign({},scenes);next[name]=item;scenes=next;}
    function unregisterScene(name,item) {if(shuttingDown||scenes[name]!==item)return;var next=Object.assign({},scenes);delete next[name];scenes=next;}
    function setSettings(patch) {checkpoint();var accepted=settingsStore.apply(patch);if(accepted)commandErrorKey="";return accepted;}
    function retrySettings(){return settingsStore.retry();}
    function setSetting(key,value) {
        if(!Object.prototype.hasOwnProperty.call(Model.defaults,key))return false;
        var patch={};patch[key]=value;return setSettings(patch);
    }
    function applyLook(name) {var patch=Looks.patch(name);return patch?setSettings(patch):false;}
    function storeLook(name,kind){
        if(profile.looks.length>=12){commandErrorKey="error.look-limit";return false;}
        var look={version:1,id:Date.now().toString(36)+"-"+(++lookSerial),name:name,kind:kind,hat:userConfig.hat,outfit:userConfig.outfit};
        if(kind!=="wardrobe"){look.artStyle=userConfig.artStyle;look.palette=userConfig.palette;}
        updateProfile({looks:profile.looks.concat([look])},true);return true;
    }
    function renameLook(id,name){updateProfile({looks:profile.looks.map(function(l){return l.id===id?Object.assign({},l,{name:name}):l;})},true);}
    function removeLook(id){updateProfile({looks:profile.looks.filter(function(l){return l.id!==id;})},true);}
    function applySavedLook(id){
        var look=profile.looks.find(function(l){return l.id===id;});if(!look)return false;
        var patch={hat:look.hat,outfit:look.outfit};
        if(look.kind==="full"){patch.artStyle=look.artStyle;patch.palette=look.palette;}
        return setSettings(patch);
    }
    function actionBlockReason(name) {return Policy.blocked(name,actionState());}
    function canAction(name) {return actionBlockReason(name)==="";}
    function setMonitor(name) {return setSettings({monitorMode:name?"fixed":"follow",monitor:name||""});}
    function updateProfile(patch,important) {memory.update(patch,!!important);}
    function saveMemory() {checkpoint();memory.flush();}
    function report(screenName,bird,w) {
        if(screenName!==monitorName||shuttingDown||!w||w.width<1||w.height<1)return;
        var positions=Object.assign({},profile.positions);positions[screenName]=Model.position(bird,w);
        var important=bird.fed!==profile.fed||bird.trust!==profile.trust;
        updateProfile({positions:positions,trust:bird.trust,energy:bird.energy,satiety:bird.satiety,fed:bird.fed},important);
    }
    function checkpoint() {if(activeScene&&activeScene.bird)report(monitorName,activeScene.bird,activeScene.world());}
    function remember(screenName,bird,w) {
        var favorites=Object.assign({},profile.favorites);favorites[screenName]=Model.position(bird,w);
        var handles=Object.assign({},favoriteHandles),p=Model.supportFor(w.surfaces,bird);
        handles[screenName]=p&&p.window?p.window:"";favoriteHandles=handles;
        updateProfile({favorites:favorites},true);sayKey("speech.remember");
    }
    function cancelRest() {clockNow=Date.now();if(profile.restUntil)updateProfile({restUntil:0},true);}
    function show() {if(world.locked)return;placement="";opened=true;}
    function hide() {opened=false;}
    function toggle() {opened?hide():show();}
    function open() {show();}
    function close() {hide();}
    function cancelPlacement() {placement="";placementMonitor="";}
    function actionState() {return {ready:ready,enabled:config.enabled,locked:world.locked,
        visible:sceneVisible&&runState!=="display-off"&&runState!=="fullscreen",hasScene:!!activeScene,
        paused:paused,dragging:!!activeScene&&(activeScene.dragging||activeScene.holdingBall)};}
    function reply(name,result) {
        lastCommand={id:commandSerial,name:name,result:result,time:Date.now()};
        commandErrorKey=result.indexOf("blocked:")===0?"reason."+result.slice(8).replace(/ /g,"-"):"";
        return result;
    }
    function place(kind,x,y,vx,vy) {
        if(["pea","ball"].indexOf(kind)<0||![x,y,vx,vy].every(function(n){return isFinite(Number(n));}))return "invalid placement";
        var blocked=Policy.blocked("treat",actionState());
        if(blocked)return reply("place","blocked: "+blocked);
        if(!activeScene.spawn(kind,Number(x),Number(y),Model.clamp(Number(vx),-700,700),Model.clamp(Number(vy),-700,700)))return reply("place","blocked: not ready");
        cancelPlacement();return reply("place","ok");
    }
    function action(name) {
        commandSerial++;queuedAction="";pendingPointer.stop();
        var blocked=Policy.blocked(name,actionState());
        if(blocked)return reply(name,blocked==="unknown action"?blocked:"blocked: "+blocked);
        if(name==="pause"){checkpoint();paused=!paused;cancelPlacement();return reply(name,"ok");}
        if(name==="work")return reply(name,setSetting("workMode",!config.workMode)?"ok":"settings unavailable");
        if(name==="clear") {
            Object.keys(scenes).forEach(function(key){if(scenes[key])scenes[key].clearItems();});
            sayKey("speech.clear");return reply(name,"ok");
        }
        if(name==="remember") {
            activeScene.ensureBird();
            if(!activeScene.bird)return reply(name,"blocked: not ready");
            remember(monitorName,activeScene.bird,activeScene.world());return reply(name,"ok");
        }
        wakePending=false;
        if(name==="rest"||name==="sleep") {
            paused=false;clockNow=Date.now();updateProfile({restUntil:clockNow+(name==="rest"?30:5)*60000},true);
            activeScene.perform("rest");sayKey(name==="rest"?"speech.rest":"speech.sleep");return reply(name,"ok");
        }
        if(name==="wake"){paused=false;cancelRest();}
        if(name==="reset")paused=false;
        if(name==="feed"||name==="ball") {
            placement=name==="feed"?"pea":"ball";placementMonitor=monitorName;opened=false;
            sayKey(name==="feed"?"speech.place-pea":"speech.place-ball");return reply(name,"ok");
        }
        if(name==="come") {queuedAction=name;const accepted=reply(name,"queued");pendingPointer.restart();world.queryPointer();return accepted;}
        var result=activeScene.perform(name);
        if(result!=="ok")return reply(name,result);
        var phrases={treat:"speech.treat",dance:"speech.dance",quack:"speech.quack",hop:"speech.hop",perch:"speech.perch",reset:"speech.reset",home:"speech.home"};
        if(phrases[name])sayKey(phrases[name]);
        if(name==="quack"&&config.sound&&!quackSound.running)quackSound.running=true;
        return reply(name,"ok");
    }
    function react(event) {
        var keys={noticeFood:"speech.noticeFood",noticeBall:"speech.noticeBall",fed:"speech.fed",pet:resting?"speech.pet-sleep":"speech.pet",wing:"speech.wing",belly:"speech.belly",surprise:"speech.surprise",wake:"speech.wake",ball:"speech.ball"};
        if(keys[event])sayKey(keys[event],event==="fed"?[config.name]:[]);
        checkpoint();
    }
    function say(message) {speechKey="";speechText=String(message).slice(0,512);speechTimer.restart();}
    function sayKey(key,args) {speechText="";speechKey=key;speechArgs=args||[];speechTimer.restart();}
    function diagnostics() {
        return JSON.stringify({version:"1.0.0",runState:runState,uptimeSeconds:Math.max(0,(Date.now()-startedAt)/1000),requests:world.requests,
            economy:economy,onBattery:UPower.onBattery,clientIntervalMs:world.clientInterval,pointerIntervalMs:world.pointerInterval,environmentRequests:world.environmentRequests,pointerRequests:world.pointerRequests,requestErrors:world.errors,
            clientRefreshes:world.refreshes,geometryRevision:world.geometryRevision,memoryWrites:memory.writes,
            settingsState:settingsState,settingsRevision:settingsStore.revision,settingsAttempts:settingsStore.attempts,memoryDirty:memory.dirty,memoryFailures:memory.failures,lastCommand:lastCommand,
            scene:activeScene?activeScene.metrics():{},error:lastError});
    }
    function status() {return JSON.stringify({version:"1.0.0",settings:config,paused:paused,opened:opened,placement:placement,
        quietNow:quietNow,settingsState:settingsState,resting:resting,restMinutes:restMinutes,monitor:monitorName,runState:runState,runtime:runtime,memory:profile,lastCommand:lastCommand,error:lastError});}
    onUserConfigChanged:clockNow=Date.now()
    onRunStateChanged: {
        commandErrorKey="";
        if(["active","paused"].indexOf(runState)<0){cancelPlacement();if(runState==="locked"||runState==="display-off")opened=false;}
        clockNow=Date.now();
        if(runState==="active"&&wakePending)wakeAfterResume.restart();
    }
    onMonitorNameChanged: {cancelPlacement();queuedAction="";}
    Component.onCompleted: stableFocus=world.focusedMonitor
    Component.onDestruction: {checkpoint();memory.flush();shuttingDown=true;}

    MemoryStore {id:memory;directory:root.stateDirectory;}
    PetSettingsStore{id:settingsStore;path:root.settingsPath;shell:root.shell;}
    HyprlandAdapter {
        id:world
        enabled:root.ready&&root.config.enabled
        sceneVisible:root.sceneVisible
        paused:root.paused
        economy:root.economy
        interacting:!!root.activeScene&&(root.activeScene.inputHeld||root.activeScene.framesWanted)
        pointerNear:!!root.activeScene&&!!root.cursor&&!!root.activeScene.monitor&&Math.hypot(root.cursor.x-root.activeScene.monitor.x-root.activeScene.birdX,root.cursor.y-root.activeScene.monitor.y-root.activeScene.birdY)<root.config.size*2.5
        tracking:!!root.activeScene&&root.activeScene.windowTracking
        followingCursor:root.config.followCursor
        pointerEnabled:root.sceneVisible&&root.runState==="active"&&!root.placement&&!root.resting&&!root.sleeping&&!root.config.workMode&&!root.config.reducedMotion
            &&(root.config.cursorReactions||root.config.followCursor)&&!!root.activeScene&&!root.activeScene.inputHeld
        onFocusedMonitorChanged: {root.cancelPlacement();focusDelay.restart();}
        onPointerReady: {
            if(root.queuedAction!=="come")return;
            root.queuedAction="";pendingPointer.stop();
            var blocked=Policy.blocked("come",root.actionState());
            root.reply("come",blocked?"blocked: "+blocked:root.activeScene.perform("come"));
        }
    }
    Timer{interval:60000;running:root.userConfig.quietHours;repeat:true;onTriggered:root.clockNow=Date.now();}
    Timer {id:focusDelay;interval:300;onTriggered:{root.checkpoint();root.stableFocus=world.focusedMonitor;}}
    Timer {id:pendingPointer;interval:1000;onTriggered:{if(root.queuedAction){root.queuedAction="";root.reply("come","failed: cursor unavailable");}}}
    Timer {id:wakeAfterResume;interval:1;onTriggered:if(root.wakePending&&root.runState==="active")root.action("wake");}
    Timer {
        interval:1000;running:root.ready&&root.profile.restUntil>0;repeat:true
        onTriggered: {
            root.clockNow=Date.now();
            if(root.profile.restUntil&&root.profile.restUntil<=root.clockNow){root.cancelRest();root.wakePending=true;if(root.runState==="active")root.action("wake");}
        }
    }
    Process {
        id:quackSound
        command:["pw-play",Qt.resolvedUrl("assets/quack.wav").toString().replace(/^(file|qs):\/\//,"")]
        onExited:function(code){if(code!==0)root.commandErrorKey="error.sound";}
    }
    Timer {id:speechTimer;interval:3200;onTriggered:{root.speechKey="";root.speechText="";}}
    Variants {model:Quickshell.screens;delegate:PetScene{required property var modelData;targetScreen:modelData;controller:root;}}
    Loader {active:root.opened;sourceComponent:Component{PetWindow{controller:root;}}}
    IpcHandler {
        target:"desktop-pets"
        function status():string{return root.status();}
        function diagnostics():string{return root.diagnostics();}
        function action(name:string):string{return root.action(name);}
        function applyLook(name:string):string{return root.applyLook(name)?"ok":"unknown look or settings unavailable";}
        function setSetting(key:string,value:string):string{try{return root.setSetting(key,JSON.parse(value))?"ok":"unknown setting or settings unavailable";}catch(e){return "invalid value";}}
        function place(kind:string,x:string,y:string,vx:string,vy:string):string{return root.place(kind,Number(x),Number(y),Number(vx),Number(vy));}
        function cancelPlacement():void{root.cancelPlacement();}
        function save():void{root.saveMemory();}
        function show():void{root.show();}
        function hide():void{root.hide();}
        function toggle():void{root.toggle();}
    }
}
