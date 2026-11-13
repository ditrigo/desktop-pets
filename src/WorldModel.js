// Keep titles and unrelated client metadata out of the scene and its cache key.
function clients(raw) {
    return raw.filter(function(c){return c&&c.address&&c.at&&c.size;}).map(function(c){
        return {address:c.address,monitor:c.monitor,mapped:!!c.mapped,hidden:!!c.hidden,visible:c.visible!==false,
            workspace:{id:c.workspace?c.workspace.id:0},at:c.at.slice(0,2),size:c.size.slice(0,2),
            floating:!!c.floating,pinned:!!c.pinned,fullscreen:c.fullscreen||0,
            focusHistoryID:c.focusHistoryID,initialClass:c.initialClass||c.class||""};
    }).sort(function(a,b){return a.address<b.address?-1:a.address>b.address?1:0;});
}
function monitors(raw) {
    return raw.map(function(m){return {id:m.id,name:m.name,x:m.x,y:m.y,width:m.width,height:m.height,
        scale:m.scale,transform:m.transform,reserved:m.reserved||[0,0,0,0],
        activeWorkspace:{id:m.activeWorkspace?m.activeWorkspace.id:0},specialWorkspace:{id:m.specialWorkspace?m.specialWorkspace.id:0},
        dpmsStatus:m.dpmsStatus!==false,disabled:!!m.disabled};}).sort(function(a,b){return a.id-b.id;});
}
function availableMonitor(list,config,focused) {
    var available=list.filter(function(m){return !m.disabled;});
    if(config.monitorMode==="fixed"&&available.some(function(m){return m.name===config.monitor;}))return config.monitor;
    return available.some(function(m){return m.name===focused;})?focused:available.length?available[0].name:"";
}
