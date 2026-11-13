pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Wayland
import "DuckModel.js" as Model

// Quickshell creates this through its platform factory; qmltypes lists only the abstract interface.
PanelWindow { // qmllint disable uncreatable-type
    id: scene
    DuckTranslations { id: strings }
    property var controller: null
    property var targetScreen: null
    screen: targetScreen
    readonly property real worldWidth: targetScreen ? targetScreen.width : 0
    readonly property real worldHeight: targetScreen ? targetScreen.height : 0
    readonly property var cfg: controller ? controller.config : Model.defaults
    readonly property var monitor: {
        let list=controller?controller.monitors:[];
        for(let i=0;i<list.length;i++)if(targetScreen&&list[i].name===targetScreen.name)return list[i];
        return null;
    }
    readonly property var perches: Model.surfaces(monitor,controller?controller.clients:[],worldWidth,worldHeight,cfg.size,cfg.walkOnWindows)
    readonly property bool fullscreenApp: {
        if(!monitor||!controller)return false;
        let workspace=monitor.specialWorkspace&&monitor.specialWorkspace.id||monitor.activeWorkspace.id;
        return controller.clients.some(function(c){return c.monitor===monitor.id&&(c.pinned||c.workspace&&c.workspace.id===workspace)&&c.mapped&&!c.hidden&&c.fullscreen>0;});
    }
    readonly property bool runnable: visible&&!!controller&&controller.runState==="active"
    readonly property bool placing: visible&&!!controller&&controller.placement!==""&&controller.placementMonitor===targetScreen.name
    property var bird: null
    property real birdX: worldWidth*.72
    property real birdY: worldHeight-6
    property string birdMode: "wave"
    property int birdDirection: -1
    property string birdView: "threeQuarter"
    property real stride: 0
    property real gaze: 0
    property real modeTime: 0
    property real visualClock: 0
    property bool blinking: false
    property bool framesWanted: false
    property bool windowTracking: false
    property real accumulator: 0
    property double lastSlow: 0
    property double lastStatus: 0
    property double lastMemory: 0
    property int handledEvent: 0
    property int ticks: 0
    property int droppedSteps: 0
    property real maxStepMs: 0
    property var frameIntervals: []
    readonly property var styleHints: Qt.styleHints
    property var items: []
    property int itemRevision: 0
    property string itemSignature: ""
    property int nextItem: 0
    // A revision makes mutations inside the simulation's plain JS objects observable.
    readonly property var itemSnapshot: ({revision:itemRevision,values:items})
    readonly property var ball: itemSnapshot.values.find(function(item){return item.type==="ball"&&!item.consumed;})||null
    property bool dragging: false
    property bool pressedVisual: false
    property bool holdingBall: false
    readonly property bool inputHeld: dragging||pressedVisual||holdingBall
    property bool moved: false
    property bool doubleClickPending: false
    property string petRegion: "head"
    property point pressPosition: Qt.point(0,0)
    property point pressBird: Qt.point(0,0)
    property point previousPosition: Qt.point(0,0)
    property double previousTime: 0
    property real throwVelocity: 0
    property point hoverPosition: Qt.point(0,0)
    property double hoverTime: 0
    property real strokeDistance: 0
    property double lastStroke: 0
    property bool lastWorkMode: false
    property bool lastReduced: false
    property bool wasVisible: false
    property point placementStart: Qt.point(0,0)
    property point ghost: Qt.point(worldWidth/2,worldHeight/2)
    property point ballPrevious: Qt.point(0,0)
    property double ballTime: 0
    property real ballVX: 0
    property real ballVY: 0
    property var seenWindows: ({})
    property bool surveyed: false
    property string pendingExplore: ""

    anchors {left:true;right:true;top:true;bottom:true}
    color:"transparent"
    exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"ditrigo-desktop-duck"
    WlrLayershell.layer:WlrLayer.Top
    WlrLayershell.keyboardFocus:placing?WlrKeyboardFocus.Exclusive:WlrKeyboardFocus.None
    visible:!!controller&&controller.ready&&!!targetScreen&&controller.monitorName===targetScreen.name&&cfg.enabled
        &&controller.runState!=="locked"&&controller.runState!=="display-off"&&!(cfg.hideFullscreen&&fullscreenApp)
    mask:Region {
        width:scene.placing?scene.worldWidth:0;height:scene.placing?scene.worldHeight:0
        // Full capture only for an active press/drag; cancellation restores the silhouette.
        Region {width:scene.inputHeld?scene.worldWidth:0;height:scene.inputHeld?scene.worldHeight:0}
        DuckSilhouette {id:silhouette;birdSprite:sprite;target:scene.contentItem;}
        Region {x:ballItem.x;y:ballItem.y;width:scene.ball?ballItem.width:0;height:scene.ball?ballItem.height:0}
    }
    function inputRegion(x,y){let p=sprite.mapFromItem(duckInput,x,y);return sprite.hitRegion(p.x,p.y);}
    function updateMask(){if(sprite.activeRenderer)silhouette.update();}
    function world() {return {width:worldWidth,height:worldHeight,surfaces:perches,items:items,
        favorite:controller&&targetScreen?controller.profile.favorites[targetScreen.name]:null,
        favoriteHandle:controller&&targetScreen?controller.favoriteHandles[targetScreen.name]:"",
        resting:controller?controller.resting:false,
        cursor:controller&&controller.cursor&&monitor?{x:controller.cursor.x-monitor.x,y:controller.cursor.y-monitor.y,dt:controller.cursor.dt,sequence:controller.cursor.sequence}:null};}
    function ensureBird() {
        if(bird||!controller||!targetScreen||!controller.ready)return;
        if(worldWidth<1||worldHeight<1)return;
        let saved=controller.profile.positions[targetScreen.name];
        bird=Model.create(worldWidth,worldHeight,cfg.size,saved,controller.profile);
        if(cfg.reducedMotion)Model.enter(bird,"idle",8);
        if(saved&&saved.edge==="window"&&saved.app) {
            let target=Model.homeTarget(world(),cfg,saved),p=Model.surfaceById(perches,target.surface);
            bird.x=target.x;bird.y=target.y;Model.attach(bird,p);
        }
        lastWorkMode=cfg.workMode;lastReduced=cfg.reducedMotion;
    }
    function sync() {
        if(!bird)return;
        birdX=Math.round(bird.x*4)/4;birdY=Math.round(bird.y*4)/4;birdMode=bird.mode;birdDirection=bird.direction;
        birdView=bird.view;stride=bird.stride;gaze=cfg.reducedMotion?0:bird.gaze;modeTime=bird.modeTime;
        if(!cfg.reducedMotion&&bird.mode!=="idle"&&bird.mode!=="sleep")visualClock=bird.age;
        maskUpdate.restart();
        let w=world();framesWanted=Model.needsFrames(bird,items,w,cfg);
        windowTracking=bird.surface!=="floor"&&!!bird.surface||items.some(function(o){return !!o.surface&&o.surface!=="floor";})||bird.mode==="fly";
        let signature=JSON.stringify(items.map(function(o){return [o.id,o.consumed,Math.round(o.x*4),Math.round(o.y*4),Math.round(o.rotation*10),o.held];}));
        if(signature!==itemSignature){itemSignature=signature;itemRevision++;}
        let now=Date.now();
        if(visible&&controller&&(now-lastStatus>(controller.opened?200:1000)||controller.runtime.mode!==bird.mode)) {
            controller.runtime={x:Math.round(bird.x),y:Math.round(bird.y),mode:bird.mode,surface:bird.surface,
                priority:Model.priority(bird,w,cfg),perches:perches.length,view:bird.view,direction:bird.direction,phase:bird.modeTime,animationClock:visualClock,goal:bird.goal,mood:Model.mood(bird,controller.resting),
                energy:Math.round(bird.energy),satiety:Math.round(bird.satiety),trust:Math.round(bird.trust),
                items:items.map(function(o){return {id:o.id,type:o.type,x:Math.round(o.x),y:Math.round(o.y),surface:o.surface};})};
            lastStatus=now;
        }
        if(visible&&controller&&now-lastMemory>1000){controller.report(targetScreen.name,bird,w);lastMemory=now;}
        if(controller&&bird.eventSerial!==handledEvent){handledEvent=bird.eventSerial;controller.react(bird.event);}
    }
    function advance(elapsed) {
        ensureBird();if(!bird)return;
        let start=Date.now(),w=world(),steps=1,dt=Math.min(5,elapsed);
        if(framesWanted) {
            accumulator+=elapsed;
            if(accumulator>8/60){droppedSteps+=Math.floor((accumulator-8/60)*60);accumulator=8/60;}
            steps=Math.floor((accumulator+.000001)*60);if(!steps)return;
            dt=1/60;accumulator=Math.max(0,accumulator-steps*dt);
        }
        for(let n=0;n<steps;n++) {
            let alive=Model.stepItems(items,dt,w);
            if(alive.length!==items.length){items=alive;w.items=items;}
            Model.step(bird,dt,w,cfg,Math.random);
        }
        ticks++;maxStepMs=Math.max(maxStepMs,Date.now()-start);sync();
    }
    function metrics() {
        let intervals=frameIntervals.slice().sort(function(a,b){return a-b;});
        return {ticks:ticks,poseUpdates:sprite.poseUpdates,paints:sprite.paintCount,renderer:sprite.renderer,droppedSteps:droppedSteps,maxStepMs:maxStepMs,framesWanted:framesWanted,items:items.length,worldWidth:worldWidth,worldHeight:worldHeight,
            frameSamples:intervals.length,frameIntervalP95Ms:intervals.length?intervals[Math.min(intervals.length-1,Math.floor(intervals.length*.95))]:0};
    }
    function spawn(kind,x,y,vx,vy) {
        ensureBird();if(!bird)return false;
        let retained=items.filter(function(o){return !o.consumed&&(kind!=="ball"||o.type!=="ball");});
        if(retained.length>=8)retained=retained.slice(-7);
        let o=Model.item(kind,Model.clamp(x,12,worldWidth-12),Model.clamp(y,35,worldHeight-12),vx,vy,String(++nextItem));
        items=retained.concat([o]);
        if(!Model.targetItem(bird,world()))Model.notice(bird,o);
        bird.manualUntil=bird.age+15;sync();return true;
    }
    function clearItems() {
        items=[];
        if(bird) {
            bird.goal="";bird.targetItem="";
            if(bird.next==="consume"||["eat","eatGoal","sniff","notice","nudge"].indexOf(bird.mode)>=0)Model.enter(bird,"idle",1);
        }
        sync();
    }
    function perform(name) {
        ensureBird();if(!bird)return "blocked: not ready";
        if(dragging)return "blocked: dragging";
        if(name==="reset"){bird=Model.create(worldWidth,worldHeight,cfg.size,null,controller.profile);items=[];handledEvent=0;}
        else if(name==="treat")return spawn("pea",bird.x+bird.direction*cfg.size*.8,bird.y-cfg.size*1.5,0,0)?"ok":"blocked: not ready";
        else if((name==="pet"||name==="head")&&controller.resting&&bird.mode==="sleep") {
            bird.trust=Model.clamp(bird.trust+2,0,100);Model.emit(bird,"pet");
        }else if(name==="home"||name==="rest"){bird.manualUntil=0;Model.goHome(bird,world(),cfg);}
        else if(name==="come") {
            let p=world().cursor,floor=perches[0];bird.goal="travel";bird.manualUntil=bird.age+8;
            Model.flyTo(bird,{x:p?p.x:worldWidth/2,y:floor.y,surface:floor.id});
        }else if(name==="perch") {
            let p2=perches.length>1?perches[1+Math.floor(Math.random()*(perches.length-1))]:perches[0];
            bird.goal="explore";bird.manualUntil=bird.age+8;Model.flyTo(bird,{x:(p2.left+p2.right)/2,y:p2.y,surface:p2.id});
        }else Model.act(bird,name);
        sync();return "ok";
    }
    function applyChanges() {
        ensureBird();if(!bird)return;
        if(visible) {
            if(!wasVisible){bird.trust=controller.profile.trust;bird.energy=controller.profile.energy;bird.satiety=controller.profile.satiety;bird.fed=controller.profile.fed;}
            wasVisible=true;
            if(cfg.reducedMotion&&!lastReduced&&bird.surface)Model.enter(bird,"idle",8);
            if(lastWorkMode!==cfg.workMode){lastWorkMode=cfg.workMode;bird.manualUntil=0;if(cfg.workMode&&runnable)Model.goHome(bird,world(),cfg);}
            lastReduced=cfg.reducedMotion;
            sync();
        }
        let seen=({}),fresh="";
        perches.forEach(function(p){if(p.window){seen[p.window]=true;if(!scene.seenWindows[p.window])fresh=p.window;}});
        if(surveyed&&fresh){pendingExplore=fresh;exploreDelay.restart();}
        seenWindows=seen;surveyed=true;
        if(placing)placementFocus.forceActiveFocus();
    }
    function cancelInteraction() {
        clickTimer.stop();pressedVisual=false;doubleClickPending=false;
        if(bird&&dragging){Model.detach(bird);Model.enter(bird,"fall",10);bird.vy=0;bird.vx=0;}
        dragging=false;holdingBall=false;
        if(ball&&ball.held){ball.held=false;ball.surface="";ball.vy=0;itemRevision++;}
        accumulator=0;sync();
    }
    function scheduleClick(){clickTimer.restart();}
    function cancelClick(){clickTimer.stop();}
    onCfgChanged:initialize.restart()
    onPerchesChanged:initialize.restart()
    onPlacingChanged:initialize.restart()
    onVisibleChanged: {if(!visible){wasVisible=false;cancelInteraction();}initialize.restart();}
    onRunnableChanged: {accumulator=0;lastSlow=Date.now();if(!runnable)cancelInteraction();initialize.restart();}
    onFramesWantedChanged: {accumulator=0;lastSlow=Date.now();}
    Component.onCompleted: {if(controller&&targetScreen)controller.registerScene(targetScreen.name,scene);initialize.restart();}
    Component.onDestruction: if(controller&&targetScreen)controller.unregisterScene(targetScreen.name,scene)
    Connections {
        target:scene.controller
        function onCursorChanged(){if(scene.runnable&&scene.bird&&!scene.inputHeld){Model.step(scene.bird,0,scene.world(),scene.cfg,Math.random);scene.sync();}}
    }
    Connections {target:sprite;function onPoseUpdatesChanged(){maskUpdate.restart();}function onScaleChanged(){maskUpdate.restart();}function onActiveRendererChanged(){maskUpdate.restart();}}
    Connections {target:hitbox;function onXChanged(){maskUpdate.restart();}function onYChanged(){maskUpdate.restart();}function onWidthChanged(){maskUpdate.restart();}}
    Timer {id:maskUpdate;interval:0;onTriggered:scene.updateMask();}
    Timer {id:initialize;interval:1;onTriggered:scene.applyChanges();}
    Timer {
        id:exploreDelay;interval:750
        onTriggered: {
            let b=scene.bird;
            if(!b||!scene.runnable||scene.dragging||scene.cfg.personality!=="curious"||scene.cfg.workMode||scene.cfg.reducedMotion||scene.controller.resting||b.age<b.manualUntil||b.age<b.flightAt||b.age<b.initiativeAt||b.goal)return;
            let p=scene.perches.find(function(edge){return edge.window===scene.pendingExplore;});
            if(!p)return;
            b.flightAt=b.age+Model.personalities.curious.flight;b.initiativeAt=b.age+Model.personalities.curious.initiative;
            b.goal="explore";Model.flyTo(b,{x:(p.left+p.right)/2,y:p.y,surface:p.id});scene.sync();
        }
    }
    Timer {id:clickTimer;interval:scene.styleHints.mouseDoubleClickInterval;onTriggered:if(scene.controller)scene.controller.action(scene.petRegion);}
    Timer {
        id:motionClock
        property double previous:0
        interval:scene.dragging||scene.ball&&(!scene.ball.surface||scene.ball.held||Math.abs(scene.ball.vx)>1)?16:33
        running:scene.runnable&&scene.framesWanted
        repeat:true
        onRunningChanged:previous=Date.now()
        onTriggered: {
            let now=Date.now(),elapsed=Math.max(0,(now-previous)/1000);previous=now;
            scene.frameIntervals.push(elapsed*1000);if(scene.frameIntervals.length>1800)scene.frameIntervals.shift();
            scene.advance(elapsed);
        }
    }
    Timer {
        interval:1000;running:scene.runnable&&!scene.framesWanted;repeat:true
        onTriggered:{let now=Date.now(),elapsed=scene.lastSlow?Math.min(5,(now-scene.lastSlow)/1000):1;scene.lastSlow=now;scene.advance(elapsed);}
    }
    Timer {interval:5300;running:scene.runnable&&!scene.cfg.reducedMotion&&scene.birdMode==="idle";repeat:true;onTriggered:{scene.blinking=true;blinkEnd.restart();}}
    Timer {id:blinkEnd;interval:150;onTriggered:scene.blinking=false;}
    Repeater {
        model:scene.items
        delegate:Rectangle {
            required property var modelData
            visible:modelData.type==="pea"&&!modelData.consumed
            readonly property point position: {
                const snapshot=scene.itemSnapshot;
                const item=snapshot.values.find(function(item){return item.id===modelData.id;});
                return Qt.point(item?item.x:0,item?item.y:0);
            }
            x:position.x-5
            y:position.y-5
            width:10;height:10;radius:5;color:"#a6cf66";border.color:"#658d3d";border.width:1
            Rectangle{x:2;y:2;width:3;height:3;radius:2;color:"#dbeda0";}
        }
    }
    Rectangle {
        id:ballItem
        visible:!!scene.ball
        readonly property var pose: {
            const snapshot=scene.itemSnapshot;
            const item=snapshot.values.find(function(item){return item.type==="ball"&&!item.consumed;});
            return item?{x:item.x,y:item.y,rotation:item.rotation}:{x:13,y:13,rotation:0};
        }
        x:pose.x-13
        y:pose.y-13
        width:26;height:26;radius:13;color:"#e79291";border.color:"#aa626b";border.width:1
        rotation:pose.rotation
        Rectangle{x:4;y:3;width:5;height:19;radius:3;color:"#f8d47e";rotation:25;}
        Rectangle{x:16;y:6;width:5;height:15;radius:3;color:"#a4c9cc";rotation:25;}
        MouseArea {
            anchors.fill:parent;cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
            onPressed:function(event){
                if(!scene.runnable||!scene.ball)return;scene.holdingBall=true;scene.ball.held=true;scene.itemRevision++;
                scene.ballPrevious=mapToItem(scene.contentItem,event.x,event.y);scene.ballTime=Date.now();scene.ballVX=0;scene.ballVY=0;
            }
            onPositionChanged:function(event){
                if(!pressed||!scene.runnable||!scene.ball||!scene.holdingBall)return;
                let p=mapToItem(scene.contentItem,event.x,event.y),now=Date.now(),dt=Math.max(.016,(now-scene.ballTime)/1000);
                scene.ballVX=Model.clamp((p.x-scene.ballPrevious.x)/dt,-700,700);scene.ballVY=Model.clamp((p.y-scene.ballPrevious.y)/dt,-700,700);
                scene.ball.x=Model.clamp(p.x,13,scene.worldWidth-13);scene.ball.y=Model.clamp(p.y,35,scene.worldHeight-13);
                scene.ballPrevious=p;scene.ballTime=now;scene.itemRevision++;scene.sync();
            }
            onReleased:{
                if(!scene.holdingBall)return;scene.holdingBall=false;if(!scene.ball)return;scene.ball.held=false;scene.ball.surface="";
                scene.ball.vx=Date.now()-scene.ballTime<180?scene.ballVX:0;
                scene.ball.vy=Date.now()-scene.ballTime<180?scene.ballVY:-240;
                scene.ensureBird();Model.notice(scene.bird,scene.ball);scene.bird.manualUntil=scene.bird.age+15;scene.itemRevision++;scene.sync();scene.sync();
            }
            onCanceled:{scene.holdingBall=false;if(scene.ball){scene.ball.held=false;scene.ball.surface="";scene.ball.vy=0;scene.sync();}}
        }
    }
    Item {
        id:hitbox
        x:scene.birdX-width/2;y:scene.birdY-height
        width:scene.cfg.size;height:scene.cfg.size*112/120
        DuckSprite {
            id:sprite
            anchors.fill:parent
            scale:scene.pressedVisual&&!scene.dragging?.97:1
            clock:scene.visualClock;blink:scene.blinking
            mode:scene.birdMode;direction:scene.birdDirection;plumage:scene.cfg.palette;artStyle:scene.cfg.artStyle;hat:scene.cfg.hat;outfit:scene.cfg.outfit
            view:scene.birdView;stride:scene.stride;gaze:scene.gaze;modeTime:scene.modeTime;swing:scene.throwVelocity/700
            reducedMotion:scene.cfg.reducedMotion
            animate:scene.runnable&&!scene.cfg.reducedMotion
        }
        DuckInput {id:duckInput;parent:scene.contentItem;z:1;birdScene:scene;}

    }
    Rectangle {
        visible:scene.cfg.bubbles&&scene.controller&&scene.controller.bubble!==""&&!scene.placing
        x:Model.clamp(scene.birdX-width/2,8,Math.max(8,scene.worldWidth-width-8));y:Math.max(30,scene.birdY-scene.cfg.size-height-10)
        width:bubbleText.implicitWidth+24;height:bubbleText.implicitHeight+18;radius:12;color:"#f9f2dd";border.color:"#c8ac69"
        Text{id:bubbleText;anchors.centerIn:parent;text:scene.controller?scene.controller.bubble:"";textFormat:Text.PlainText;color:"#594b32";font.family:"sans-serif";font.pixelSize:12;}
    }
    MouseArea {
        id:placementArea
        anchors.fill:parent;z:10;enabled:scene.placing;hoverEnabled:true;acceptedButtons:Qt.LeftButton|Qt.RightButton
        cursorShape:Qt.CrossCursor
        onPressed:function(event){if(event.button===Qt.RightButton){scene.controller.cancelPlacement();return;}scene.placementStart=Qt.point(event.x,event.y);}
        onPositionChanged:function(event){scene.ghost=Qt.point(event.x,event.y);}
        onReleased:function(event){
            if(event.button!==Qt.LeftButton||!scene.placing)return;
            let ball=scene.controller.placement==="ball",dx=event.x-scene.placementStart.x,dy=event.y-scene.placementStart.y;
            scene.controller.place(ball?"ball":"pea",event.x,event.y,ball?Model.clamp(dx*3,-650,650):0,ball?Math.abs(dy)>10?Model.clamp(dy*3,-650,650):-260:0);
        }
    }
    FocusScope {id:placementFocus;anchors.fill:parent;focus:scene.placing;Keys.onEscapePressed:if(scene.placing)scene.controller.cancelPlacement();}
    Rectangle {
        z:12;visible:scene.placing;anchors.horizontalCenter:parent.horizontalCenter;y:46
        width:instructions.implicitWidth+32;height:44;radius:12;color:"#f5edd8";border.color:"#cab579"
        Text{id:instructions;textFormat:Text.PlainText;anchors.centerIn:parent;text:scene.controller&&scene.controller.placement==="pea"?strings.t("placement.pea"):strings.t("placement.ball");color:"#594b32";font.pixelSize:13;}
    }
    Rectangle {
        z:11;visible:scene.placing;x:scene.ghost.x-width/2;y:scene.ghost.y-height/2
        width:scene.controller&&scene.controller.placement==="ball"?22:10;height:width;radius:width/2
        opacity:.75;color:scene.controller&&scene.controller.placement==="ball"?"#e79291":"#a6cf66"
    }
}
