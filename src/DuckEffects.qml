pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: fx
    required property var bird
    Image {smooth:!fx.bird.modelSpec.pixel&&fx.bird.modelSpec.renderer==="flat";visible:fx.bird.mode==="love"||fx.bird.mode==="giggle";x:28+Math.sin(fx.bird.t*3)*3-14*.55;y:26-(fx.bird.t%1.8)*9-20*.55;width:38*.55;height:29*.55;source:fx.bird.asset("heart");sourceSize:Qt.size(76,58);}
    Image {smooth:!fx.bird.modelSpec.pixel&&fx.bird.modelSpec.renderer==="flat";visible:fx.bird.mode==="love"||fx.bird.mode==="giggle";x:95-14*.4;y:18-((fx.bird.t+.9)%1.8)*7-20*.4;width:38*.4;height:29*.4;source:fx.bird.asset("heart");sourceSize:Qt.size(76,58);}
    Text {visible:fx.bird.asleep;x:83;y:23-baselineOffset;text:"z";color:"#a8bad5";font.family:"sans-serif";font.pixelSize:14;font.bold:true;}
    Text {visible:fx.bird.asleep;x:99;y:12-baselineOffset;text:"z";color:"#a8bad5";font.family:"sans-serif";font.pixelSize:11;font.bold:true;}
    Repeater {
        model:5
        delegate:Image {smooth:!fx.bird.modelSpec.pixel&&fx.bird.modelSpec.renderer==="flat";required property int index;visible:fx.bird.mode==="eat";x:82+index*5;y:102+Math.sin(index*4)*2;width:3;height:2;source:fx.bird.asset("crumb");sourceSize:Qt.size(6,4);}
    }
    Text {visible:fx.bird.mode==="dance";x:9;y:34+Math.sin(fx.bird.t*4)*5-baselineOffset;text:"♪";color:"#96cbb8";font.family:"sans-serif";font.pixelSize:18;font.bold:true;}
    Text {visible:fx.bird.mode==="dance";x:96;y:25-Math.sin(fx.bird.t*4)*5-baselineOffset;text:"♫";color:"#96cbb8";font.family:"sans-serif";font.pixelSize:18;font.bold:true;}
    Image {smooth:!fx.bird.modelSpec.pixel&&fx.bird.modelSpec.renderer==="flat";visible:fx.bird.mode==="quack";x:109;y:32;width:12;height:15;source:fx.bird.asset("quack");sourceSize:Qt.size(24,30);}
    Text {visible:fx.bird.mode==="surprise"||fx.bird.mode==="notice";x:98;y:20-baselineOffset;text:fx.bird.mode==="notice"?"?":"!";color:"#f5c87b";font.family:"sans-serif";font.pixelSize:21;font.bold:true;}
}
