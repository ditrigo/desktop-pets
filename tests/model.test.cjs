const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const model = vm.createContext({Math, Object, Number, Array, JSON, isFinite, Error});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/PetModel.js'), 'utf8'), model);
const cfg = model.settings({});
const monitor = {id: 0, x: -85, y: 0, reserved: [0, 26, 0, 0], activeWorkspace: {id: 2}, specialWorkspace: {id: 0}};
const client = {address: 'window', monitor: 0, mapped: true, hidden: false, workspace: {id: 2}, at: [15, 220], size: [600, 500], fullscreen: 0};
function world(clients = [client]) { return {width: 1600, height: 1000, surfaces: model.surfaces(monitor, clients, 1600, 1000, 76, true)}; }
function advance(bird, seconds, w = world(), options = cfg) { for (let i = 0; i < seconds * 30; i++) model.step(bird, 1/30, w, options, () => 0.5); }

test('settings reject bad enums and bound dimensions', () => {
    const s = model.settings({size: 10000, speed: -1, palette: 'bad', enabled: 'false', artStyle:'../bad', hat:null, outfit:'bad'});
    assert.equal(s.size, 144); assert.equal(s.speed, 25); assert.equal(s.palette, 'yellow'); assert.equal(s.enabled, true);
    assert.equal(s.artStyle,'vector'); assert.equal(s.hat,'none'); assert.equal(s.outfit,'none');
    const dressed=model.settings({artStyle:'voxel',hat:'explorer',outfit:'scarf'});
    assert.equal(dressed.artStyle,'voxel'); assert.equal(dressed.hat,'explorer'); assert.equal(dressed.outfit,'scarf');
});
test('batch parser tolerates brackets, quotes and newlines inside window titles', () => {
    const input = JSON.stringify([monitor]) + '\n\n' + JSON.stringify([{...client, title: 'a [b] "c"\n\n} d'}]) + '\n\n' + '{"x": 30, "y": -4}';
    const out = model.parseBatch(input);
    assert.equal(out[1][0].title, 'a [b] "c"\n\n} d'); assert.equal(out[2].y, -4);
    assert.throws(() => model.parseBatch('unknown request'));
});
test('perches use logical coordinates with a negative monitor origin', () => {
    const surfaces = world().surfaces;
    assert.equal(surfaces.length, 3); assert.equal(surfaces[1].left, 100 + 76 * 0.35); assert.equal(surfaces[1].y, 220);
});
test('windows on other workspaces, hidden or fullscreen are excluded', () => {
    const clients = [{...client, workspace: {id: 3}}, {...client, hidden: true}, {...client, fullscreen: 1}];
    assert.equal(world(clients).surfaces.length, 1);
    assert.equal(world([{...client, workspace: {id: 3}, pinned: true}]).surfaces.length, 3);
    assert.equal(model.surfaces({...monitor, specialWorkspace: {id: -99}}, [client], 1600, 1000, 76, true).length, 1);
});
test('a released duck lands on the first edge it crosses', () => {
    const b = model.create(1600,1000,76); b.x = 300; b.y = 150; b.surface = ''; b.mode = 'fall';
    advance(b, 0.5); assert.equal(b.surface, 'window:top'); assert.equal(b.y, 220);
});
test('removing a supporting window makes the duck fall to the desktop', () => {
    const b = model.create(1600,1000,76); b.x = 300; b.y = 220; b.surface = 'window:top'; b.mode = 'sleep';
    advance(b, 2, world([])); assert.equal(b.surface, 'floor'); assert.equal(b.y, 994);
});
test('a moving window carries its duck to the new edge', () => {
    const b = model.create(1600,1000,76); b.x = 300; b.y = 220; b.surface = 'window:top'; b.mode = 'sleep';
    const w = world([{...client, at: [15, 300]}]); model.step(b,1/30,w,cfg);
    assert.ok(b.y>220&&b.y<300, 'window motion is interpolated');
    advance(b,.4,w); assert.ok(Math.abs(b.y-300)<.01);
});
test('flight survives its destination closing', () => {
    const b = model.create(1600,1000,76);
    model.flyTo(b, {x: 300, y: 220, surface: 'window:top'}); advance(b, 8, world([]));
    assert.equal(b.surface,'floor'); assert.equal(b.y,994);
});
test('long runs stay in bounds for every personality', () => {
    for (const personality of ['calm','curious','playful']) {
        const b = model.create(1600,1000,76);
        for (let n = 0; n < 20000; n++) {
            model.step(b,1/30,world(),model.settings({personality}),Math.random);
            assert.ok(Number.isFinite(b.x) && Number.isFinite(b.y));
            assert.ok(b.x >= 38 && b.x <= 1562 && b.y >= 76 && b.y <= 994);
        }
    }
});
test('reduced motion stays still after the current action finishes', () => {
    const b = model.create(1600,1000,76); advance(b, 30, world(),model.settings({reducedMotion:true}));
    assert.equal(b.mode,'idle'); assert.equal(b.x,1152);
});
test('dragging freezes physics; actions can wake a sleeping duck', () => {
    const b = model.create(1600,1000,76); b.mode = 'drag'; b.y = 150; advance(b, 2);
    assert.equal(b.y,150); assert.equal(b.mode,'drag');
    model.act(b,'sleep'); assert.equal(b.mode,'sleep'); model.act(b,'wake'); assert.equal(b.mode,'stretch');
    assert.equal(model.act(b,'unknown'),false);
});

function simulate(bird,w,seconds,options=cfg,random=()=>.5) {
    for(let n=0;n<Math.ceil(seconds*60);n++) {
        w.items=model.stepItems(w.items||[],1/60,w);
        model.step(bird,1/60,w,options,random);
    }
}
test('foreground windows remove covered segments from background perches',()=>{
    const behind={...client,address:'behind',focusHistoryID:2};
    const front={...client,address:'front',at:[190,150],size:[180,300],floating:true,focusHistoryID:0};
    const spans=world([behind,front]).surfaces.filter(p=>p.base==='behind:top');
    assert.equal(spans.length,2);
    assert.ok(spans.every(p=>p.right<275||p.left>455),'no support behind the foreground window');
});
test('fully occluded edges are not offered as destinations',()=>{
    const front={...client,address:'front',at:[-85,100],size:[1600,800],floating:true,focusHistoryID:0};
    assert.equal(world([client,front]).surfaces.filter(p=>p.window==='window').length,0);
});
test('a duck keeps its horizontal offset while its supporting window moves',()=>{
    const b=model.create(1600,1000,76);b.x=300;b.y=220;b.surface='window:top';b.mode='sleep';
    model.step(b,1/60,world(),cfg);
    simulate(b,world([{...client,at:[115,220]}]),.5);
    assert.ok(Math.abs(b.x-400)<.1);
});
test('a new jump includes anticipation and an arcing flight',()=>{
    const b=model.create(1600,1000,76);model.flyTo(b,{x:400,y:994,surface:'floor'});
    assert.equal(b.mode,'anticipate');simulate(b,world([]),.5);
    assert.equal(b.mode,'fly');assert.ok(b.y<994-10);
    simulate(b,world([]),4);assert.equal(b.surface,'floor');assert.ok(Number.isFinite(b.x));
});
test('walking foot phase follows distance and calm ducks walk slower',()=>{
    const a=model.create(1600,1000,76),b=model.create(1600,1000,76);
    for(const s of [a,b]){s.mode='walk';s.remaining=5;s.x=800;}
    simulate(a,world([]),1,model.settings({personality:'calm'}));
    simulate(b,world([]),1,model.settings({personality:'playful'}));
    assert.ok(800-b.x>800-a.x);assert.ok(b.stride>a.stride);
});
test('a dropped pea lands, attracts the duck, is eaten, and changes its memory',()=>{
    const b=model.create(1600,1000,76);b.x=900;b.offset=null;
    const w=world([]),pea=model.item('pea',1050,850,0,0,'pea');w.items=[pea];model.notice(b,pea);
    const fed=b.fed;simulate(b,w,14);
    assert.equal(w.items.length,0);assert.equal(b.fed,fed+1);assert.ok(b.satiety>65);assert.ok(b.trust>20);
});
test('food on another window triggers travel before eating',()=>{
    const b=model.create(1600,1000,76),w=world();
    const pea=model.item('pea',400,210,0,0,'pea');w.items=[pea];model.notice(b,pea);
    simulate(b,w,15);assert.equal(b.fed,1);assert.equal(w.items.length,0);
});
test('a ball bounces and can be nudged by a playful duck',()=>{
    const b=model.create(1600,1000,76);b.x=900;
    const w=world([]),ball=model.item('ball',940,983,0,0,'ball');ball.surface='floor';w.items=[ball];model.notice(b,ball);
    simulate(b,w,1.5,model.settings({personality:'playful'}));
    assert.equal(w.items.length,1);assert.ok(Math.abs(ball.vx)>10||Math.abs(ball.x-940)>15);assert.equal(b.event,'ball');
});
test('a held ball does not move and toys eventually expire',()=>{
    const w=world([]),ball=model.item('ball',800,500,300,-200,'ball');ball.held=true;w.items=[ball];
    for(let i=0;i<100;i++)model.stepItems(w.items,.03,w);
    assert.equal(ball.x,800);assert.equal(ball.y,500);
    ball.held=false;ball.age=301;assert.equal(model.stepItems(w.items,.03,w).length,0);
});
test('toys fall when their supporting window closes',()=>{
    const w=world([]),pea=model.item('pea',400,215,0,0,'pea');pea.surface='window:top';
    for(let i=0;i<180;i++)model.stepItems([pea],1/60,w);
    assert.equal(pea.surface,'floor');assert.equal(pea.y,989);
});
test('head, wing and belly gestures have different reactions',()=>{
    const b=model.create(1600,1000,76);
    model.act(b,'head');assert.equal(b.mode,'love');assert.equal(b.trust,22);
    model.act(b,'wing');assert.equal(b.mode,'wave');
    model.act(b,'belly');assert.equal(b.mode,'giggle');
    model.act(b,'startle');assert.equal(b.mode,'surprise');
});
test('a fast approach surprises an idle duck while work mode ignores it',()=>{
    const b=model.create(1600,1000,76);b.mode='idle';b.remaining=10;b.x=800;b.lastCursor={x:500,y:948};
    const w=world([]);w.cursor={x:800,y:948,dt:.1};
    model.step(b,1/60,w,cfg);assert.equal(b.mode,'surprise');
    model.enter(b,'idle',10);b.lastCursor={x:500,y:948};b.approachCooldown=0;
    model.step(b,1/60,w,model.settings({workMode:true}));assert.equal(b.mode,'idle');
});
test('quiet mode goes to a favorite spot and stays there despite a ball',()=>{
    const b=model.create(1600,1000,76),w=world([]);w.favorite={x:.8,edge:'floor'};w.items=[model.item('ball',300,983,0,0,'ball')];
    b.remaining=0;simulate(b,w,20,model.settings({workMode:true}));
    assert.ok(Math.abs(b.x-1280)<2);assert.equal(b.mode,'idle');assert.equal(b.goal,'');
});
test('timed rest settles at home and sleeping restores energy',()=>{
    const b=model.create(1600,1000,76),w=world([]);w.resting=true;w.favorite={x:.8,edge:'floor'};
    b.remaining=0;b.energy=10;simulate(b,w,15);
    assert.equal(b.mode,'sleep');assert.ok(b.energy>15);assert.ok(Math.abs(b.x-1280)<2);
});
test('persistent memory is bounded and survives a JSON round-trip',()=>{
    const before=model.memory({trust:70,energy:45,satiety:80,fed:12,restUntil:999,favorites:{'eDP-1':{x:.2,edge:'window'}},positions:{'eDP-1':{x:.6,edge:'floor'}}});
    const after=model.memory(JSON.parse(JSON.stringify(before)));
    assert.equal(JSON.stringify(before),JSON.stringify(after));
    const b=model.create(1600,1000,76,after.positions['eDP-1'],after);
    assert.equal(b.x,960);assert.equal(b.trust,70);assert.equal(b.fed,12);
    assert.equal(model.memory({trust:1000,energy:-5,favorites:{bad:{x:'no'}}}).energy,0);
});
test('pet names are bounded and preserve existing configuration defaults',()=>{
    assert.equal(model.settings({name:'  Кряк  '}).name,'Кряк');
    assert.equal(model.settings({name:'a'.repeat(100)}).name.length,32);
    assert.equal(model.settings({palette:'white'}).palette,'white');assert.equal(model.settings({}).workMode,false);
});

test('food removed, held, moved away or moved off its support cannot be consumed',()=>{
    for(const kind of ['missing','held','far','otherSurface']) {
        const b=model.create(1600,1000,76),w=world([]),pea=model.item('pea',b.x,989,0,0,'pea');
        pea.surface='floor';if(kind==='held')pea.held=true;if(kind==='far')pea.x=100;if(kind==='otherSurface')pea.surface='missing';
        w.items=kind==='missing'?[]:[pea];b.mode='eat';b.next='consume';b.remaining=.001;b.targetItem='pea';b.goal='food';
        model.step(b,.02,w,cfg,()=>.5);assert.equal(b.fed,0,kind);assert.ok(b.satiety<66,kind);
    }
});
test('memory v2 migrates without losing needs and v3 remembers app and edge',()=>{
    const old=model.memory({version:2,trust:77,fed:4,favorites:{screen:{x:.25,edge:'window'}}});
    assert.equal(old.version,3);assert.equal(old.trust,77);assert.equal(old.fed,4);assert.equal(old.favorites.screen.x,.25);
    const next=model.memory({favorites:{screen:{x:.4,edge:'window',app:'editor',side:'top',localX:.3}}});
    assert.equal(next.favorites.screen.app,'editor');assert.equal(next.favorites.screen.localX,.3);
    assert.equal(model.memory(JSON.parse(JSON.stringify(next))).favorites.screen.side,'top');
});
test('favorite window resolves by app and side, never the first unrelated window',()=>{
    const w=world([{...client,initialClass:'editor'}]);w.favorite={x:.3,edge:'window',app:'editor',side:'top',localX:.4};
    assert.equal(model.homeTarget(w,cfg).surface,'window:top');
    w.favorite.app='missing';assert.equal(model.homeTarget(w,cfg).surface,'floor');
    w.favorite={x:.3,edge:'window'};assert.equal(model.homeTarget(w,cfg).surface,'floor');
});
test('support cannot jump across an occluded part when fragments are renumbered',()=>{
    const b=model.create(1600,1000,76);b.x=300;b.surface='w:top';b.surfaceBase='w:top';b.offset=300;
    const spans=[{id:'floor',base:'floor',left:38,right:1562,y:994,origin:0},{id:'w:top',base:'w:top',left:500,right:900,y:220,origin:0}];
    assert.equal(model.supportFor(spans,b),null);
    spans.push({id:'w:top:1',base:'w:top',left:200,right:400,y:220,origin:0});
    assert.equal(model.supportFor(spans,b).id,'w:top:1');
});
test('sleep and idle advance real active seconds without a physics substep loop',()=>{
    const b=model.create(1600,1000,76);b.mode='sleep';b.remaining=300;b.energy=20;
    model.step(b,1,world([]),cfg,()=>.5);assert.equal(b.age,1);assert.equal(b.remaining,299);assert.ok(Math.abs(b.energy-20.8)<.001);
    assert.equal(model.needsFrames(b,[],world([]),cfg),false);
});
test('changing size near the edge wakes the clamp immediately',()=>{
    const b=model.create(1600,1000,76);b.mode='idle';b.x=38;b.offset=38;
    const large=model.settings({size:144}),w={width:1600,height:1000,surfaces:model.surfaces(monitor,[],1600,1000,144,false)};
    assert.equal(model.needsFrames(b,[],w,large),true);model.step(b,1/60,w,large,()=>.5);assert.ok(b.x>=72);
});
test('stationary toys do not require continuous frames; moving toys do',()=>{
    const w=world([]),pea=model.item('pea',400,989,0,0,'pea');pea.surface='floor';
    assert.equal(model.dynamicItems([pea],w),false);pea.surface='';assert.equal(model.dynamicItems([pea],w),true);
});
test('toys on a moving support activate physics even when the duck is idle',()=>{
    const w=world(),pea=model.item('pea',400,215,0,0,'pea');pea.surface='window:top';pea.origin=100;
    model.stepItems([pea],1/60,w);assert.equal(model.dynamicItems([pea],w),false);
    const moved=world([{...client,at:[115,300]}]);assert.equal(model.dynamicItems([pea],moved),true);
    model.stepItems([pea],1/60,moved);assert.ok(Math.abs(pea.x-500)<.01);assert.equal(pea.y,295);
});
test('manual play during scheduled rest returns home when its lease ends',()=>{
    const b=model.create(1600,1000,76),w=world([]);w.resting=true;w.favorite={x:.8,edge:'floor'};
    model.act(b,'dance');simulate(b,w,1);assert.equal(b.mode,'dance');
    simulate(b,w,15);assert.equal(b.mode,'sleep');assert.ok(Math.abs(b.x-1280)<2);
});
test('cursor reactions can be disabled and samples are consumed only once',()=>{
    const b=model.create(1600,1000,76);b.mode='idle';b.remaining=10;b.x=800;b.lastCursor={x:500,y:948};
    const w=world([]);w.cursor={x:800,y:948,dt:.1,sequence:1};
    model.step(b,0,w,model.settings({cursorReactions:false}));assert.equal(b.mode,'idle');
    b.lastCursor={x:500,y:948};model.step(b,0,w,cfg);assert.equal(b.mode,'idle');
    w.cursor.sequence=2;model.step(b,0,w,cfg);assert.equal(b.mode,'surprise');
});
test('unknown actions leave the model intact',()=>{
    const b=model.create(1600,1000,76);model.act(b,'dance');const before=JSON.stringify(b);
    assert.equal(model.act(b,'not-an-action'),false);assert.equal(JSON.stringify(b),before);
});
test('full ducks do not autonomously chase more peas',()=>{
    const b=model.create(1600,1000,76),w=world([]);b.satiety=100;b.age=20;b.remaining=0;b.mode='idle';
    w.items=[model.item('pea',b.x,989,0,0,'pea')];model.choose(b,cfg,()=>.1,w);assert.notEqual(b.goal,'food');
});

function loadPure(name) {
    const context=vm.createContext({Math,Object,Number,Array,JSON,isFinite,Error});
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/'+name),'utf8'),context);return context;
}

test('host-owned tooltips receive escaped user text',()=>{
    const text=loadPure('PetText.js');
    for(const value of ['<img src="https://example.invalid/tracker">',"<b>duck & friends</b>","\"'<script>bad</script>"]){
        const escaped=text.escapeMarkup(value);
        assert.equal(escaped.includes('<'),false);
        assert.equal(escaped.includes('>'),false);
        assert.ok(escaped.includes('&lt;'));
    }
    assert.equal(text.escapeMarkup('Ducky'),'Ducky');
});
test('command policy preserves maintenance during pause and reports environmental blocks',()=>{
    const p=loadPure('PetPolicy.js'),state={ready:true,enabled:true,visible:true,hasScene:true,paused:true,dragging:false,locked:false};
    assert.equal(p.blocked('clear',state),'');assert.equal(p.blocked('remember',state),'');assert.equal(p.blocked('dance',state),'paused');
    assert.equal(p.blocked('wake',state),'');state.locked=true;assert.equal(p.blocked('wake',state),'locked');
    assert.equal(p.blocked('wat',state),'unknown action');state.locked=false;state.paused=false;state.dragging=true;assert.equal(p.blocked('feed',state),'dragging');
});
test('world cache includes geometry-affecting flags but ignores titles',()=>{
    const w=loadPure('WorldModel.js'),base=w.clients([client]);
    assert.equal(JSON.stringify(base),JSON.stringify(w.clients([{...client,title:'private title'}])));
    for(const key of ['pinned','floating','hidden','fullscreen','visible','monitor','focusHistoryID']) {
        const value=key==='visible'?false:['fullscreen','monitor','focusHistoryID'].includes(key)?9:true;
        assert.notEqual(JSON.stringify(base),JSON.stringify(w.clients([{...client,[key]:value}])),key);
    }
});
test('fixed monitor survives focus changes and falls back after hotplug',()=>{
    const w=loadPure('WorldModel.js'),monitors=[{name:'left',id:0,x:-1600},{name:'right',id:1,x:0}];
    assert.equal(w.availableMonitor(monitors,{monitorMode:'fixed',monitor:'left'},'right'),'left');
    assert.equal(w.availableMonitor(monitors.slice(1),{monitorMode:'fixed',monitor:'left'},'right'),'right');
    assert.equal(w.availableMonitor(monitors,{monitorMode:'follow'},'right'),'right');
});

test('wardrobe presets change only accessories and return independent patches',()=>{
    const looks=loadPure('PetLooks.js');
    for(const entry of looks.options){
        const patch=looks.patch(entry.key);assert.deepEqual(Object.keys(patch).sort(),['hat','outfit']);
        const before=model.settings({artStyle:'pixel',palette:'white',name:'Утя',size:96});
        const after=model.settings({...before,...patch});assert.equal(after.artStyle,'pixel');assert.equal(after.palette,'white');assert.equal(after.size,96);assert.equal(after.name,'Утя');
        assert.equal(looks.matches(after,entry),true);
    }
    const patch=looks.patch('wizard');patch.hat='none';assert.equal(looks.patch('wizard').hat,'wizard');assert.equal(looks.patch('unknown'),null);
});

test('all flat clothes survive settings, saved looks and renderer switches',()=>{
    const looks=loadPure('PetLooks.js');
    const catalog=loadPure('PetCatalog.js').data;
    assert.deepEqual(Array.from(looks.hats,h=>h.key).filter(k=>k!=='none').sort(),Array.from(catalog.hats,h=>h.key).sort());
    assert.deepEqual(Array.from(looks.outfits,o=>o.key).filter(k=>k!=='none').sort(),Array.from(catalog.outfits,o=>o.key).sort());
    for(const look of looks.options){
        for(const style of ['vector','pixel']){
            const cfg=model.settings({artStyle:style,...looks.patch(look.key)});
            assert.equal(cfg.hat,look.hat);assert.equal(cfg.outfit,look.outfit);
            const saved=model.memory({looks:[{id:'new',name:look.label,kind:'full',...cfg}]}).looks[0];
            assert.equal(saved.hat,look.hat);assert.equal(saved.outfit,look.outfit);
            const other=model.settings({...cfg,artStyle:'voxel'});
            const restored=model.settings({...other,artStyle:style});
            assert.equal(restored.hat,look.hat);assert.equal(restored.outfit,look.outfit);
        }
    }
    assert.equal(looks.available(looks.options,'voxel').every(x=>x.models.includes('voxel')),true);
    assert.ok(looks.available(looks.options,'pixel').length>=14);
});

test('intent priorities and a completed manual action hold off autonomous toys',()=>{
 const b=model.create(1600,1000,76),w=world([]);w.items=[model.item('ball',b.x+100,994,0,0,'temptation')];
 model.enter(b,'drag',10);assert.equal(model.priority(b,w,cfg),'drag');
 model.act(b,'dance');w.resting=true;assert.equal(model.priority(b,w,cfg),'manual');
 w.resting=false;model.enter(b,'idle',.01);model.step(b,.1,w,cfg,()=>.5);
 assert.equal(b.goal,'');assert.equal(b.mode,'idle');
 b.age=b.manualUntil;w.resting=true;assert.equal(model.priority(b,w,cfg),'rest');
 w.resting=false;assert.equal(model.priority(b,w,cfg),'autonomous');
});
test('quiet hours cross midnight, use exact endpoints and validate input',()=>{
 const c=model.settings({quietHours:true,quietStart:'22:00',quietEnd:'08:00'});
 assert.equal(model.quietAt(c,22*60),true);assert.equal(model.quietAt(c,8*60),false);
 assert.equal(model.quietAt(c,3*60),true);assert.equal(model.quietAt(c,12*60),false);
 assert.equal(model.settings({quietStart:'27:99'}).quietStart,'22:00');
 assert.equal(model.quietAt({...c,quietEnd:'22:00'},0),false);
});
test('local looks migrate, bound collection and recover unknown clothes',()=>{
 const old=model.memory({version:3,trust:73,fed:17,favorites:{display:{x:.7}},positions:{display:{x:.3}}});
 assert.equal(old.looks.length,0);assert.equal(old.trust,73);assert.equal(old.fed,17);
 const looks=Array.from({length:20},(_,i)=>({version:1,id:'id'+i,name:' My look ',kind:i?'wardrobe':'full',hat:'removed',outfit:'cape',artStyle:'pixel',palette:'white'}));
 const m=model.memory({...old,looks});assert.equal(m.looks.length,12);assert.equal(m.looks[0].hat,'none');assert.equal(m.looks[0].artStyle,'pixel');
 assert.equal(m.looks[1].artStyle,undefined);assert.equal(m.looks[0].name,'My look');assert.equal(m.favorites.display.x,.7);
 assert.equal(JSON.stringify(model.memory(JSON.parse(JSON.stringify(m)))),JSON.stringify(m));
});

test('walking finishes with a bounded stop phase before the next initiative',()=>{
 const b=model.create(1600,1000,76),w=world([]);model.enter(b,'walk',.01);b.initiativeAt=b.age+20;
 model.step(b,.02,w,cfg,()=>.5);assert.equal(b.mode,'settle');
 advance(b,.3,w,cfg);assert.equal(b.mode,'idle');assert.equal(model.needsFrames(b,[],w,cfg),false);
});
