pragma ComponentBehavior: Bound
import QtQuick
import "PetGeometry.js" as Geometry
import "PetAtlas.js" as Atlas
import "PetHit.js" as Hit
import "PetCatalog.js" as Catalog

Item {
    id: studio
    objectName:"blender-renderer"
    required property var bird
    readonly property var modelSpec:Catalog.model(bird.artStyle)
    readonly property var atlas:modelSpec.atlas||Atlas.data
    readonly property var hatArt:Catalog.atlasPart("hat",bird.hat,bird.artStyle)
    readonly property var outfitArt:Catalog.atlasPart("outfit",bird.outfit,bird.artStyle)
    readonly property int viewIndex:bird.view==="front"?2:bird.view==="threeQuarter"?1:0
    readonly property var pivots:studio.atlas.views[bird.view] ? studio.atlas.views[bird.view].pivots : studio.atlas.views.side.pivots
    readonly property var faceCenter:studio.atlas.views[bird.view]&&studio.atlas.views[bird.view].face||[80,42]
    function contour(item,zone,name,pose){let d=studio.atlas.parts[name];return Hit.polygon(item,zone,d.hulls[viewIndex*d.poses+(pose||0)]);}
    function interactionShapes() {
        let shapes=[contour(headRig,"head",bird.plumage+"-head",bird.eyesClosed?1:bird.mode==="surprise"?2:0)];
        if(hatArt)shapes.push(Hit.polygon(headRig,"head",hatArt.spec.hulls[viewIndex*hatArt.spec.poses]));
        for(let side of ["near","far"])shapes.push(contour(bodyRig,"wing",bird.plumage+"-wing."+side,wingPose(bird.flap)));
        shapes.push(contour(bodyRig,"belly",bird.plumage+"-body",0));
        if(outfitArt&&outfitLoader.item){
            let d=outfitArt.spec;
            shapes.push(Hit.polygon(outfitLoader.item,"belly",d.hulls[viewIndex].map(function(p){return [p[0]-d.x,p[1]-d.y];})));
        }
        for(let i=0;i<feet.count;i++){let foot=feet.itemAt(i);shapes.push(contour(foot,"belly",bird.plumage+"-foot."+(i===0?"far":"near"),footPose(bird.stride+(i===0?Math.PI:0))));}
        return shapes;
    }
    function hitRegion(x,y){return Hit.region(interactionShapes(),studio,x,y);}
    function inputPolygons(target){return Hit.polygons(interactionShapes(),target);}
    function wingPose(angle) {let values=studio.atlas.wingAngles,best=0;for(let i=1;i<values.length;i++)if(Math.abs(values[i]-angle)<Math.abs(values[best]-angle))best=i;return best;}
    function footPose(phase) {return bird.flying||bird.mode==="drag"?3:bird.stepMix<=0?1:Math.sin(phase)*bird.stepMix<-.35?0:Math.sin(phase)*bird.stepMix>.35?2:1;}
    component Part:PetAtlasPart {atlasData:studio.atlas;assetRoot:studio.modelSpec.root;}
    Item {
        width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
        transform:Scale{xScale:studio.width/Geometry.data.canvas[0];yScale:studio.height/Geometry.data.canvas[1];}
        Image{x:22;y:100;width:72;height:7;source:Qt.resolvedUrl("assets/duck/shadow.svg");sourceSize:Qt.size(144,14);}
        Item {
            width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
            transform:Scale{origin.x:Geometry.data.rig.mirrorX;xScale:(studio.bird.direction<0?-1:1)*studio.bird.turnScale;}
            Item {
                id:bodyRig
                width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
                y:-studio.bird.bounce
                transform:[
                    Scale{origin.x:Geometry.data.rig.groundPivot[0];origin.y:Geometry.data.rig.groundPivot[1];xScale:1+studio.bird.squash*.5-studio.bird.stretch*.3;yScale:1-studio.bird.squash+studio.bird.stretch;},
                    Rotation{origin.x:Geometry.data.rig.rotationPivot[0];origin.y:Geometry.data.rig.rotationPivot[1];angle:studio.bird.reducedMotion?0:studio.bird.mode==="drag"?(Math.sin(studio.bird.t*8)*.08+studio.bird.swing*.25)*180/Math.PI:studio.bird.mode==="shake"?Math.sin(studio.bird.t*26)*.08*180/Math.PI:0;}
                ]
                Part {id:farWing;partName:studio.bird.plumage+"-wing.far";viewIndex:studio.viewIndex;pose:studio.wingPose(studio.bird.flap);}
                Repeater {
                    id:feet
                    model:["far","near"]
                    delegate:Item {
                        required property string modelData
                        readonly property real phase:studio.bird.stride+(modelData==="far"?Math.PI:0)
                        y:studio.bird.moving&&!studio.bird.reducedMotion?-Math.max(0,Math.cos(phase))*2:0
                        Part{partName:studio.bird.plumage+"-foot."+parent.modelData;viewIndex:studio.viewIndex;pose:studio.footPose(parent.phase);}
                    }
                }
                Part {partName:studio.bird.plumage+"-body";viewIndex:studio.viewIndex;}
                Loader {
                    id:outfitLoader
                    active:!!studio.outfitArt
                    sourceComponent:Component{Part{overrideSpec:studio.outfitArt.spec;assetRoot:studio.outfitArt.root;partName:"outfit."+studio.bird.outfit;viewIndex:studio.viewIndex;rotation:Catalog.layer(studio.bird.outfit,studio.bird.artStyle)==="neck"||Catalog.layer(studio.bird.outfit,studio.bird.artStyle)==="back"?studio.bird.clothAngle*.5:0;transformOrigin:Item.Top;}}
                }
                Part {id:nearWing;partName:studio.bird.plumage+"-wing.near";viewIndex:studio.viewIndex;pose:studio.wingPose(studio.bird.flap);}
                Item {
                    id:headRig
                    objectName:"blender-head"
                    width:Geometry.data.canvas[0];height:Geometry.data.canvas[1]
                    x:studio.bird.gaze*.35;y:studio.bird.asleep?3:0
                    transform:Rotation{origin.x:studio.pivots.head[0];origin.y:studio.pivots.head[1];angle:studio.bird.tilt*180/Math.PI;}
                    Part {partName:studio.bird.plumage+"-head";viewIndex:studio.viewIndex;pose:studio.bird.eyesClosed?1:studio.bird.mode==="surprise"?2:0;}
                    Loader {
                        active:!!studio.hatArt
                        sourceComponent:Component{Part{overrideSpec:studio.hatArt.spec;assetRoot:studio.hatArt.root;partName:"hat."+studio.bird.hat;viewIndex:studio.viewIndex;}}
                    }
                }
            }
        }
        PetEffects {anchors.fill:parent;bird:studio.bird;}
    }
}
