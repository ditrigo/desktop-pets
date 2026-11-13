import QtQuick
import QtTest
import "../src" as Duck
import "../src/DuckGeometry.js" as Geometry

Rectangle {
    width:240;height:224;color:"#202a36"
    Duck.DuckSprite{id:bird;width:240;height:224;artStyle:"vector";}
    TestCase {
        name:"FlatWardrobe"
        when:windowShown
        function snapshot(){wait(16);return grabImage(bird);}
        function sameImage(a,b){
            if(a.equals(b))return true;
            // Software rendering can round antialiased wing edges differently
            // after another image invalidates the surrounding scene graph.
            for(var y=0;y<bird.height;y++)for(var x=0;x<bird.width;x++)
                if(Math.abs(a.red(x,y)-b.red(x,y))>4||Math.abs(a.green(x,y)-b.green(x,y))>4||Math.abs(a.blue(x,y)-b.blue(x,y))>4)return false;
            return true;
        }
        function init(){bird.artStyle="vector";bird.view="threeQuarter";bird.mode="idle";bird.clock=.17;bird.modeTime=.4;bird.stride=.8;bird.direction=1;bird.hat="none";bird.outfit="none";bird.plumage="yellow";bird.animate=true;bird.reducedMotion=false;wait(20);}
        function test_neck_and_hat_attachment_data(){
            var rows=[];for(var style of ["vector","pixel"])for(var view of ["side","threeQuarter","front"])for(var hat of Geometry.data.flat.hats)rows.push({tag:style+"-"+view+"-"+hat,style:style,view:view,hat:hat});return rows;
        }
        function test_neck_and_hat_attachment(data){
            bird.artStyle=data.style;bird.view=data.view;bird.hat=data.hat;bird.outfit="scarf";wait(20);
            var head=findChild(bird,"flat-head"),hat=findChild(bird,"flat-hat"),neck=findChild(bird,"flat-neckwear");
            verify(head&&hat&&neck,"all attachment nodes loaded");
            for(var mode of ["idle","walk","fly","sleep","eat","preen","drag"]){
                bird.mode=mode;bird.direction=mode==="walk"?-1:1;snapshot();
                var band=hat.mapToItem(bird,32,28),crown=head.mapToItem(bird,2,data.style==="pixel"?-36:-38);
                verify(Math.hypot(band.x-crown.x,band.y-crown.y)<.01,"hat follows fitted crown during "+mode);
                var hatPoint=hat.mapToItem(bird,32,20);
                compare(bird.hitRegion(hatPoint.x,hatPoint.y),"head","hat input follows its artwork during "+mode);
                var cx=data.view==="front"?30:34;
                var collar=neck.mapToItem(bird,cx,50),anchor=head.mapToItem(bird,cx-30,2);
                verify(Math.hypot(collar.x-anchor.x,collar.y-anchor.y)<.01,"collar follows neck during "+mode);
            }
        }
        function test_wardrobe_changes_the_render_data(){var rows=[];for(var style of ["vector","pixel"])for(var view of Geometry.data.views)for(var palette of ["yellow","mallard","white"])rows.push({tag:style+view+palette,style:style,view:view,palette:palette});return rows;}
        function test_wardrobe_changes_the_render(data){
            bird.artStyle=data.style;bird.view=data.view;bird.plumage=data.palette;var base=snapshot();
            for(var name of Geometry.data.flat.hats){bird.hat=name;verify(!base.equals(snapshot()),name);}
            bird.hat="none";verify(sameImage(base,snapshot()));
            for(var outfit of Geometry.data.flat.outfits){bird.outfit=outfit;verify(!base.equals(snapshot()),outfit);}
            bird.outfit="none";verify(sameImage(base,snapshot()));
        }
        function test_shirt_sleeves_follow_wings_data(){var rows=[];for(var style of ["vector","pixel"])for(var outfit of Geometry.data.flat.uniforms)rows.push({tag:style+outfit,style:style,outfit:outfit});return rows;}
        function test_shirt_sleeves_follow_wings(data){
            bird.artStyle=data.style;bird.mode="wave";bird.outfit=data.outfit;bird.clock=0;var a=snapshot();bird.clock=.13;verify(!a.equals(snapshot()));
            var wing=findChild(bird,"flat-near-wing"),sleeve=findChild(bird,"flat-sleeve-near");verify(wing&&sleeve);
            var seam=sleeve.mapToItem(bird,wing.frontal?20:8,6),joint=wing.mapToItem(bird,0,0);
            verify(Math.hypot(seam.x-joint.x,seam.y-joint.y)<.01,"sleeve stays on wing joint");
            bird.animate=false;var paused=snapshot();bird.clock=20;verify(paused.equals(snapshot()),"paused clothes stay still");
        }
        function test_cloth_and_stop_share_phase_data(){return [{tag:"classic",style:"vector"},{tag:"pixel",style:"pixel"}];}
        function test_cloth_and_stop_share_phase(data){
            bird.artStyle=data.style;bird.outfit="scarf";bird.mode="walk";bird.stride=.2;wait(30);
            var neck=findChild(bird,"flat-neckwear");verify(neck);
            var first=neck.transform[0].angle;bird.stride=2;wait(10);verify(first!==neck.transform[0].angle,"cloth follows stride");
            bird.mode="settle";bird.modeTime=0;compare(bird.stepMix,1);bird.modeTime=.18;compare(bird.stepMix,0);
            bird.mode="idle";wait(10);compare(bird.clothAngle,0);var still=snapshot();bird.clock=200;verify(still.equals(snapshot()),"idle cloth stays still");
        }
        function test_no_extra_idle_updates_data(){return [{tag:"classic",style:"vector"},{tag:"pixel",style:"pixel"}];}
        function test_no_extra_idle_updates(data){
            bird.artStyle=data.style;bird.hat="wizard";bird.outfit="scarf";var a=snapshot(),count=bird.poseUpdates;bird.clock=30;wait(35);verify(a.equals(snapshot()));compare(bird.poseUpdates,count);
        }
    }
}
