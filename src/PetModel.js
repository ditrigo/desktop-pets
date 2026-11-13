// Pure simulation shared by QML and Node. Positions are logical screen pixels.
// pet-art:keys:start
var wardrobeKeys = {"artStyle":["vector","pixel","voxel"],"hat":["none","wizard","pirate","santa","explorer","chef","crown","rainhat","detective","beret","straw","tophat","nightcap"],"outfit":["none","scarf","sailor","space","cape","raincoat","trench","apron","overalls","tuxedo","pajamas"]};
// pet-art:keys:end
var defaults = {enabled:true, name:"Ducky", size:76, speed:80, personality:"curious", palette:"yellow",
    walkOnWindows:true, followCursor:false, sound:false, bubbles:true, hideFullscreen:true,
    reducedMotion:false, workMode:false, cursorReactions:true, monitorMode:"follow", monitor:"",
    artStyle:"vector", hat:"none", outfit:"none", powerProfile:"normal",quietHours:false,quietStart:"22:00",quietEnd:"08:00",quietMode:"work"};
// Personality affects choices, rather than creating a second state machine.
var personalities = {
    calm:{speed:.72,idle:14,initiative:60,flight:90,play:.25,curiosity:.08},
    curious:{speed:1,idle:9,initiative:40,flight:60,play:.45,curiosity:.65},
    playful:{speed:1.18,idle:7,initiative:30,flight:60,play:.8,curiosity:.25}
};
function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }
function finite(n, fallback) { return isFinite(Number(n)) ? Number(n) : fallback; }
function settings(raw) {
    var out = {}; raw = raw || {};
    for (var k in defaults) out[k] = raw[k] === undefined ? defaults[k] : raw[k];
    out.size = clamp(finite(out.size,76),48,144); out.speed = clamp(finite(out.speed,80),25,180);
    out.name = typeof out.name === "string" ? out.name.trim().slice(0,32) || "Ducky" : "Ducky";
    if (["curious","calm","playful"].indexOf(out.personality)<0) out.personality="curious";
    if (["yellow","mallard","white"].indexOf(out.palette)<0) out.palette="yellow";
    if (wardrobeKeys.artStyle.indexOf(out.artStyle)<0) out.artStyle="vector";
    if (wardrobeKeys.hat.indexOf(out.hat)<0) out.hat="none";
    if (wardrobeKeys.outfit.indexOf(out.outfit)<0) out.outfit="none";
    if (["follow","fixed"].indexOf(out.monitorMode)<0) out.monitorMode="follow";
    if(["normal","economy","auto"].indexOf(out.powerProfile)<0)out.powerProfile="normal";
    for(var timeKey of ["quietStart","quietEnd"])if(!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(out[timeKey]))out[timeKey]=defaults[timeKey];
    if(["work","reduced"].indexOf(out.quietMode)<0)out.quietMode="work";
    out.monitor=typeof out.monitor==="string"?out.monitor.slice(0,128):"";
    for (var key in defaults) if (typeof defaults[key]==="boolean") out[key]=typeof out[key]==="boolean"?out[key]:defaults[key];
    return out;
}
function parseValues(text, expected) {
    var values=[],start=-1,depth=0,quoted=false,escaped=false;
    for(var i=0;i<text.length;i++) {
        var ch=text[i];
        if(quoted) { if(escaped) escaped=false; else if(ch==="\\") escaped=true; else if(ch==='"') quoted=false; }
        else if(ch==='"') quoted=true;
        else if(ch==="{"||ch==="[") { if(depth++===0) start=i; }
        else if(ch==="}"||ch==="]") { if(--depth===0&&start>=0) { values.push(JSON.parse(text.slice(start,i+1))); start=-1; } }
    }
    if(depth!==0||quoted||values.length!==expected) throw new Error("incomplete JSON response");
    return values;
}
function parseBatch(text) {
    var values=parseValues(text,3);
    if(!Array.isArray(values[0])||!Array.isArray(values[1])||!isFinite(values[2].x)||!isFinite(values[2].y)) throw new Error("invalid compositor snapshot");
    return values;
}
function memory(raw) {
    raw=raw||{};
    var out={version:3,trust:clamp(finite(raw.trust,20),0,100),energy:clamp(finite(raw.energy,85),0,100),
        satiety:clamp(finite(raw.satiety,65),0,100),fed:Math.floor(Math.max(0,finite(raw.fed,0))),
        restUntil:Math.max(0,finite(raw.restUntil,0)),looksVersion:1,looks:[],favorites:{},positions:{}};
    var ids={};
    for(var look of Array.isArray(raw.looks)?raw.looks.slice(0,12):[]){
        if(!look||typeof look.id!=="string"||!look.id||ids[look.id]||Number(look.version||1)>1)continue;
        ids[look.id]=true;var clean=settings(look),kind=look.kind==="wardrobe"?"wardrobe":"full";
        var saved={version:1,id:look.id.slice(0,64),name:typeof look.name==="string"?look.name.trim().slice(0,32)||"My look":"My look",kind:kind,hat:clean.hat,outfit:clean.outfit};
        if(kind==="full"){saved.artStyle=clean.artStyle;saved.palette=clean.palette;}
        out.looks.push(saved);
    }
    ["favorites","positions"].forEach(function(key) {
        var entries=raw[key];
        if(!entries||typeof entries!=="object"||Array.isArray(entries)) return;
        Object.keys(entries).slice(0,16).forEach(function(name) {
            var p=entries[name]; if(!p||!isFinite(p.x)) return;
            out[key][name]={x:clamp(Number(p.x),0,1),edge:p.edge==="window"?"window":"floor"};
            if(out[key][name].edge==="window"&&typeof p.app==="string"&&p.app) {
                out[key][name].app=p.app.slice(0,256);
                out[key][name].side=p.side==="top"?"top":"bottom";
                out[key][name].localX=clamp(finite(p.localX,.5),0,1);
            }
        });
    });
    return out;
}
function subtract(segments, lo, hi) {
    var out=[];
    segments.forEach(function(s) { if(hi<=s[0]||lo>=s[1]) out.push(s); else { if(lo>s[0]) out.push([s[0],lo]); if(hi<s[1]) out.push([hi,s[1]]); } });
    return out;
}
function surfaces(monitor,clients,width,height,size,onWindows) {
    var r=monitor&&monitor.reserved||[0,0,0,0],floor=clamp(height-r[3]-6,Math.min(size,height),height);
    var out=[{id:"floor",base:"floor",left:r[0]+size/2,right:Math.max(r[0]+size/2,width-r[2]-size/2),y:floor,origin:0,edge:"floor"}];
    if(!monitor||!onWindows) return out;
    var workspace=monitor.specialWorkspace&&monitor.specialWorkspace.id||monitor.activeWorkspace&&monitor.activeWorkspace.id;
    // Floating windows are above tiled ones; focus history orders overlapping
    // windows inside each group (Hyprland's client snapshot exposes no z-index).
    var windows=clients.filter(function(c) { return c.mapped&&!c.hidden&&c.visible!==false&&c.monitor===monitor.id&&
        (c.pinned||c.workspace&&c.workspace.id===workspace)&&c.at&&c.size; }).slice().sort(function(a,b) {
        if(!!a.floating!==!!b.floating) return a.floating?-1:1;
        return finite(a.focusHistoryID,999)-finite(b.focusHistoryID,999);
    });
    windows.forEach(function(c,index) {
        if(c.fullscreen>0) return;
        var origin=c.at[0]-monitor.x,left=Math.max(out[0].left,origin+size*.35),right=Math.min(out[0].right,origin+c.size[0]-size*.35);
        if(right-left<size*.6) return;
        var top=c.at[1]-monitor.y;
        [{kind:"top",y:top},{kind:"bottom",y:top+c.size[1]}].forEach(function(edge) {
            if(edge.y<size+r[1]||edge.y>floor-3) return;
            var spans=[[left,right]];
            for(var j=0;j<index;j++) {
                var front=windows[j],fy=front.at[1]-monitor.y;
                if(fy<edge.y+1&&fy+front.size[1]>edge.y-size*.85) {
                    var fx=front.at[0]-monitor.x;
                    spans=subtract(spans,fx-size*.45,fx+front.size[0]+size*.45);
                }
            }
            var base=c.address+":"+edge.kind;
            spans.forEach(function(span,n) { if(span[1]-span[0]>=size*.6) out.push({id:base+(n?":"+n:""),base:base,
                left:span[0],right:span[1],y:edge.y,origin:origin,edge:edge.kind,window:c.address,
                app:c.initialClass||c.class||"",windowWidth:c.size[0]}); });
        });
    });
    return out;
}
function surfaceById(list,id) { for(var i=0;i<list.length;i++) if(list[i].id===id) return list[i]; return null; }
function supportFor(list,s) {
    if(!s.surfaceBase||s.surfaceBase==="floor") return surfaceById(list,s.surface);
    // Fragment numbers change as windows occlude an edge. Follow the local
    // attachment point, never a newly renumbered fragment on the other side.
    for(var i=0;i<list.length;i++) if(list[i].base===s.surfaceBase) {
        var x=s.offset===null?s.x:(list[i].origin||0)+s.offset;
        if(x>=list[i].left-.5&&x<=list[i].right+.5) return list[i];
    }
    return null;
}
function enter(s,mode,duration,next) { s.mode=mode; s.remaining=duration===undefined?1:duration; s.modeTime=0; s.next=next||""; }
function create(width,height,size,saved,profile) {
    profile=memory(profile); var x=saved&&isFinite(saved.x)?saved.x*width:width*.72;
    return {x:clamp(x,size/2,width-size/2),y:height-6,vx:0,vy:0,direction:-1,wantedDirection:-1,
        mode:"wave",remaining:1.5,modeTime:0,next:"",surface:"floor",surfaceBase:"floor",offset:null,
        goal:"",target:null,targetItem:"",flight:null,age:0,stride:0,view:"threeQuarter",gaze:0,
        energy:profile.energy,satiety:profile.satiety,trust:profile.trust,fed:profile.fed,
        event:"",eventSerial:0,manualUntil:0,lastCursor:null,cursorSequence:-1,approachCooldown:0,ballCooldown:0,
        initiativeAt:12,flightAt:0,playCount:0};
}
function emit(s,event) { s.event=event; s.eventSerial++; }
function attach(s,p) { s.surface=p.id; s.surfaceBase=p.base||p.id; s.offset=s.x-(p.origin||0); }
function detach(s) { s.surface=""; s.surfaceBase=""; s.offset=null; }
function flyTo(s,target,after) {
    s.target={x:target.x,y:target.y,surface:target.surface}; s.flight=null;
    s.afterFlight=after||""; enter(s,"anticipate",.24,"fly"); s.goal=s.goal||"travel";
}
function turn(s,direction) {
    if(s.direction===direction) return false;
    s.wantedDirection=direction; enter(s,"turn",.18,"walk"); return true;
}
function act(s,name) {
    if(["wake","sleep","feed","pet","head","wing","belly","startle","look","dance","quack","hop"].indexOf(name)<0)return false;
    s.goal=""; s.targetItem=""; s.target=null; s.flight=null; s.manualUntil=s.age+8;
    if(name==="wake") { enter(s,"stretch",.8,"wave"); emit(s,"wake"); }
    else if(name==="sleep") enter(s,"sleep",300);
    else if(name==="feed") { enter(s,"eat",1.3,"love"); s.satiety=clamp(s.satiety+12,0,100); s.fed++; emit(s,"fed"); }
    else if(name==="pet"||name==="head") { s.trust=clamp(s.trust+2,0,100); enter(s,"love",2.5); emit(s,"pet"); }
    else if(name==="wing") { enter(s,"wave",1.6); emit(s,"wing"); }
    else if(name==="belly") { enter(s,"giggle",1.5); emit(s,"belly"); }
    else if(name==="startle") { enter(s,"surprise",.65,"shake"); s.approachCooldown=5; emit(s,"surprise"); }
    else if(name==="look") { enter(s,"look",1.4); }
    else if(name==="dance") { enter(s,"dance",4); s.energy=Math.max(0,s.energy-2); }
    else if(name==="quack") enter(s,"quack",1.4);
    else if(name==="hop") { enter(s,"anticipate",.24,"hop"); }
    else return false;
    return true;
}
function item(type,x,y,vx,vy,id) {
    return {id:id,type:type,x:x,y:y,vx:vx||0,vy:vy||0,radius:type==="ball"?11:5,
        surface:"",surfaceBase:"",offset:null,origin:0,age:0,consumed:false,held:false,rotation:0};
}
function stepItems(items,dt,world) {
    dt=clamp(dt,0,5);
    items.forEach(function(o) {
        if(o.held||o.consumed) return;
        o.age+=dt;
        if(o.age>(o.type==="ball"?300:90)) { o.consumed=true; return; }
        var p=supportFor(world.surfaces,o);
        if(p) { o.x+=(p.origin||0)-o.origin;o.origin=p.origin||0;o.y=p.y-o.radius;o.surface=p.id;o.surfaceBase=p.base||p.id; }
        else o.surface="";
        var old=o.y+o.radius;
        if(!o.surface) o.vy+=700*dt;
        o.x+=o.vx*dt; o.y+=o.vy*dt; o.rotation+=o.vx*dt/22;
        var hit=null;
        if(!o.surface&&o.vy>=0) world.surfaces.forEach(function(edge) {
            if(old<=edge.y+1&&o.y+o.radius>=edge.y&&o.x>=edge.left&&o.x<=edge.right&&(!hit||edge.y<hit.y)) hit=edge;
        });
        if(hit||o.y+o.radius>=world.surfaces[0].y) {
            hit=hit||world.surfaces[0]; o.y=hit.y-o.radius;
            if(o.type==="ball"&&Math.abs(o.vy)>70) o.vy=-o.vy*.48;
            else { o.vy=0;o.surface=hit.id;o.surfaceBase=hit.base||hit.id;o.origin=hit.origin||0; }
        }
        if(o.surface) {
            o.vx*=Math.pow(o.type==="ball"?.4:.04,dt);
            if(Math.abs(o.vx)<.5)o.vx=0;
            p=surfaceById(world.surfaces,o.surface);
            if(p&&(o.x<p.left||o.x>p.right)) {o.surface="";o.vy=5;}
            if(p)o.offset=o.x-(p.origin||0);
        }
        if(o.x<o.radius||o.x>world.width-o.radius) {o.x=clamp(o.x,o.radius,world.width-o.radius);o.vx*=-.65;}
    });
    return items.filter(function(o){return !o.consumed;});
}
function targetItem(s,world) {
    var items=world.items||[];for(var i=0;i<items.length;i++)if(items[i].id===s.targetItem&&!items[i].consumed)return items[i];return null;
}
function notice(s,o) { s.goal=o.type==="pea"?"food":"ball";s.targetItem=o.id;s.target=null;enter(s,"notice",.5,"goal");emit(s,o.type==="pea"?"noticeFood":"noticeBall"); }
function homeTarget(world,cfg,preference) {
    var f=preference||world.favorite||{x:.85,edge:"floor"},p=world.surfaces[0],x=f.x*world.width;
    if(f.edge==="window"&&f.app&&cfg.walkOnWindows&&!cfg.workMode) {
        var candidates=world.surfaces.filter(function(edge){return edge.app===f.app&&edge.edge===f.side;});
        // A live handle is only used in this session, never persisted.
        candidates.sort(function(a,b){return Number(b.window===world.favoriteHandle)-Number(a.window===world.favoriteHandle)||Math.abs((a.origin||0)-x)-Math.abs((b.origin||0)-x);});
        for(var i=0;i<candidates.length;i++) {
            var local=(candidates[i].origin||0)+finite(f.localX,.5)*candidates[i].windowWidth;
            if(local>=candidates[i].left&&local<=candidates[i].right){p=candidates[i];x=local;break;}
        }
    }
    return {x:clamp(x,p.left,p.right),y:p.y,surface:p.id};
}
function position(s,world) {
    var p=supportFor(world.surfaces,s),saved={x:clamp(s.x/Math.max(1,world.width),0,1),edge:p&&p.window?"window":"floor"};
    if(p&&p.window&&p.app){saved.app=p.app;saved.side=p.edge;saved.localX=clamp((s.x-p.origin)/Math.max(1,p.windowWidth),0,1);}
    return saved;
}
function goHome(s,world,cfg) {
    var target=homeTarget(world,cfg);
    if(s.surface!==target.surface||Math.abs(s.x-target.x)>2) { s.goal="home";flyTo(s,target,"rest"); }
    else {enter(s,world.resting?"sleep":"idle",world.resting?3600:5);s.goal="";}
}
// User intent wins over scheduled calm, then autonomous initiatives.
function priority(s,world,cfg){return s.mode==="drag"?"drag":s.age<s.manualUntil?"manual":world.resting||cfg.workMode?"rest":"autonomous";}
function quietAt(cfg,minutes){
    if(!cfg.quietHours)return false;
    function minute(t){var p=t.split(":");return Number(p[0])*60+Number(p[1]);}
    var a=minute(cfg.quietStart),b=minute(cfg.quietEnd);
    return a===b?false:a<b?minutes>=a&&minutes<b:minutes>=a||minutes<b;
}
function choose(s,cfg,random,world) {
    s.view="side";
    if((world.resting||cfg.workMode)&&s.age>=s.manualUntil) {goHome(s,world,cfg);return;}
    if(cfg.reducedMotion) {enter(s,"idle",8);return;}
    if(s.age<s.manualUntil) {enter(s,"idle",Math.min(5,s.manualUntil-s.age));return;}
    if(s.energy<20) {enter(s,"sleep",18+random()*12);return;}
    var character=personalities[cfg.personality];
    var candidates=(world.items||[]).filter(function(o){return !o.consumed&&!o.held&&(o.type==="pea"?(s.satiety<90||s.age<s.manualUntil):s.ballCooldown<=0&&s.energy>25);});
    if(candidates.length) {
        candidates.sort(function(a,b){return Math.abs(a.x-s.x)+Math.abs(a.y-s.y)-Math.abs(b.x-s.x)-Math.abs(b.y-s.y);});
        notice(s,candidates[0]);return;
    }
    if(s.age<s.initiativeAt) {enter(s,"idle",Math.min(5,s.initiativeAt-s.age));return;}
    s.initiativeAt=s.age+character.initiative+random()*15;
    var roll=random(),calm=cfg.personality==="calm",playful=cfg.personality==="playful";
    if(roll<(calm?.4:.13)) {enter(s,"idle",character.idle+random()*5);s.view="front";}
    else if(roll<(calm?.6:.25)) enter(s,"preen",3+random()*3);
    else if(roll<(calm?.76:.30)) enter(s,"sleep",12+random()*14);
    else if(playful&&roll<.48) enter(s,"dance",3);
    else if(calm&&roll<.9&&world.favorite) goHome(s,world,cfg);
    else if(cfg.personality==="curious"&&roll<.56&&world.surfaces.length>1&&s.age>=s.flightAt) {
        var p=world.surfaces[1+Math.floor(random()*(world.surfaces.length-1))];s.goal="explore";
        s.flightAt=s.age+character.flight;
        flyTo(s,{x:(p.left+p.right)/2,y:p.y,surface:p.id});
    } else {enter(s,"walk",3+random()*5);if(random()<.35)turn(s,-s.direction);}
}
function aimForItem(s,world,cfg) {
    var o=targetItem(s,world);if(!o||o.held){s.goal="";s.targetItem="";enter(s,"idle",1);return;}
    if(!o.surface){enter(s,"look",.4,"goal");return;}
    var p=surfaceById(world.surfaces,o.surface);if(!p){enter(s,"look",.4,"goal");return;}
    if(s.surface!==p.id) {flyTo(s,{x:clamp(o.x-s.direction*cfg.size*.25,p.left,p.right),y:p.y,surface:p.id},"goal");return;}
    enter(s,"walk",8,"goal");
}
function after(s,world,cfg,random) {
    var next=s.next;s.next="";
    if(next==="hop") {detach(s);s.vy=-285;s.vx=s.direction*65;enter(s,"fall",10);return;}
    if(next==="fly") {
        var p=surfaceById(world.surfaces,s.target&&s.target.surface)||world.surfaces[0];
        var tx=clamp(s.target?s.target.x:s.x,p.left,p.right),ty=p.y,dist=Math.hypot(tx-s.x,ty-s.y);
        s.flight={fromX:s.x,fromY:s.y,time:0,duration:clamp(dist/Math.max(180,cfg.speed*2.8),.4,3),arc:clamp(dist*.18,28,130)};
        detach(s);enter(s,"fly",10);return;
    }
    if(next==="goal") {aimForItem(s,world,cfg);return;}
    if(next==="consume") {
        var food=targetItem(s,world);
        if(!food||food.type!=="pea"||food.held||food.surface!==s.surface||Math.abs(food.x-s.x)>cfg.size) {
            s.goal="";s.targetItem="";enter(s,"idle",1);return;
        }
        food.consumed=true;
        s.satiety=clamp(s.satiety+18,0,100);s.energy=clamp(s.energy+4,0,100);s.trust=clamp(s.trust+1,0,100);s.fed++;
        s.goal="";s.targetItem="";enter(s,"love",1.5);emit(s,"fed");return;
    }
    if(next==="rest") {s.goal="";enter(s,world.resting?"sleep":"idle",world.resting?3600:5);return;}
    if(next==="edge") {
        if(!cfg.workMode&&!world.resting&&s.age>=s.flightAt&&world.surfaces.length>1&&random()<personalities[cfg.personality].curiosity) {
            var options=world.surfaces.filter(function(p){return p.id!==s.surface&&Math.abs((p.left+p.right)/2-s.x)<700;});
            var dest=options[Math.floor(random()*options.length)];
            if(dest){s.flightAt=s.age+personalities[cfg.personality].flight;flyTo(s,{x:clamp(s.x,dest.left,dest.right),y:dest.y,surface:dest.id});return;}
        }
        s.wantedDirection=-s.direction;enter(s,"turn",.22,"walk");return;
    }
    if(next==="walk") {s.direction=s.wantedDirection;enter(s,"walk",2+random()*3);return;}
    if(next) {enter(s,next,next==="shake"?.7:1.2);return;}
    if(s.goal==="food"||s.goal==="ball"){aimForItem(s,world,cfg);return;}
    if(s.mode==="walk"){enter(s,"settle",.18);return;}
    choose(s,cfg,random,world);
}
function step(s,dt,world,cfg,random) {
    dt=clamp(dt,0,["walk","fly","fall","turn","land","anticipate"].indexOf(s.mode)<0?5:.08);random=random||Math.random;s.age+=dt;s.modeTime+=dt;
    s.approachCooldown=Math.max(0,s.approachCooldown-dt);s.ballCooldown=Math.max(0,s.ballCooldown-dt);
    if(s.mode==="drag")return s;
    s.satiety=clamp(s.satiety-dt*.015,0,100);
    s.energy=clamp(s.energy+dt*(s.mode==="sleep"?.8:s.mode==="idle"?.08:-.025),0,100);
    var floor=world.surfaces[0],perch=supportFor(world.surfaces,s);
    if(s.mode!=="fly"&&s.mode!=="fall") {
        if(!perch){detach(s);s.vy=0;s.vx=0;enter(s,"fall",10);}
        else {
            if(s.offset===null)s.offset=s.x-(perch.origin||0);
            var targetX=clamp((perch.origin||0)+s.offset,perch.left,perch.right);
            s.offset=targetX-(perch.origin||0);s.surface=perch.id;s.surfaceBase=perch.base||perch.id;
            s.x+=(targetX-s.x)*Math.min(1,dt*22);s.y+=(perch.y-s.y)*Math.min(1,dt*22);
        }
    }
    var cursor=world.cursor;
    if(cursor&&(cursor.sequence===undefined||cursor.sequence!==s.cursorSequence)) {
        var dx=cursor.x-s.x,dy=cursor.y-(s.y-cfg.size*.6),distance=Math.hypot(dx,dy);
        if(!cfg.reducedMotion&&s.mode!=="sleep")s.gaze=Math.round(clamp(dx/Math.max(cfg.size,1),-1,1)*10)/10;
        if(s.lastCursor&&s.approachCooldown<=0&&["idle","look","preen"].indexOf(s.mode)>=0&&priority(s,world,cfg)==="autonomous"&&cfg.cursorReactions&&!cfg.workMode&&!world.resting&&!cfg.reducedMotion) {
            var speed=Math.hypot(cursor.x-s.lastCursor.x,cursor.y-s.lastCursor.y)/Math.max(cursor.dt||dt,.001);
            if(distance<cfg.size*1.4&&speed>1100+s.trust*7){act(s,"startle");}
            else if(distance<cfg.size*2.5&&speed<140&&speed>2){enter(s,"look",1.6);s.view="front";s.approachCooldown=3;}
        }
        s.lastCursor={x:cursor.x,y:cursor.y};
        s.cursorSequence=cursor.sequence;
    }
    if((cfg.workMode||world.resting)&&s.age>=s.manualUntil&&s.goal!=="home"&&["sleep","fly","fall","drag"].indexOf(s.mode)<0)goHome(s,world,cfg);
    if(s.mode==="fly") {
        var destination=surfaceById(world.surfaces,s.target&&s.target.surface)||floor;
        var target=s.target||{x:s.x,y:floor.y,surface:"floor"};target.x=clamp(target.x,destination.left,destination.right);target.y=destination.y;target.surface=destination.id;
        var f=s.flight;
        if(!f){s.flight={fromX:s.x,fromY:s.y,time:0,duration:.7,arc:35};f=s.flight;}
        f.time+=dt;var t=clamp(f.time/f.duration,0,1),ease=t*t*(3-2*t);
        s.x=f.fromX+(target.x-f.fromX)*ease;s.y=f.fromY+(target.y-f.fromY)*ease-4*t*(1-t)*f.arc;
        if(Math.abs(target.x-s.x)>2)s.direction=target.x>s.x?1:-1;
        if(t>=1){s.x=target.x;s.y=target.y;attach(s,destination);s.flight=null;var follow=s.afterFlight; s.afterFlight="";enter(s,"land",.3,follow);emit(s,"land");}
    } else if(s.mode==="fall") {
        var oldY=s.y;s.vy+=760*dt;s.y+=s.vy*dt;s.x+=s.vx*dt;var landing=null;
        world.surfaces.forEach(function(p){if(s.vy>=0&&oldY<=p.y+1&&s.y>=p.y&&s.x>=p.left&&s.x<=p.right&&(!landing||p.y<landing.y))landing=p;});
        if(landing||s.y>=floor.y){landing=landing||floor;s.y=landing.y;s.vx=0;s.vy=0;attach(s,landing);enter(s,"land",.3,"shake");emit(s,"land");}
    } else {
        if(s.mode==="turn")s.view="front";
        else if(["look","notice","love","giggle","surprise","stretch"].indexOf(s.mode)>=0)s.view="threeQuarter";
        else if(s.mode!=="idle")s.view="side";
        s.remaining-=dt;
        if(s.mode==="walk"&&perch) {
            var object=targetItem(s,world),goalX=null;
            if(object&&object.surface!==s.surface){aimForItem(s,world,cfg);}
            else {
                if(object)goalX=object.x;
                else if(cfg.followCursor&&cursor&&!cfg.workMode)goalX=cursor.x;
                if(goalX!==null&&Math.abs(goalX-s.x)<cfg.size*(object?.48:.85)) {
                    if(object&&object.type==="pea"){enter(s,"sniff",.5,"eatGoal");}
                    else if(object&&s.ballCooldown<=0){object.vx=s.direction*(cfg.personality==="playful"?250:150);object.vy=-130;object.surface="";s.playCount++;s.ballCooldown=s.playCount>=4?20:1.3;if(s.playCount>=4){s.goal="";s.targetItem="";s.playCount=0;}enter(s,"nudge",.4);emit(s,"ball");}
                    else if(!object)enter(s,"look",1.3);
                } else {
                    var wanted=goalX===null?s.direction:goalX>s.x?1:-1;
                    if(wanted!==s.direction)turn(s,wanted);
                    else {
                        var velocity=cfg.speed*personalities[cfg.personality].speed;
                        var travel=s.direction*velocity*dt;s.offset+=travel;s.x+=travel;s.stride+=Math.abs(travel)/Math.max(12,cfg.size*.27)*Math.PI;
                        if(s.x<=perch.left||s.x>=perch.right){s.x=clamp(s.x,perch.left,perch.right);s.offset=s.x-(perch.origin||0);enter(s,"peek",.75,"edge");}
                    }
                }
            }
        }
        if(s.mode==="eatGoal")enter(s,"eat",1.3,"consume");
        if(s.remaining<=0)after(s,world,cfg,random);
    }
    s.x=clamp(s.x,Math.min(cfg.size/2,world.width/2),Math.max(cfg.size/2,world.width-cfg.size/2));
    s.y=clamp(s.y,Math.min(cfg.size,world.height),floor.y);
    return s;
}
function dynamicItems(items,world) {
    return items.some(function(o){
        if(o.consumed||o.held)return false;
        var p=supportFor(world.surfaces,o);
        return !p||Math.abs(o.vx)>.5||Math.abs(o.vy)>.5||Math.abs((p.origin||0)-o.origin)>.1||Math.abs(p.y-o.radius-o.y)>.1;
    });
}
function needsFrames(s,items,world,cfg) {
    if(!s)return false;
    if(dynamicItems(items,world))return true;
    if(s.mode!=="idle"&&s.mode!=="sleep"&&(!cfg.reducedMotion||["walk","fly","fall","turn","land","anticipate","drag"].indexOf(s.mode)>=0))return true;
    var p=supportFor(world.surfaces,s);
    return !p||Math.abs(s.y-p.y)>.1||s.offset!==null&&Math.abs(s.x-clamp((p.origin||0)+s.offset,p.left,p.right))>.1;
}
function mood(s,resting) {return resting||s.mode==="sleep"?"sleepy":s.energy<25?"resting":s.mode==="love"||s.mode==="giggle"?"happy":s.goal==="food"?"food":s.goal==="ball"?"playful":s.trust>55?"trusting":"curious";}
