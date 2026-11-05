import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Files/Resources/Models/CharacterSuite/Stocky/Gameplay_High.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r.animation_data_create();r.animation_data.action=None
for t in r.animation_data.nla_tracks:t.mute=True
r['BlenderCloth']=False;r['Wear_Protector']=False;r['Wear_Helmet']=False;r['Wear_FootGuards']=False;r.update_tag();s.frame_set(1)
body=bpy.data.objects['Body'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;keep=set()
for side in 'lr':
 aa=r.matrix_world@r.data.bones['calf_'+side].head_local;bb=r.matrix_world@r.data.bones['foot_'+side].head_local;axis=(bb-aa).normalized()
 for v in body.data.vertices:
  p=body.matrix_world@v.co;t=(p-bb).dot(axis);rad=(p-bb-axis*t).length
  if -.22*scale<t<.30*scale and rad<.14*scale:keep.add(v.index)
for name in ['CoveredBy_Jacket','CoveredBy_Pants']:
 g=body.vertex_groups.get(name)
 if g:g.remove(list(keep))
review.audit.pose(r,'Front_Kick_L',scale);s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.065*scale));position=target+Vector((1,-.4,.2))*scale
review.render(s,r,1,OUT,'SkinOverlap_Pilot',tuple(position),tuple(target),.4*scale,600,600)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SkinOverlap_Pilot.blend'),compress=True)
print('RESTORED_MASK_REGION',len(keep),flush=True)
