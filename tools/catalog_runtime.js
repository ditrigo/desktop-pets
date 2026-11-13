// Kept outside generated data so the compiler and runtime share one format.
function model(key) {
    for(var item of data.models)if(item.key===key)return item;
    return data.models[0];
}
function entry(kind,key) {
    for(var item of data[kind+"s"])if(item.key===key)return item;
    return null;
}
function variant(kind,key,modelKey) {
    var item=entry(kind,key),m=model(modelKey);
    if(!item)return null;
    var visited=[];
    while(visited.indexOf(m.key)<0){
        visited.push(m.key);
        if(item.variants[m.key])return item.variants[m.key];
        if(!m.wardrobeBase)return null;
        m=model(m.wardrobeBase);
    }
    return null;
}
function layer(key,modelKey) {
    var item=entry("outfit",key);
    return item&&variant("outfit",key,modelKey)?item.layer:"none";
}
function defaultPlacement(role,g,view) {
    if(role==="hat")return g.hatOffset.concat(g.hat);
    if(role==="neck")return g.neckwearOffset.concat(g.neckwear);
    if(role==="head"||role==="eyes")return g.headOffset.concat(g.head);
    if(role==="wing"||role==="sleeve")return view==="front"?g.wingPartFront:g.wingPartSide;
    if(role==="foot")return [0,0].concat(g.footSize);
    return [0,0].concat(g.canvas);
}
function part(modelKey,name,hat,outfit,view) {
    var m=model(modelKey),g=m.geometry,source=m,v=null,stem=name,role="body";
    if(name.indexOf("hat-"+hat+"-")===0){role="hat";v=variant("hat",hat,modelKey);if(v)stem=name.replace("hat-"+hat+"-","hat-"+v.prefix+"-");}
    else if(name.indexOf("neck-"+outfit+"-")===0){role="neck";v=variant("outfit",outfit,modelKey);if(v)stem=name.replace("neck-"+outfit+"-","neck-"+v.prefix+"-");}
    else if(name.indexOf("outfit-"+outfit+"-")===0){role="body";v=variant("outfit",outfit,modelKey);if(v)stem=name.replace("outfit-"+outfit+"-","outfit-"+v.prefix+"-");}
    else if(name.indexOf("sleeve-"+outfit+"-")===0){role="sleeve";v=variant("outfit",outfit,modelKey);if(v)stem=name.replace("sleeve-"+outfit+"-","sleeve-"+v.prefix+"-");}
    else if(name.indexOf("-head-")>=0)role="head";
    else if(name.indexOf("eyes-")===0)role="eyes";
    else if(name.indexOf("-wing-")>=0)role="wing";
    else if(name==="foot")role="foot";
    if(v)source=model(v.model);
    var projection=role==="wing"||role==="sleeve"?(name.slice(-6)==="-front"?"front":"side"):view;
    var placement=v&&v.placement&&v.placement[role]&&v.placement[role][projection]||defaultPlacement(role,g,projection);
    var sizes=v&&v.sizes||source.sizes||{};
    var size=sizes[stem]||defaultPlacement(role,source.geometry,projection).slice(2);
    var hulls=v&&v.hulls||source.hulls||{};
    return {path:(v?v.root:m.root)+"/"+stem+"."+(v?v.format:m.format),placement:placement,size:size,hull:hulls[stem]||[]};
}
function atlasPart(kind,key,modelKey) {
    var v=variant(kind,key,modelKey);
    if(!v||v.format!=="atlas")return null;
    var source=model(v.model),spec=v.spec||source.atlas.parts[v.part];
    return spec?{root:v.root,spec:spec}:null;
}
