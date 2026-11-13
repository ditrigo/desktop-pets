pragma ComponentBehavior: Bound
import QtQuick
import "DuckGeometry.js" as Geometry
import "DuckCatalog.js" as Catalog

// SVG parts and Blender PNG atlases are cached as textures. Existing scene
// timing drives poses; neither renderer owns a timer or a JavaScript Canvas.
Item {
    id: duck
    property string mode: "idle"
    property string plumage: "yellow"
    property string artStyle: "vector"
    property string hat: "none"
    property string outfit: "none"
    property int direction: 1
    property bool reducedMotion: false
    property real clock: 0
    property bool animate: visible
    property string view: "side"
    property real stride: 0
    property real gaze: 0
    property real modeTime: 0
    property real swing: 0
    property bool blink: false
    property int poseUpdates: 0
    readonly property int paintCount: poseUpdates
    readonly property var modelSpec:Catalog.model(artStyle)
    readonly property string renderer:modelSpec.renderer==="atlas"?"blender-atlas":modelSpec.pixel?"pixel-parts":"svg-parts"
    implicitWidth:Geometry.data.canvas[0]
    implicitHeight:Geometry.data.canvas[1]
    readonly property real t:animate&&!reducedMotion&&mode!=="idle"&&mode!=="sleep"?clock:0
    readonly property bool moving:mode==="walk"
    readonly property real stepMix:reducedMotion?0:moving?1:mode==="settle"?Math.max(0,1-modeTime/.18):0
    readonly property real turnScale:mode==="turn"&&!reducedMotion?1-.18*Math.sin(Math.min(1,modeTime/.22)*Math.PI):1
    readonly property real clothAngle:reducedMotion||mode==="idle"||asleep?0:mode==="walk"?Math.sin(stride-0.6)*2.2:mode==="land"?Math.sin(Math.min(1,modeTime/.3)*Math.PI)*3:mode==="drag"?Math.sin(t*8-.5)*3:Math.sin(t*3)*1.2
    readonly property bool flying:mode==="fly"||mode==="fall"
    readonly property bool asleep:mode==="sleep"
    readonly property bool happy:mode==="love"||mode==="dance"||mode==="giggle"
    readonly property bool front:view==="front"
    readonly property bool quarter:view==="threeQuarter"
    readonly property bool eyesClosed:asleep||happy||blink||t%5.3>5.12
    readonly property real squash:reducedMotion?0:mode==="anticipate"?.18*Math.sin(Math.min(1,modeTime/.24)*Math.PI/2):mode==="land"?.24*Math.max(0,1-modeTime/.3):0
    readonly property real stretch:reducedMotion?0:mode==="stretch"?Math.sin(Math.min(1,modeTime/.8)*Math.PI)*.2:mode==="drag"?.13*Math.min(1,modeTime/.25):0
    readonly property real bounce:reducedMotion||mode==="idle"||asleep?0:moving?Math.abs(Math.sin(stride))*3:mode==="dance"||mode==="giggle"?Math.abs(Math.sin(t*9))*9:Math.sin(t*2)*1.3
    readonly property real flap:reducedMotion?.18:mode==="land"?.18-.55*Math.max(0,1-modeTime/.3):mode==="anticipate"?.18-.4*Math.min(1,modeTime/.24):flying||mode==="drag"&&modeTime>.35?-.6+Math.sin(t*24)*.85:mode==="wave"||mode==="dance"?-.45+Math.sin(t*12)*.6:.18
    readonly property real tilt:asleep?.6:mode==="preen"?.8+Math.sin(t*6)*.3:mode==="eat"?.6+Math.sin(t*10)*.3:mode==="peek"?.55:mode==="sniff"||mode==="nudge"?.35:mode==="look"||mode==="notice"?gaze*.12:0
    function asset(name){var style=modelSpec.renderer==="atlas"?"voxel":modelSpec.pixel?"pixel":"vector";return Qt.resolvedUrl("assets/duck/"+(style==="vector"?"":style+"/")+name+".svg");}
    onArtStyleChanged:poseUpdates++
    onHatChanged:poseUpdates++
    onOutfitChanged:poseUpdates++
    onClockChanged:if(animate&&!reducedMotion&&mode!=="idle"&&!asleep)poseUpdates++
    onModeChanged:poseUpdates++
    onPlumageChanged:poseUpdates++
    onDirectionChanged:poseUpdates++
    onViewChanged:poseUpdates++
    onGazeChanged:if(!reducedMotion&&!asleep)poseUpdates++
    onBlinkChanged:if(mode==="idle"&&!reducedMotion)poseUpdates++
    onReducedMotionChanged:poseUpdates++

    readonly property var activeRenderer:rendererLoader.item
    function hitRegion(x,y){return activeRenderer?activeRenderer.hitRegion(x,y):"";}

    function inputPolygons(target){return activeRenderer?activeRenderer.inputPolygons(target):[];}

    Loader {
        id:rendererLoader
        anchors.fill:parent
        sourceComponent:duck.modelSpec.renderer==="atlas"?studioComponent:flatComponent
    }
    Component {
        id:studioComponent
        DuckBlenderSprite{width:duck.width;height:duck.height;bird:duck;}
    }
    Component {
        id:flatComponent
        DuckFlatSprite{width:duck.width;height:duck.height;bird:duck;}
    }
}
