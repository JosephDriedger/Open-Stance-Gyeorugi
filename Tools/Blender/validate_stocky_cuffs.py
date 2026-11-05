import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery';images=[]
native=OUT/'Files/Resources/Models/CharacterSuite/Stocky/Gameplay_High.blend'
bpy.ops.wm.open_mainfile(filepath=str(native));pants=bpy.data.objects['Pants'];native_points=[pants.matrix_world@v.co for v in pants.data.vertices]
def prepare():
 s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE' and 'RIG_Body' in o.name)
 r.animation_data_create();r.animation_data.action=None
 for track in r.animation_data.nla_tracks:track.mute=True
 for key in ['BlenderCloth','Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[key]=False
 r.update_tag();bpy.context.view_layer.update();s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
 return s,r,(r.matrix_world@r.data.bones['head'].head_local).z/1.578
def close(s,r,scale,label,side='l'):
 target=r.matrix_world@r.pose.bones['foot_'+side].matrix.translation+Vector((0,0,.065*scale))
 position=target+Vector((1 if side=='l' else -1,-.4,.2))*scale
 images.append(review.render(s,r,1,OUT,label,tuple(position),tuple(target),.40*scale,600,600))
s,r,scale=prepare()
for pose,side in [('Neutral','l'),('Front_Kick_L','l'),('Front_Kick_R','r'),('Side_Kick_L','l'),('Ankle_Flexed','l'),('Ankle_Extended','l'),('Deep_Squat','l')]:
 review.audit.pose(r,pose,scale);close(s,r,scale,'Native_'+pose,side)
# Confirm the actual reported sample pose, not just the synthetic ROM poses.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Files/Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Stocky_Wrap.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r['BlenderCloth']=False;r['Wear_Protector']=False;r['Wear_Helmet']=False;r.update_tag();s.frame_set(35);s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
close(s,r,scale,'Native_Reported_Sample')
# Import the binary-patched FBX into the same lit scene after removing characters.
bpy.ops.wm.open_mainfile(filepath=str(native));s=bpy.context.scene
for o in list(s.objects):
 if o.type in ('MESH','ARMATURE') and o.name not in ('Ground','Mat','Floor'):bpy.data.objects.remove(o,do_unlink=True)
fbx=OUT/'Files/Resources/Models/CharacterSuite/Stocky/Gameplay_High_Dobok.fbx'
bpy.ops.import_scene.fbx(filepath=str(fbx));pants=next(o for o in s.objects if o.type=='MESH' and o.name.startswith('Pants'))
tree=KDTree(len(native_points))
for i,p in enumerate(native_points):tree.insert(p,i)
tree.balance();maximum=max(tree.find(pants.matrix_world@v.co)[2] for v in pants.data.vertices)
assert maximum<.0001,maximum
s,r,scale=prepare()
for pose in ('Front_Kick_L','Ankle_Flexed','Ankle_Extended'):
 review.audit.pose(r,pose,scale);close(s,r,scale,'FBX_'+pose)
(OUT/'reimport_validation.json').write_text(json.dumps({'passed':True,'native_fbx_maximum_vertex_distance_m':maximum,'images':images,'scope':'Close cuff checks only. Visual review required; other known clothing issues remain.'},indent=2))
print('STOCKY_CUFF_REIMPORT_VALIDATED',maximum,flush=True)
