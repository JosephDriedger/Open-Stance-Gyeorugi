"""Additional visual acceptance checks for the uninstalled calf-fit candidate."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT
OUT=ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfClearance/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];pants=bpy.data.objects['Pants']
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
had_custom=pants.data.has_custom_normals
# Automatic loop normals are regenerated from the corrected garment surface.
if had_custom:pants.data.normals_split_custom_set([(0,0,0)]*len(pants.data.loops))
pants.data.update()
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
images=[]
for gear in (False,True):
 r['Wear_FootGuards']=gear;review.build.refresh(r)
 for label,side in [('Front_Kick_L','l'),('Side_Kick_R','r'),('Ankle_Extended','l'),('Heel_Back_L','l'),('Lunge_R','r'),('Deep_Squat','l')]:
  review.audit.pose(r,label,scale)
  target=r.matrix_world@r.pose.bones['foot_'+side].matrix.translation+Vector((0,0,.075*scale))
  position=target+Vector((1 if side=='l' else -1,-.6,.25))*scale
  images.append(review.render(s,r,1,OUT,('Gear_' if gear else 'Bare_')+label,tuple(position),tuple(target),.48*scale,600,600))
review.audit.pose(r,'Neutral',scale)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'had_custom_normals':had_custom,'normals_recomputed':had_custom,'images':images,'cloth_enabled':bool(r.get('BlenderCloth'))},indent=2))
