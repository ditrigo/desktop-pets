"""Shared export stage; executed with a validated in-memory rig context."""
rig.animation_data.action=None
rig['eyeState']=0
for b in rig.pose.bones:b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
bpy.context.view_layer.update()

manifest={'contractVersion':1,'width':contract['canvas'][0],'height':contract['canvas'][1],'renderScale':3,'views':{},'actions':list(ACTIONS),'blender':bpy.app.version_string,'renders':[],'wingAngles':list(WING_ANGLES)}
manifest['partLabels']={key:str(col.get('duck_label',key.split('.',1)[1])) for key,col in GROUPS.items() if key.startswith(('hat.','outfit.'))}
start=time.monotonic()
for vn in VIEWS:
    view(vn)
    pivots={}
    for key in BONES:
        projected=world_to_camera_view(scene,camera,rig.matrix_world @ rig.data.bones[key].head_local)
        pivots[key]=[round(projected.x*120,3),round((1-projected.y)*112,3)]
    face=world_to_camera_view(scene,camera,Vector((.57,0,1.96)))
    manifest['views'][vn]={'pivots':pivots,'face':[round(face.x*120,3),round((1-face.y)*112,3)]}
    jobs=[]
    for pn in ('yellow','mallard','white'):
        jobs.append((pn+'-body',['body'],pn,0,1,None,0))
        for eye_index,eye in enumerate(('open','closed','wide')):
            jobs.append((pn+'-head',['head','eyes.'+eye],pn,eye_index,3,None,0))
        for side in ('near','far'):
            for i,angle in enumerate(WING_ANGLES):
                jobs.append((pn+'-wing.'+side,['wing.'+side,'occluder.body','occluder.head'],pn,i,len(WING_ANGLES),'wing.'+side,angle if side=='near' else -angle))
            for i,angle in enumerate((-.45,0,.45,.70)):
                jobs.append((pn+'-foot.'+side,['foot.'+side,'occluder.body'],pn,i,4,'foot.'+side,angle))
    jobs += [(key,[key,'occluder.head']+(['occluder.body'] if key.startswith('outfit.') else []),'yellow',0,1,None,0) for key in GROUPS if key.startswith(('hat.','outfit.'))]
    for name,groups,pn,pose,poses,joint,angle in jobs:
        if globals().get("SAMPLE_ONLY") and (vn!="side" or name!="yellow-body"):continue
        for b in rig.pose.bones:b.rotation_euler=(0,0,0)
        if joint:
            if joint.startswith('wing'):rig.pose.bones[joint].rotation_euler.x=angle
            else:rig.pose.bones[joint].rotation_euler.y=angle
        rig['eyeState']=pose if name.endswith('-head') else 0
        rig.update_tag()
        palette(pn);show(groups)
        filename=vn+'--'+name+'--'+str(pose)+'.png';scene.render.filepath=str(OUT/filename)
        bpy.ops.render.render(write_still=True)
        manifest['renders'].append({'view':vn,'part':name,'pose':pose,'poses':poses,'file':filename})
    print('VIEW_DONE',vn,'seconds',round(time.monotonic()-start,1),flush=True)
if globals().get('SAMPLE_ONLY'):
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('SAMPLE_DONE',flush=True);sys.exit(0)
if globals().get('SKIP_REFERENCE'):
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('BUILD_DONE',len(manifest['renders']),'parts, seconds',round(time.monotonic()-start,1),flush=True)
    sys.exit(0)
# Animated reference, including clothes attached to moving bones.
view('threeQuarter');palette('yellow');show(base+['hat.wizard','outfit.cape'])
animation=OUT/'animation';animation.mkdir(exist_ok=True)
for name in ('Walk','Fly','Wave','Dance','Sleep','Eat'):
    rig.animation_data.action=ACTIONS[name]
    show(base+['hat.wizard','outfit.cape'])
    for i,f in enumerate(range(1,25,3)):
        scene.frame_set(f);scene.render.filepath=str(animation/(name.lower()+f'-{i:02}.png'))
        bpy.ops.render.render(write_still=True)
    print('ANIMATION_DONE',name,flush=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('BUILD_DONE',len(manifest['renders']),'parts, seconds',round(time.monotonic()-start,1),flush=True)
