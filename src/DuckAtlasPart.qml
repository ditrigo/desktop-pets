pragma ComponentBehavior: Bound
import QtQuick
import "DuckAtlas.js" as Atlas

// A cropped cell from a cached PNG atlas. Changing pose moves texture geometry;
// it does not decode another image or start an animation timer.
Item {
    id: part
    required property string partName
    property var atlasData:Atlas.data
    property var overrideSpec:null
    property string assetRoot:"assets/duck3d"
    property int viewIndex: 0
    property int pose: 0
    readonly property var spec:overrideSpec||atlasData.parts[partName]||null
    readonly property int frame: spec ? viewIndex * spec.poses + Math.max(0, Math.min(spec.poses-1, pose)) : 0
    x: spec ? spec.x : 0
    y: spec ? spec.y : 0
    width: spec ? spec.width : 0
    height: spec ? spec.height : 0
    clip: true
    Image {
        x:part.spec?-(part.frame%part.spec.columns)*part.spec.width:0
        y:part.spec?-Math.floor(part.frame/part.spec.columns)*part.spec.height:0
        width:part.spec?part.spec.width*part.spec.columns:0
        height:part.spec?part.spec.height*part.spec.rows:0
        source:part.spec?Qt.resolvedUrl(part.assetRoot+"/"+part.spec.file):""
        smooth:true
    }
}
