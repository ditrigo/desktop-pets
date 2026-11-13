import QtQuick
import Quickshell
import "PetHit.js" as Hit
Region {
    id:mask
    required property var birdSprite
    required property var target
    property var pool:[]
    property int used:0
    property string signature:""
    function update() {
        let bands=Hit.bands(birdSprite.inputPolygons(target),2),sig=JSON.stringify(bands);
        if(sig===signature)return;signature=sig;
        while(pool.length<bands.length){let r=part.createObject(mask);pool.push(r);regions.push(r);}
        for(let i=0;i<Math.max(used,bands.length);i++){
            let b=bands[i],r=pool[i];r.x=b?b.x:0;r.y=b?b.y:0;r.width=b?b.width:0;r.height=b?b.height:0;
        }
        used=bands.length;
    }
    property Component part: Component{Region{}}
}
