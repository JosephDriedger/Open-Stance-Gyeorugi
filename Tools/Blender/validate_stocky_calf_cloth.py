"""Run the repaired candidate through the existing dummy capture study."""
import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCalfClothReview';OUT.mkdir(exist_ok=True)
source=ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Stocky_Wrap.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
original=bpy.data.objects['RIG_Body_Stocky'];action=original.animation_data.action
assert action,'Study needs an active dummy action'
action_name=action.name
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky']
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.actions=[action_name]
r.animation_data_create();r.animation_data.action=dst.actions[0]
if hasattr(r.animation_data,'action_slot') and dst.actions[0].slots:r.animation_data.action_slot=dst.actions[0].slots[0]
for track in r.animation_data.nla_tracks:track.mute=True
for o in s.objects:
 if o.type=='MESH' and o.name!='Pants':
  for m in o.modifiers:
   if m.type=='CLOTH':
    for prop in ('show_viewport','show_render'):m.driver_remove(prop);setattr(m,prop,False)
r['BlenderCloth']=True;r['Wear_FootGuards']=True;review.build.refresh(r)
pants=bpy.data.objects['Pants'];cloth=next(m for m in pants.modifiers if m.type=='CLOTH')
cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=144
s.frame_end=144;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
for frame in range(1,145):
 s.frame_set(frame);ev=pants.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 assert all(math.isfinite(x) and abs(x)<5 for v in mesh.vertices for x in pants.matrix_world@v.co),frame
 ev.to_mesh_clear()
 if frame in (26,35,72,144):review.render(s,r,scale,OUT,'Frame_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,600,700)
(OUT/'report.json').write_text(json.dumps({'finite_geometry_passed':True,'frames':144,'action':action_name,'production_installed':False,'scope':'Pants cloth only; other cloth disabled. Visual review required.'},indent=2))
