var commands=["pet","head","wing","belly","startle","look","feed","treat","ball","dance","sleep","rest","wake","quack","hop","come","perch","pause","reset","remember","home","work","clear"];
function maintenance(name){return name==="clear"||name==="remember";}
function blocked(name,state) {
    if(commands.indexOf(name)<0)return "unknown action";
    if(name==="pause"||name==="work"||name==="clear")return "";
    if(!state.ready)return "not ready";
    if(name==="remember")return state.hasScene?"":"no screen";
    if(!state.enabled)return "disabled";
    if(state.locked)return "locked";
    if(!state.visible)return "hidden";
    if(state.dragging)return "dragging";
    if(state.paused&&["wake","rest","sleep","reset"].indexOf(name)<0)return "paused";
    return "";
}
