import QtQuick
import Quickshell
import Quickshell.Io
import "PetModel.js" as Model

Scope {
    id: store
    PetTranslations { id: strings }
    property string directory: ""
    property var profile: Model.memory({})
    property bool loaded: false
    property bool directoryReady: false
    readonly property bool ready: loaded&&directoryReady
    property bool recovering: false
    property bool dirty: false
    property bool writing: false
    property bool flushing: false
    property bool urgent: false
    property int revision: 0
    property int writingRevision: 0
    property string writingText: ""
    property string persistedText: ""
    property string backedUpText: ""
    property string errorKey: ""
    readonly property string error:errorKey?strings.t(errorKey):""
    property int writes: 0
    property int failures: 0

    function decode(text) {
        var raw=JSON.parse(text);
        if(!raw||typeof raw!=="object"||Array.isArray(raw)||Number(raw.version)>3)throw new Error("unsupported memory");
        return Model.memory(raw);
    }
    function update(patch,important) {
        var next=Model.memory(Object.assign({},profile,patch));
        if(JSON.stringify(next)===JSON.stringify(profile))return;
        profile=next;revision++;dirty=true;
        if(important){urgent=true;if(!soon.running)soon.start();}
    }
    function save() {
        if(!ready||!dirty||writing)return;
        writing=true;urgent=false;writingRevision=revision;writingText=JSON.stringify(profile,null,2)+"\n";
        if(writingText===persistedText){writing=false;dirty=false;return;}
        // FileView emits no saved signal for an unchanged setText. Recovery
        // can leave the backup already equal to the last primary checkpoint.
        if(persistedText&&backedUpText!==persistedText)backup.setText(persistedText);
        else primary.setText(writingText);
    }
    function failed(message) {
        writing=false;dirty=true;errorKey=message;failures++;
        retry.interval=failures<=3?5000:60000;retry.restart();
    }
    function flush() {
        if(!ready||!dirty)return;
        flushing=true;
        // Finish in-flight I/O before issuing the last synchronous checkpoint.
        backup.waitForJob();primary.waitForJob();
        if(!dirty){flushing=false;return;}
        var finalText=JSON.stringify(profile,null,2)+"\n";
        if(finalText===persistedText){dirty=false;writing=false;flushing=false;return;}
        writing=false;
        if(persistedText&&backedUpText!==persistedText){backup.setText(persistedText);if(!backup.waitForJob()){flushing=false;return;}}
        writing=true;writingRevision=revision;writingText=finalText;
        primary.setText(writingText);primary.waitForJob();
        flushing=false;
    }
    onReadyChanged: if(ready&&dirty)save()
    Component.onCompleted: mkdir.running=true
    Component.onDestruction: flush()
    Process {
        id:mkdir;command:["mkdir","-p",store.directory]
        onExited:function(code){store.directoryReady=code===0;if(code!==0)store.errorKey="error.memory-directory";}
    }
    FileView {
        id:primary
        path:store.directory+"/memory.json";atomicWrites:true;printErrors:false
        onLoaded: {
            if(store.loaded)return;
            try{store.profile=store.decode(text());store.persistedText=JSON.stringify(store.profile,null,2)+"\n";store.loaded=true;}
            catch(e){store.errorKey="error.memory-recover";store.recovering=true;}
        }
        onLoadFailed:store.recovering=true
        onSaved: {
            if(!store.writing)return;
            store.persistedText=store.writingText;store.writing=false;store.writes++;store.failures=0;store.errorKey="";
            store.dirty=store.revision!==store.writingRevision;
            if(store.dirty&&store.urgent&&!soon.running)soon.start();
        }
        onSaveFailed:store.failed("error.memory-save")
    }
    FileView {
        id:backup
        path:store.directory+"/memory.previous.json";atomicWrites:true;printErrors:false
        preload:store.recovering
        onLoaded: {
            store.backedUpText=text();
            if(!store.recovering||store.loaded)return;
            try{store.profile=store.decode(text());store.persistedText=JSON.stringify(store.profile,null,2)+"\n";store.dirty=true;store.revision++;}
            catch(e){store.profile=Model.memory({});}
            store.loaded=true;
        }
        onLoadFailed:if(store.recovering)store.loaded=true
        onSaved: {store.backedUpText=store.persistedText;if(store.writing&&!store.flushing)primary.setText(store.writingText);}
        onSaveFailed:store.failed("error.memory-backup")
    }
    Timer {id:soon;interval:1200;onTriggered:store.save();}
    Timer {
        id:retry
        onTriggered: {
            // A failed FileView write may retain the attempted text in its
            // cache. Reload before retrying the same payload.
            primary.reload();primary.waitForJob();backup.reload();backup.waitForJob();store.save();
        }
    }
    Timer {interval:60000;running:store.ready;repeat:true;onTriggered:store.save();}
}
