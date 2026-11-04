import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite/Stocky/Gameplay_High.blend'));s=bpy.context.scene
for o in list(s.objects):
 if o.type in ('MESH','ARMATURE') and o.name not in ('Ground','Mat','Floor'):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Resources/Models/CharacterSuite/Stocky/Gameplay_High_Dobok.fbx'))
r=next(o for o in s.objects if o.type=='ARMATURE');r.animation_data_create();r.animation_data.action=None
for t in r.animation_data.nla_tracks:t.mute=True
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
review.audit.pose(r,'Front_Kick_L',scale)
target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.065*scale));position=target+Vector((1,-.4,.2))*scale
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
review.render(s,r,1,OUT,'Before_FBX_Front_Kick_L',tuple(position),tuple(target),.4*scale,600,600)
