import QtQuick
import QtTest
import "../src" as Pet
import "../src/PetModel.js" as Model

Item {
    id: root
    width: 400; height: 300
    QtObject {
        id: backend
        property var actions: []
        function action(name) {actions.push(name);}
        function say(message) {}
        function sayKey(key) {}
    }
    QtObject {
        id: state
        property bool runnable:true
        property bool dragging:false
        property bool pressedVisual:false
        property bool moved:false
        property bool doubleClickPending:false
        property string petRegion:""
        property var controller:backend
        property var bird:Model.create(400,300,76)
        property var cfg:Model.settings({})
        property int birdDirection:1
        property string birdView:"side"
        property string birdMode:"idle"
        property int width:400
        property var perches:[{id:"floor",base:"floor",left:38,right:362,y:294,origin:0}]
        property var contentItem:root
        property point pressPosition:Qt.point(0,0)
        property point previousPosition:Qt.point(0,0)
        property point pressBird:Qt.point(0,0)
        property double previousTime:0
        property real throwVelocity:0
        property double hoverTime:0
        property point hoverPosition:Qt.point(0,0)
        property real strokeDistance:0
        property double lastStroke:0
        property int clicks:0
        function inputRegion(x,y){return birdSprite.hitRegion(x,y);}
        function ensureBird() {}
        function sync() {}
        function cancelClick() {}
        function scheduleClick() {clicks++;}
        function cancelInteraction() {pressedVisual=false;dragging=false;}
    }
    Rectangle {
        width:200;height:180;color:"transparent"
        Pet.PetSprite{id:birdSprite;width:200;height:180;artStyle:state.cfg.artStyle;hat:state.cfg.hat;view:state.birdView;mode:state.birdMode;direction:state.birdDirection;animate:false;}
        Pet.PetInput {id:input;birdScene:state;}
    }
    TestCase {
        name:"PetInput"
        when:windowShown
        function init() {
            birdSprite.width=200;birdSprite.height=180;
            state.bird=Model.create(400,300,76);state.dragging=false;state.pressedVisual=false;state.moved=false;state.doubleClickPending=false;
            state.clicks=0;state.runnable=true;backend.actions=[];state.birdDirection=1;state.birdView="side";state.birdMode="idle";state.cfg=Model.settings({});
        }
        function test_anatomical_head_zones_data(){
            var rows=[];for(var style of ["vector","pixel","voxel"])for(var view of ["side","threeQuarter","front"])rows.push({tag:style+"-"+view,style:style,view:view});return rows;
        }
        function test_anatomical_head_zones(data){
            state.cfg=Model.settings({artStyle:data.style,hat:"wizard"});state.birdView=data.view;wait(30);
            var head=findChild(birdSprite,data.style==="voxel"?"blender-head":"flat-head");verify(head);
            var studio=data.style==="voxel"?findChild(birdSprite,"blender-renderer"):null;
            for(var direction of [1,-1])for(var mode of ["idle","sleep","eat"]){
                state.birdDirection=direction;state.birdMode=mode;wait(5);
                var cx=studio?studio.faceCenter[0]:0,cy=studio?studio.faceCenter[1]:-21;
                for(var dx of [-10,10]){
                    var p=head.mapToItem(input,cx+dx,cy);compare(input.region(p.x,p.y),"head","both cheeks: "+mode+" "+direction);
                }
            }
        }
        function test_silhouette_data(){return test_anatomical_head_zones_data();}
        function test_silhouette(data){
            state.cfg=Model.settings({artStyle:data.style,hat:"wizard"});state.birdView=data.view;wait(25);
            for(var factor of [.6,1,1.4])for(var direction of [1,-1])for(var mode of ["idle","walk","fly","sleep","eat","drag","land"]){
                birdSprite.width=200*factor;birdSprite.height=180*factor;
                state.birdDirection=direction;state.birdMode=mode;wait(5);
                compare(birdSprite.hitRegion(1,1),"","transparent corner "+mode);
                var shapes=birdSprite.activeRenderer.interactionShapes();
                for(var shape of shapes){
                    var x=shape.x,y=shape.y;
                    if(shape.points){if(!shape.points.length)continue;x=0;y=0;for(var point of shape.points){x+=point[0]/shape.points.length;y+=point[1]/shape.points.length;}}
                    var p=shape.item.mapToItem(birdSprite,x,y);verify(birdSprite.hitRegion(p.x,p.y)!=="","figure centre covered "+shape.zone);
                }
                verify(birdSprite.inputPolygons(root).length>=5);
            }
        }
        function test_release_outside_and_cancel(){
            mousePress(input,100,90,Qt.LeftButton);mouseMove(input,350,250);verify(state.dragging);
            mouseRelease(input,350,250,Qt.LeftButton);compare(state.bird.mode,"fall");verify(!state.dragging);
            mousePress(input,100,90,Qt.LeftButton);state.cancelInteraction();mouseRelease(input,300,250,Qt.LeftButton);compare(state.clicks,0);
        }
        function test_press_feedback_without_drag() {
            mousePress(input,100,90,Qt.LeftButton);
            compare(state.pressedVisual,true);compare(state.dragging,false);compare(state.bird.mode,"wave");
            mouseRelease(input,100,90,Qt.LeftButton);
            compare(state.pressedVisual,false);compare(state.clicks,1);compare(state.dragging,false);
        }
        function test_drag_threshold_and_release() {
            mousePress(input,100,90,Qt.LeftButton);
            mouseMove(input,102,91);compare(state.dragging,false);
            mouseMove(input,135,115);compare(state.dragging,true);compare(state.bird.mode,"drag");
            mouseRelease(input,135,115,Qt.LeftButton);
            compare(state.dragging,false);compare(state.bird.mode,"fall");compare(state.clicks,0);
        }
        function test_suspended_scene_cannot_start_drag() {
            state.runnable=false;mousePress(input,100,90,Qt.LeftButton);mouseMove(input,140,120);
            compare(state.dragging,false);compare(state.pressedVisual,false);mouseRelease(input,140,120,Qt.LeftButton);
        }
        function test_secondary_buttons() {
            mouseClick(input,100,90,Qt.MiddleButton);compare(backend.actions[0],"treat");
        }
        function test_double_click_hops() {
            mouseDoubleClickSequence(input,100,90,Qt.LeftButton);
            compare(backend.actions[0],"hop");
        }
    }
}
