import QtQuick
import QtTest
import "../src" as Pet

Rectangle {
    width:240;height:224;color:"#1d2731"
    Pet.PetSprite{id:bird;width:240;height:224;artStyle:"voxel";}
    TestCase {
        name:"BlenderSprite"
        when:windowShown
        function snapshot(){wait(20);return grabImage(bird);}
        function visibleBody(image){return image.red(120,140)!==image.red(0,0)||image.green(120,140)!==image.green(0,0)||image.blue(120,140)!==image.blue(0,0);}
        function init(){bird.artStyle="voxel";bird.plumage="yellow";bird.mode="idle";bird.animate=true;bird.reducedMotion=false;bird.clock=0;bird.stride=0;bird.modeTime=0;bird.hat="none";bird.outfit="none";bird.view="side";bird.direction=1;bird.blink=false;wait(30);}
        function test_static_and_suspended_images_do_not_advance(){
            var a=snapshot(),updates=bird.poseUpdates;bird.clock=5;wait(30);
            verify(a.equals(snapshot()));compare(bird.poseUpdates,updates);
            bird.mode="fly";bird.animate=false;a=snapshot();bird.clock=8;wait(30);verify(a.equals(snapshot()));
            bird.animate=true;bird.reducedMotion=true;a=snapshot();bird.clock=10;wait(30);verify(a.equals(snapshot()));
        }
        function test_baked_wing_and_foot_poses_change_the_render(){
            bird.mode="walk";bird.clock=.01;var a=snapshot();bird.stride=Math.PI/2;bird.clock=.12;verify(!a.equals(snapshot()));
            bird.mode="fly";bird.clock=0;a=snapshot();bird.clock=Math.PI/48;verify(!a.equals(snapshot()));
        }
        function test_every_hat_and_outfit_renders_and_can_be_removed(){
            bird.view="threeQuarter";var base=snapshot();
            for(var hat of ["wizard","pirate","santa","explorer","chef","crown"]){bird.hat=hat;verify(!base.equals(snapshot()),hat);}
            bird.hat="none";verify(base.equals(snapshot()));
            for(var outfit of ["scarf","sailor","space","cape"]){bird.outfit=outfit;verify(!base.equals(snapshot()),outfit);}
            bird.outfit="none";verify(base.equals(snapshot()));
        }
        function test_all_views_and_palettes_have_visible_bodies(){
            for(var palette of ["yellow","mallard","white"]){
                bird.plumage=palette;var previous=null;
                for(var view of ["side","threeQuarter","front"]){
                    bird.view=view;var image=snapshot();
                    verify(visibleBody(image),"body: "+palette+" "+view);
                    if(previous)verify(!previous.equals(image),"view changes texture");previous=image;
                }
            }
        }
        function test_blink_and_direction_change_the_image(){
            bird.view="threeQuarter";var a=snapshot();bird.blink=true;verify(!a.equals(snapshot()));
            bird.blink=false;verify(a.equals(snapshot()));bird.direction=-1;verify(!a.equals(snapshot()));
        }
        function test_switching_renderers_keeps_the_sprite_visible(){
            var previous=null;
            for(var style of ["vector","pixel","voxel","vector"]){bird.artStyle=style;wait(30);var image=snapshot();verify(visibleBody(image));if(previous)verify(!previous.equals(image));previous=image;}
        }
        function test_flat_only_wardrobe_is_retained_across_voxel_preview(){
            bird.artStyle="pixel";bird.hat="beret";bird.outfit="apron";wait(30);var dressed=snapshot();
            bird.artStyle="voxel";wait(30);verify(visibleBody(snapshot()));
            verify(bird.inputPolygons(bird).length>0,"unsupported accessories do not break voxel input");
            compare(bird.hat,"beret");compare(bird.outfit,"apron");
            bird.artStyle="pixel";wait(30);verify(dressed.equals(snapshot()),"returning restores the same clothes");
        }
    }
}
