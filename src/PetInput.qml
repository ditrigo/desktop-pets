import QtQuick
import "PetModel.js" as Model

MouseArea {
    id: mouse
    required property var birdScene
    readonly property var styleHints: Qt.styleHints
    anchors.fill:parent
    acceptedButtons:Qt.LeftButton|Qt.RightButton|Qt.MiddleButton
    hoverEnabled:true
    cursorShape:birdScene.dragging?Qt.ClosedHandCursor:Qt.OpenHandCursor
    preventStealing:true

    function region(x,y) {return birdScene.inputRegion(x,y);}
    onEntered: {birdScene.hoverTime=Date.now();birdScene.strokeDistance=0;}
    onPressed:function(event) {
        if(!region(event.x,event.y)){event.accepted=false;return;}
        if(event.button!==Qt.LeftButton||!birdScene.runnable)return;
        birdScene.cancelClick();birdScene.doubleClickPending=false;birdScene.ensureBird();if(!birdScene.bird)return;
        birdScene.petRegion=region(event.x,event.y);
        if(!birdScene.petRegion){event.accepted=false;return;}
        birdScene.pressPosition=mapToItem(birdScene.contentItem,event.x,event.y);birdScene.previousPosition=birdScene.pressPosition;
        birdScene.pressBird=Qt.point(birdScene.bird.x,birdScene.bird.y);birdScene.previousTime=Date.now();
        birdScene.throwVelocity=0;birdScene.moved=false;birdScene.pressedVisual=true;
    }
    onPositionChanged:function(event) {
        var p=mapToItem(birdScene.contentItem,event.x,event.y),now=Date.now();
        if(!birdScene.pressedVisual&&!birdScene.dragging) {
            if(!birdScene.runnable)return;
            const dist=Math.hypot(p.x-birdScene.hoverPosition.x,p.y-birdScene.hoverPosition.y),elapsed=Math.max(.016,(now-birdScene.hoverTime)/1000);
            if(region(event.x,event.y)==="head"&&dist/elapsed<1000)birdScene.strokeDistance+=Math.min(dist,12);else birdScene.strokeDistance=0;
            if(birdScene.strokeDistance>birdScene.cfg.size*.65&&now-birdScene.lastStroke>1600){birdScene.controller.action("head");birdScene.lastStroke=now;birdScene.strokeDistance=0;}
            birdScene.hoverPosition=p;birdScene.hoverTime=now;return;
        }
        var dx=p.x-birdScene.pressPosition.x,dy=p.y-birdScene.pressPosition.y;
        if(!birdScene.dragging&&Math.hypot(dx,dy)<styleHints.startDragDistance)return;
        if(!birdScene.dragging){birdScene.dragging=true;birdScene.moved=true;Model.enter(birdScene.bird,"drag",10);}
        birdScene.bird.x=Model.clamp(birdScene.pressBird.x+dx,birdScene.cfg.size/2,(birdScene.worldWidth||birdScene.width)-birdScene.cfg.size/2);
        birdScene.bird.y=Model.clamp(birdScene.pressBird.y+dy,birdScene.cfg.size,birdScene.perches[0].y);
        birdScene.throwVelocity=Model.clamp((p.x-birdScene.previousPosition.x)/Math.max(.016,(now-birdScene.previousTime)/1000),-320,320);
        birdScene.previousPosition=p;birdScene.previousTime=now;birdScene.sync();
    }
    onReleased:function(event) {
        if(!birdScene.controller)return;
        if(event.button===Qt.RightButton){birdScene.controller.show();return;}
        if(event.button===Qt.MiddleButton){birdScene.controller.action("treat");return;}
        if(!birdScene.pressedVisual&&!birdScene.dragging)return;
        birdScene.pressedVisual=false;
        if(birdScene.dragging) {
            birdScene.dragging=false;Model.detach(birdScene.bird);Model.enter(birdScene.bird,"fall",10);
            birdScene.bird.vy=0;birdScene.bird.vx=Date.now()-birdScene.previousTime<150?birdScene.throwVelocity:0;
            birdScene.bird.manualUntil=birdScene.bird.age+8;birdScene.controller.sayKey("speech.whee");birdScene.sync();
        }else if(birdScene.doubleClickPending){birdScene.doubleClickPending=false;birdScene.controller.action("hop");}
        else birdScene.scheduleClick();
    }
    onCanceled:birdScene.cancelInteraction()
    onDoubleClicked: {birdScene.cancelClick();birdScene.doubleClickPending=true;}
    onWheel:if(birdScene.controller)birdScene.controller.action("quack")
}
