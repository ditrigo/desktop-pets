import QtQuick
import Quickshell
import Quickshell.Io
import "DuckModel.js" as Model

// The shell owns writing. This observer confirms persistence by fresh disk reads.
Scope {
    id:store
    DuckTranslations { id: strings }
    property var shell:null
    property string path:""
    property string pluginId:"ditrigo.desktop-duck"
    property var disk:({})
    property var pending:({})
    readonly property var settings:Object.assign({},disk,pending)
    property string state:"idle"
    property string errorKey:""
    readonly property string error:errorKey?strings.t(errorKey):""
    property int revision:0
    property int attempts:0
    property double deadline:0
    property int timeoutMs:4000
    readonly property bool applying:state==="applying"
    function entry(text){
        let doc=JSON.parse(text),layout=doc.bar?doc.bar.layout||{}:{};
        for(let section of ["left","center","right"])for(let e of layout[section]||[])if(e.id===pluginId)return e;
        for(let e of doc.plugins||[])if(e.id===pluginId)return e;
        return {};
    }
    function matches(){let clean=Model.settings(disk);return Object.keys(pending).every(function(k){return JSON.stringify(clean[k])===JSON.stringify(store.pending[k]);});}
    function read(text){
        try{disk=entry(text);}catch(e){if(applying)errorKey="error.settings-read";return;}
        if(applying&&matches()){pending={};state="saved";errorKey="";poll.stop();}
    }
    function apply(patch){
        if(!shell){errorKey="error.settings-unavailable";return false;}
        let wanted=Object.assign({},pending,patch),clean=Model.settings(Object.assign({},disk,wanted));
        for(let k of Object.keys(wanted)){if(!Object.prototype.hasOwnProperty.call(Model.defaults,k))return false;wanted[k]=clean[k];}
        if(!applying&&Object.keys(wanted).every(function(k){return JSON.stringify(clean[k])===JSON.stringify(Model.settings(store.disk)[k]);})){errorKey="";return true;}
        if(applying&&JSON.stringify(wanted)===JSON.stringify(pending))return true;
        let next=Object.assign({},disk,wanted);
        if(shell.updateEntryInline(pluginId,next)===false){errorKey="error.settings-apply";return false;}
        pending=wanted;revision++;attempts=1;deadline=Date.now()+timeoutMs;state="applying";errorKey="";poll.restart();return true;
    }
    function retry(){
        if(!Object.keys(pending).length)return false;
        state="applying";attempts=0;deadline=Date.now()+timeoutMs;errorKey="";poll.restart();file.reload();return true;
    }
    FileView{id:file;path:store.path;watchChanges:true;printErrors:false;onLoaded:store.read(text());onFileChanged:reload();onLoadFailed:if(store.applying)store.errorKey="error.settings-read";}
    Timer {
        id:poll;interval:150;repeat:true
        onTriggered:{
            if(!store.applying){stop();return;}
            if(Date.now()>=store.deadline){store.state="failed";store.errorKey="error.settings-confirm";stop();return;}
            // Rebase retries on a recently read entry; the host merges into its live config.
            if(store.attempts<3&&Date.now()>store.deadline-store.timeoutMs+store.attempts*900){
                store.shell.updateEntryInline(store.pluginId,Object.assign({},store.disk,store.pending));store.attempts++;
            }
            file.reload();
        }
    }
}
