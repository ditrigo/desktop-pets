"""Export a selected .blend in memory; never save over the artist's source."""
import argparse,json,math,re,sys,time
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--check-only',action='store_true')
parser.add_argument('--sample-only',action='store_true')
parser.add_argument('--assets-only',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
SOURCE=Path(__file__).resolve().parent
contract=json.loads((SOURCE.parents[1]/'src/assets/duck-contract.json').read_text())
OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
rig=bpy.data.objects.get('DuckRig')
if not rig or rig.type!='ARMATURE':raise ValueError('DuckRig armature is required')
BONES=contract['bones']
for bone in BONES:
    if bone not in rig.data.bones:raise ValueError('Missing bone '+bone)
required=['body','head','wing.near','wing.far','foot.near','foot.far','eyes.open','eyes.closed','eyes.wide']
required += ['hat.'+x for x in ['wizard','pirate','santa','explorer','chef','crown']]
required += ['outfit.'+x for x in ['scarf','sailor','space','cape']]
GROUPS={k:bpy.data.collections.get(k) for k in required}
for key,col in GROUPS.items():
    if not col or not col.objects:raise ValueError('Missing/empty collection '+key)
for col in bpy.data.collections:
    if col.name.startswith(('hat.','outfit.')):
        key=col.name.split('.',1)[1]
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',key) or key in ('none','constructor','prototype'):raise ValueError('Invalid accessory collection '+col.name)
        if col.objects:GROUPS[col.name]=col
M={k:bpy.data.materials.get(k) for k in ['feather','head','cream','wing']}
if not all(M.values()):raise ValueError('Missing plumage materials')
camera=scene.camera
if not camera or camera.data.type!='ORTHO':raise ValueError('Orthographic camera is required')
ACTIONS={k:bpy.data.actions.get(k) for k in ['Idle','Walk','Fly','Wave','Dance','Sleep','Eat','Drag','Love','Shake','Stretch','Land']}
if not all(ACTIONS.values()):raise ValueError('Missing rig Actions')
print('BLEND_VALIDATED',bpy.data.filepath,flush=True)
if args.check_only:sys.exit(0)
# Occluders are refreshed from edited meshes in this temporary Blender process.
holdout=bpy.data.materials.get('Sprite occlusion')
if not holdout:raise ValueError('Missing holdout material')
for name in ['body','head']:
    key='occluder.'+name;col=bpy.data.collections.get(key)
    if not col:col=bpy.data.collections.new(key);scene.collection.children.link(col)
    for obj in list(col.objects):bpy.data.objects.remove(obj,do_unlink=True)
    for obj in GROUPS[name].objects:
        clone=obj.copy();clone.data=obj.data.copy();clone.data.materials.clear();clone.data.materials.append(holdout);col.objects.link(clone)
    GROUPS[key]=col
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=360;scene.render.resolution_y=336;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
WING_ANGLES=contract['wingAngles'];VIEWS=contract['cameraViews']
SAMPLE_ONLY=args.sample_only
SKIP_REFERENCE=args.assets_only
base=required[:9]
def rgba(code):
    values = [int(code[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values) + (1,)


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


if not SKIP_REFERENCE and not SAMPLE_ONLY:
    view('threeQuarter');palette('yellow');show(base+['hat.explorer','outfit.scarf'])
    scene.render.filepath=str(OUT/'preview.png');bpy.ops.render.render(write_still=True)
exec(compile((SOURCE/'export_duck.py').read_text(),str(SOURCE/'export_duck.py'),'exec'))
