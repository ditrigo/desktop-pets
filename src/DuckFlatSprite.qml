pragma ComponentBehavior: Bound
import QtQuick
import "DuckGeometry.js" as Geometry
import "DuckHit.js" as Hit
import "DuckCatalog.js" as Catalog

Item {
    id: flat
    objectName:"flat-renderer"
    required property var bird
    readonly property var modelSpec:Catalog.model(bird.artStyle)
    readonly property var geometry:modelSpec.geometry
    readonly property bool pixel:modelSpec.pixel
    readonly property bool hasHat:!!Catalog.variant("hat",bird.hat,bird.artStyle)
    readonly property bool hasOutfit:!!Catalog.variant("outfit",bird.outfit,bird.artStyle)
    readonly property string outfitLayer:Catalog.layer(bird.outfit,bird.artStyle)
    readonly property string view:bird.front?"front":bird.quarter?"threeQuarter":"side"
    readonly property real headX:flat.geometry.headAnchors[view][0]
    readonly property real headY:flat.geometry.headAnchors[view][1]+(bird.asleep?10:0)
    readonly property string restSuffix:bird.asleep?"-sleep":""
    readonly property bool uniform:outfitLayer==="uniform"
    function part(name){return Catalog.part(bird.artStyle,name,bird.hat,bird.outfit,view);}
    function contour(item,zone,name,local){
        let spec=part(name),rect=spec.placement;
        return Hit.polygon(item,zone,spec.hull.map(function(p){return [(local?0:rect[0])+p[0]*rect[2]/spec.size[0],(local?0:rect[1])+p[1]*rect[3]/spec.size[1]];}));
    }
    function interactionShapes() {
        let shapes=[contour(headRig,"head",bird.plumage+"-head-"+view+(hasHat?"-covered":""),false)];
        if(hasHat)shapes.push(contour(headRig,"head","hat-"+bird.hat+"-"+view,false));
        shapes.push(contour(nearWing,"wing",bird.plumage+"-wing-"+(nearWing.frontal?"front":"side"),false));
        if(farWing.visible)shapes.push(contour(farWing,"wing",bird.plumage+"-wing-front",false));
        shapes.push(contour(bodyRig,"belly",bird.plumage+"-body-"+view+restSuffix,false));
        if(hasOutfit){
            if(neckLoader.item)shapes.push(contour(neckLoader.item,"belly","neck-"+bird.outfit+"-"+view,true));
            if(outfitLayer==="back"&&capeLoader.item)shapes.push(contour(capeLoader.item,"belly","outfit-"+bird.outfit+"-"+view+restSuffix,true));
            else if(uniform)shapes.push(contour(bodyRig,"belly","outfit-"+bird.outfit+"-"+view+restSuffix,false));
        }
        for(let i=0;i<feet.count;i++){const foot=feet.itemAt(i) as Foot;if(foot)shapes.push(Hit.oval(foot,"belly",foot.fx+4,foot.fy+4,10,5));}
        return shapes;
    }
    function hitRegion(x,y){return Hit.region(interactionShapes(),flat,x,y);}
    function inputPolygons(target){return Hit.polygons(interactionShapes(),target);}
    component Part:Image {
        required property string partName
        readonly property var art:flat.part(partName)
        readonly property real artScaleX:art.placement[2]/art.size[0]
        readonly property real artScaleY:art.placement[3]/art.size[1]
        x:art.placement[0]+(partName.indexOf("eyes-")===0?flat.bird.gaze:0)
        y:art.placement[1]
        width:art.placement[2];height:art.placement[3]
        source:Qt.resolvedUrl(art.path)
        smooth:!flat.pixel
        sourceSize:flat.pixel?Qt.size(0,0):Qt.size(Math.ceil(width*3),Math.ceil(height*3))
    }
    component Wing:Item {
        id:wing
        objectName:far?"flat-far-wing":"flat-near-wing"
        required property bool far
        readonly property bool frontal:flat.bird.front||far
        x:(far?flat.geometry.farWing:flat.geometry.nearWing)[flat.view][0]
        y:(far?flat.geometry.farWing:flat.geometry.nearWing)[flat.view][1]+(flat.bird.asleep?12:0)
        visible:!far||flat.bird.front||flat.bird.quarter
        scale:far&&!flat.bird.front?.7:1
        transform:[Scale{xScale:wing.far?-1:1;},Rotation{angle:flat.bird.flap*180/Math.PI;}]
        Part {partName:flat.bird.plumage+"-wing-"+(wing.frontal?"front":"side");}
        Loader {
            active:flat.uniform
            sourceComponent:Component{Part{objectName:wing.far?"flat-sleeve-far":"flat-sleeve-near";partName:"sleeve-"+flat.bird.outfit+"-"+(wing.frontal?"front":"side");}}
        }
    }
    component Foot:Item {
        required property int index
        readonly property real phase:flat.bird.stride+index*Math.PI
        readonly property real fx:flat.geometry.feetX[index]+(flat.bird.stepMix>0?Math.sin(phase)*6*flat.bird.stepMix:0)
        readonly property real fy:flat.bird.flying||flat.bird.mode==="drag"?92+Math.sin(flat.bird.t*15+index*Math.PI)*3:flat.geometry.feetY-(flat.bird.stepMix>0?Math.max(0,Math.cos(phase))*3*flat.bird.stepMix:0)
        Rectangle{x:parent.fx-1;y:flat.geometry.legTop;width:3;height:Math.max(1,parent.fy-flat.geometry.legTop);radius:flat.pixel?0:1.5;color:"#c58a42";}
        Part{x:parent.fx-6;y:parent.fy;width:flat.geometry.footSize[0];height:flat.geometry.footSize[1];partName:"foot";}
    }
    Item {
        width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
        transform:Scale{xScale:flat.width/Geometry.data.canvas[0];yScale:flat.height/Geometry.data.canvas[1];}
        Image{x:22;y:101;width:72;height:7;source:Qt.resolvedUrl("assets/duck/shadow.svg");sourceSize:Qt.size(144,14);}
        Item {
            width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
            transform:Scale{origin.x:Geometry.data.rig.mirrorX;xScale:(flat.bird.direction<0?-1:1)*flat.bird.turnScale;}
            Item {
                id:bodyRig
                width:Geometry.data.canvas[0];height:Geometry.data.canvas[1];y:-flat.bird.bounce
                transform:[
                    Scale{origin.x:Geometry.data.rig.groundPivot[0];origin.y:Geometry.data.rig.groundPivot[1];xScale:1+flat.bird.squash*.5-flat.bird.stretch*.3;yScale:1-flat.bird.squash+flat.bird.stretch;},
                    Rotation{origin.x:Geometry.data.rig.rotationPivot[0];origin.y:Geometry.data.rig.rotationPivot[1];angle:flat.bird.reducedMotion?0:flat.bird.mode==="drag"?(Math.sin(flat.bird.t*8)*.08+flat.bird.swing*.25)*180/Math.PI:flat.bird.mode==="shake"?Math.sin(flat.bird.t*26)*.08*180/Math.PI:0;}
                ]
                Loader {
                    id:capeLoader
                    active:flat.outfitLayer==="back"
                    sourceComponent:Component{Part{id:capeWear;transform:Rotation{origin.x:(flat.bird.front?60:70)-capeWear.x;origin.y:(flat.bird.asleep?72:60)-capeWear.y;angle:flat.bird.clothAngle*.5;}partName:"outfit-"+flat.bird.outfit+"-"+flat.view+flat.restSuffix;}}
                }
                Wing{id:farWing;far:true;}
                Repeater {
                    id:feet
                    model:2
                    delegate:Foot {}
                }
                Part {partName:flat.bird.plumage+"-body-"+flat.view+flat.restSuffix;}
                Loader {
                    active:flat.uniform
                    sourceComponent:Component{Part{partName:"outfit-"+flat.bird.outfit+"-"+flat.view+flat.restSuffix;}}
                }
                Wing{id:nearWing;far:false;}
                Item {
                    id:headRig
                    objectName:"flat-head"
                    x:flat.headX;y:flat.headY
                    rotation:Math.min(flat.hasHat?.6:1,flat.bird.tilt)*180/Math.PI
                    Part{partName:flat.bird.plumage+"-head-"+flat.view+(flat.hasHat?"-covered":"");}
                    Loader {
                        id:neckLoader
                        active:flat.hasOutfit
                        sourceComponent:Component{Part{id:neckWear;objectName:"flat-neckwear";transform:Rotation{origin.x:(flat.bird.front?30:34)*neckWear.artScaleX;origin.y:50*neckWear.artScaleY;angle:flat.bird.clothAngle;}partName:"neck-"+flat.bird.outfit+"-"+flat.view;}}
                    }
                    Part{partName:"eyes-"+flat.view+"-"+(flat.bird.eyesClosed?"closed":flat.bird.mode==="surprise"?"wide":"open");}
                    Loader {
                        active:flat.hasHat
                        sourceComponent:Component{Part{objectName:"flat-hat";partName:"hat-"+flat.bird.hat+"-"+flat.view;}}
                    }
                }
            }
        }
        DuckEffects{anchors.fill:parent;bird:flat.bird;}
    }
}
