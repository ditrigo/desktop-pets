"""Build the Desktop Duck master model, wardrobe, rig and sprite source renders.

Run with Blender's Python; integration/build_blender_assets.py packs the renders.
Axes: +X is the beak, -Y is the near wing, +Z is up. Units are metres only
for convenient editing. All rigid meshes have named armature vertex groups.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--preview-only', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(__file__).resolve().parent
contract=json.loads((SOURCE.parents[1]/'src/assets/duck-contract.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 360
scene.render.resolution_y = 336
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
if hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 32
scene.render.fps = 24
scene.view_settings.view_transform = 'Standard'
scene.world = bpy.data.worlds.new('Studio ambient')
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.6, .7, 1, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35


def rgba(code):
    values = [int(code[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values) + (1,)


def material(name, code, metal=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba(code)
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba(code)
    bsdf.inputs['Roughness'].default_value = .53
    bsdf.inputs['Metallic'].default_value = metal
    return m


M = {name: material(name, color, metal) for name, color, metal in [
    ('feather', '#ffdb62', 0), ('head', '#ffe17b', 0), ('cream', '#ffedaa', 0),
    ('wing', '#eebf49', 0), ('bill', '#ed9a42', 0), ('feet', '#d78437', 0),
    ('eye', '#24323b', 0), ('shine', '#fff8e7', 0), ('red', '#c95364', 0),
    ('gold', '#eac15e', .3), ('purple', '#7161a3', 0), ('purpleDark', '#4a416d', 0),
    ('cape', '#81516e', 0), ('capeLining', '#c78c9f', 0), ('navy', '#365c80', 0),
    ('white', '#f7f0da', 0), ('black', '#2c3446', 0), ('tan', '#d2b27b', 0),
    ('brown', '#74553c', 0), ('suit', '#cbdcdd', .1), ('teal', '#6a9aaa', .1),
    ('green', '#7ac5ae', .1), ('badge', '#e9985d', 0), ('chest', '#89604a', 0)
]}
GROUPS = {}
BONES = {'root': ((0, 0, 0), None), 'body': ((-.2, 0, .9), 'root'),
         'head': ((.42, 0, 1.42), 'body'),
         'wing.near': ((-.35, -.53, 1.13), 'body'),
         'wing.far': ((-.35, .53, 1.13), 'body'),
         'foot.near': ((-.2, -.31, .36), 'root'),
         'foot.far': ((-.2, .31, .36), 'root')}


def group(name):
    if name not in GROUPS:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
        GROUPS[name] = col
    return GROUPS[name]


def finish(obj, name, collection, mat, bone, bevel=.04):
    obj.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    group(collection).objects.link(obj)
    obj.data.materials.append(M[mat])
    if bevel:
        mod = obj.modifiers.new('Soft voxel edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    if bone:
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
        mod = obj.modifiers.new('Duck skeleton', 'ARMATURE')
        mod.object = rig
        obj.parent = rig
    return obj


def box(name, pos, size, mat, collection, bone='body', bevel=.035, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos, rotation=rotation)
    obj = bpy.context.object
    obj.scale = size
    return finish(obj, name, collection, mat, bone, bevel)


def cone(name, pos, r1, r2, height, mat, collection, bone='head', vertices=8, scale=(1,1,1)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=height, location=pos)
    obj = bpy.context.object
    obj.scale = scale
    return finish(obj, name, collection, mat, bone, .015)


def panel(name, vertices, faces, mat, collection, bone='body'):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    group(collection).objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    finish(obj, name, collection, mat, bone, .015)
    mod = obj.modifiers.new('Cloth thickness', 'SOLIDIFY')
    mod.thickness = .035
    return obj


armature = bpy.data.armatures.new('Duck skeleton')
rig = bpy.data.objects.new('DuckRig', armature)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (position, parent) in BONES.items():
    bone = armature.edit_bones.new(name)
    bone.head = position
    bone.tail = Vector(position) + Vector((0, .22, 0))
    if parent:
        bone.parent = armature.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True
for bone in rig.pose.bones:
    bone.rotation_mode = 'XYZ'

# Compact toy proportions, broad webbed feet and a distinct two-part bill.
box('Torso', (-.28, 0, .91), (1.65, 1.04, 1.16), 'feather', 'body', bevel=.13)
box('Cream breast', (.33, 0, .91), (.58, 1.055, .84), 'cream', 'body', bevel=.13)
box('Tail', (-1.12, 0, 1.03), (.51, .70, .32), 'feather', 'body', rotation=(0,-.30,0), bevel=.055)
box('Neck', (.38, 0, 1.46), (.65, .72, .57), 'head', 'head', 'head', bevel=.10)
box('Head', (.57, 0, 1.96), (.96, .94, .93), 'head', 'head', 'head', bevel=.12)
box('Upper bill', (1.20, 0, 1.78), (.56, .70, .17), 'bill', 'head', 'head', bevel=.045)
box('Lower bill', (1.16, 0, 1.685), (.48, .62, .055), 'feet', 'head', 'head', bevel=.018)
for i, x in enumerate((.32, .49)):
    box('Crest '+str(i), (x, 0, 2.43+i*.035), (.13, .22, .22), 'head', 'head', 'head', rotation=(0,-.23,0), bevel=.025)
for side, y in [('near', -.53), ('far', .53)]:
    box('Wing '+side, (-.35, y, .96), (.95, .16, .56), 'wing', 'wing.'+side, 'wing.'+side, bevel=.07)
    for i in range(2):
        box('Feather stripe '+side+str(i), (-.48, y+(-.087 if y<0 else .087), 1.04-i*.16), (.50-i*.1, .018, .045), 'cream', 'wing.'+side, 'wing.'+side, bevel=.012)
    box('Ankle '+side, (-.12, y*.59, .28), (.13, .13, .30), 'feet', 'foot.'+side, 'foot.'+side, bevel=.022)
    box('Webbed foot '+side, (.03, y*.59, .11), (.60, .36, .14), 'bill', 'foot.'+side, 'foot.'+side, bevel=.035)
# Two eyes sit on the beveled front corners: the same pair works from
# the side, the quarter view and the front, without duplicate face eyes.
for side, sign in [('near', -1), ('far', 1)]:
    rotation=(0,0,-sign*math.pi/4)
    for state, height in [('open',.22),('wide',.29),('closed',.045)]:
        box('Eye '+side+' '+state,(1.005,sign*.424,2.055),(.16,.045,height),
            'eye','eyes.'+state,'head',bevel=.018,rotation=rotation)
        if state!='closed':
            box('Eye shine '+side+' '+state,(1.025,sign*.444,2.10),(.045,.017,.05),
                'shine','eyes.'+state,'head',bevel=.007,rotation=rotation)

# Every hat is real geometry parented to the head bone.
cone('Wizard brim', (.57, 0, 2.43), .68, .68, .075, 'purpleDark', 'hat.wizard')
cone('Wizard crown', (.57, 0, 2.88), .46, .035, .87, 'purple', 'hat.wizard')
cone('Wizard band', (.57, 0, 2.53), .44, .40, .09, 'gold', 'hat.wizard')
for x, z in [(.53,2.80),(.73,2.65)]:
    box('Wizard rune', (x,-.255,z), (.075,.04,.10), 'gold', 'hat.wizard', 'head', rotation=(0,0,.2), bevel=.008)
cone('Explorer brim', (.57,0,2.43), .68,.68,.07,'tan','hat.explorer')
cone('Explorer crown', (.57,0,2.61), .44,.38,.35,'tan','hat.explorer')
cone('Explorer band', (.57,0,2.48), .452,.44,.09,'brown','hat.explorer')
cone('Chef band', (.57,0,2.55), .40,.40,.25,'white','hat.chef')
for x,y,z in [(.35,0,2.78),(.75,0,2.78),(.56,.2,2.81),(.56,-.2,2.81)]:
    box('Chef puff', (x,y,z), (.46,.43,.43),'white','hat.chef','head',bevel=.14)
cone('Santa fur band', (.57,0,2.45), .49,.49,.15,'white','hat.santa')
cone('Santa cap', (.63,0,2.78), .43,.10,.59,'red','hat.santa',scale=(1.15,1,1))
box('Santa pompom', (1.0,0,2.89), (.28,.28,.28),'white','hat.santa','head',bevel=.09)
cone('Pirate cap', (.57,0,2.56), .44,.34,.28,'black','hat.pirate')
# Tricorn brim: three rising corners and three low valleys.
points=[]
for i in range(6):
    a=i*math.pi/3
    points.append((.57+(.72 if i%2==0 else .42)*math.cos(a),(.72 if i%2==0 else .42)*math.sin(a),2.70 if i%2==0 else 2.43))
points.append((.57,0,2.40))
panel('Tricorn brim',points,[(i,(i+1)%6,6) for i in range(6)],'black','hat.pirate','head')
box('Pirate skull', (.60,-.40,2.62),(.16,.035,.14),'white','hat.pirate','head',bevel=.025)
for x in (.56,.65):
    box('Skull eye', (x,-.426,2.64),(.033,.015,.034),'black','hat.pirate','head',bevel=.004)
cone('Crown band', (.57,0,2.48), .49,.49,.18,'gold','hat.crown')
for i in range(6):
    a=i*math.pi/3
    cone('Crown point',(.57+.43*math.cos(a),.43*math.sin(a),2.68),.15,0,.30,'gold','hat.crown',vertices=4)
for x,y,mat in [(.57,-.496,'red'),(1.06,0,'green')]:
    box('Crown jewel',(x,y,2.49),(.15,.075,.13),mat,'hat.crown','head',bevel=.025)

# Modular garments share the torso rig; wings always remain free.
cone('Scarf collar',(.40,0,1.51),.43,.43,.17,'red','outfit.scarf',bone='body')
box('Scarf tail',(.21,-.60,1.05),(.22,.08,.67),'red','outfit.scarf',bevel=.025,rotation=(0,-.13,0))
for z in (.86,.93):
    box('Scarf stripe',(.23,-.647,z),(.23,.015,.035),'gold','outfit.scarf',bevel=.005)
box('Sailor shirt',(-.20,0,.72),(1.72,1.09,.71),'navy','outfit.sailor',bevel=.10)
for side in (-1,1):
    panel('Sailor collar',[(.40,side*.46,1.58),(-.23,side*.57,1.34),(.48,side*.58,1.04)],[(0,1,2)],'navy','outfit.sailor')
    for z in (.65,.72):
        box('Sailor stripe',(-.20,side*.559,z),(1.40,.015,.028),'white','outfit.sailor',bevel=.006)
box('Sailor tie',(.61,-.32,1.16),(.14,.12,.45),'red','outfit.sailor',bevel=.025,rotation=(0,-.15,0))
box('Space suit',(-.24,0,.87),(1.78,1.12,1.02),'suit','outfit.space',bevel=.13)
box('Space backpack',(-1.17,0,.99),(.28,.77,.70),'teal','outfit.space',bevel=.06)
box('Space control panel',(.03,-.60,1.06),(.48,.065,.34),'navy','outfit.space',bevel=.035)
for x,mat in [(-.09,'green'),(.09,'badge')]:
    box('Space indicator',(x,-.64,1.10),(.10,.02,.10),mat,'outfit.space',bevel=.012)
box('Space belt',(-.24,-.58,.58),(1.40,.035,.10),'teal','outfit.space',bevel=.02)
for side in (-1,1):
    panel('Cape panel',[(.44,side*.40,1.52),(-.93,side*.63,1.20),(-1.37,side*.70,.27),(.05,side*.58,.40)],[(0,1,2,3)],'cape','outfit.cape')
panel('Cape back',[(-.93,-.63,1.20),(-.93,.63,1.20),(-1.37,.70,.27),(-1.37,-.70,.27)],[(0,1,2,3)],'capeLining','outfit.cape')
box('Cape clasp',(.63,-.26,1.43),(.15,.16,.13),'gold','outfit.cape',bevel=.025)

# Eye visibility belongs to the same rig Action as the body animation.
rig['eyeState']=0  # 0=open, 1=closed, 2=surprised
for index,state in enumerate(('open','closed','wide')):
    for obj in GROUPS['eyes.'+state].objects:
        for channel in ('hide_render','hide_viewport'):
            driver=obj.driver_add(channel).driver
            variable=driver.variables.new();variable.name='eye'
            variable.targets[0].id=rig;variable.targets[0].data_path='["eyeState"]'
            driver.expression='eye != '+str(index)

# Holdout copies preserve occlusion when wings, hats and garments are exported
# separately; the body itself is supplied by a different runtime layer.
holdout=bpy.data.materials.new('Sprite occlusion')
nodes=holdout.node_tree.nodes;nodes.clear()
shader=nodes.new('ShaderNodeHoldout');output=nodes.new('ShaderNodeOutputMaterial')
holdout.node_tree.links.new(shader.outputs[0],output.inputs['Surface'])
for base in ('body','head'):
    for obj in list(GROUPS[base].objects):
        clone=obj.copy();clone.data=obj.data.copy();clone.name='Occluder '+obj.name
        clone.data.materials.clear();clone.data.materials.append(holdout)
        group('occluder.'+base).objects.link(clone)

# Lights stay in world space for consistent shading across all parts and views.
for name, pos, energy, size, color in [
    ('Key',(-3,-4,7),500,5,(1,.89,.73)),
    ('Fill',(4,-1,4),280,4,(.73,.84,1)),
    ('Rim',(-2,4,6),550,3,(1,.83,.59))]:
    bpy.ops.object.light_add(type='AREA',location=pos)
    obj=bpy.context.object;obj.name=name;obj.data.energy=energy;obj.data.shape='DISK';obj.data.size=size;obj.data.color=color
    obj.rotation_euler=(Vector((0,0,1.4))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add()
camera=bpy.context.object;camera.name='Sprite orthographic camera';camera.data.type='ORTHO';camera.data.ortho_scale=4.1
scene.camera=camera
WING_ANGLES=contract['wingAngles']
VIEWS=contract['cameraViews']


def view(name):
    target=Vector((0,0,1.70));position=Vector(VIEWS[name])
    camera.location=position
    camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()


def show(names):
    for key,col in GROUPS.items():
        col.hide_render=key not in names
        col.hide_viewport=key not in names
    bpy.context.view_layer.update()


def palette(name):
    colors={'yellow':('#ffdb62','#ffe17b','#ffedaa','#eebf49'),
            'mallard':('#b8ada0','#378a72','#956b50','#8d8271'),
            'white':('#eeeae0','#faf4e8','#fff8ec','#c9c7bd')}[name]
    for key,color in zip(('feather','head','cream','wing'),colors):
        M[key].diffuse_color=rgba(color)
        M[key].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=rgba(color)


# Real rig actions remain editable in the .blend file. One cycle is 24 frames.
ACTIONS={}
for name in ('Idle','Walk','Fly','Wave','Dance','Sleep','Eat','Drag','Love','Shake','Stretch','Land'):
    rig.animation_data_create()
    action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    for f in range(1,26,3):
        t=(f-1)/24*math.tau
        for b in rig.pose.bones:
            b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
        pb=rig.pose.bones
        if name=='Idle':pb['body'].scale.z=1+.016*math.sin(t)
        if name=='Walk':
            pb['root'].location.z=.045*(1-math.cos(2*t))
            for side,sign in [('near',1),('far',-1)]:pb['foot.'+side].rotation_euler.y=sign*.48*math.sin(t)
            pb['body'].rotation_euler.x=.035*math.sin(t)
        if name in ('Fly','Drag'):
            pb['wing.near'].rotation_euler.x=-.75+.7*math.sin(t)
            pb['wing.far'].rotation_euler.x=.75-.7*math.sin(t)
            pb['foot.near'].rotation_euler.y=.55;pb['foot.far'].rotation_euler.y=.55
            pb['body'].rotation_euler.y=-.08
        if name=='Wave':pb['wing.near'].rotation_euler.x=-.7+.5*math.sin(t)
        if name in ('Dance','Love'):
            pb['root'].location.z=.13*(1-math.cos(2*t));pb['body'].rotation_euler.z=.12*math.sin(t)
            pb['wing.near'].rotation_euler.x=-.5+.3*math.sin(t);pb['wing.far'].rotation_euler.x=.5-.3*math.sin(t)
            pb['head'].rotation_euler.y=.12*math.sin(t)
        if name=='Sleep':pb['head'].rotation_euler.y=.38;pb['body'].scale.z=.91
        if name=='Eat':pb['head'].rotation_euler.y=.35+.18*math.sin(t)
        if name=='Shake':pb['head'].rotation_euler.z=.22*math.sin(2*t);pb['body'].rotation_euler.x=.07*math.sin(2*t)
        if name=='Stretch':pb['body'].scale.z=1+.10*(1-math.cos(t));pb['head'].rotation_euler.y=-.13*math.sin(t/2)
        if name=='Land':pb['body'].scale.z=1-.15*(1-math.cos(t))/2
        rig['eyeState']=1 if name in ('Sleep','Love') else 0
        rig.keyframe_insert(data_path='["eyeState"]',frame=f,group='Face')
        for b in pb:
            for channel in ('location','rotation_euler','scale'):b.keyframe_insert(data_path=channel,frame=f,group=b.name)
    ACTIONS[name]=action
rig.animation_data.action=None
rig['eyeState']=0
for b in rig.pose.bones:b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
scene.frame_set(1)

# Full-model studio preview before exporting isolated textures.
view('threeQuarter');palette('yellow')
base=['body','head','wing.near','wing.far','foot.near','foot.far','eyes.open','eyes.closed','eyes.wide']
show(base+['hat.explorer','outfit.scarf'])
scene.render.filepath=str(OUT/'preview.png')
bpy.ops.render.render(write_still=True)
rig.animation_data.action=ACTIONS['Idle'];scene.frame_set(1)
scene.frame_start=1;scene.frame_end=25
bpy.context.view_layer.objects.active=rig
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
rig['readme']='Rigid voxel duck. +X beak, -Y near wing. Choose a rig Action; enable one hat and outfit collection. Rebuild with build_blender_assets.py.'
rig['actions']=','.join(ACTIONS)
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'desktop-duck.blend'))
if args.preview_only:
    print('PREVIEW_READY',flush=True);sys.exit(0)
exec(compile((SOURCE/'export_duck.py').read_text(),str(SOURCE/'export_duck.py'),'exec'))
