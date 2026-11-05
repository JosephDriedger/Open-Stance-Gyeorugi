import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardFairingReview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardRemeshRefined/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;rows=[]
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];before=[v.co.copy() for v in o.data.vertices]
 for m in list(o.modifiers):o.modifiers.remove(m)
 mod=o.modifiers.new('Surface_fairing','LAPLACIANSMOOTH');mod.iterations=20;mod.lambda_factor=.5;mod.lambda_border=0;mod.use_volume_preserve=True;mod.use_normalized=True
 with bpy.context.temp_override(object=o,active_object=o):bpy.ops.object.modifier_apply(modifier=mod.name)
 if o.data.has_custom_normals:o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
 for p in o.data.polygons:p.use_smooth=True
 for e in o.data.edges:e.use_edge_sharp=False
 mod=o.modifiers.new('Deform','ARMATURE');mod.object=r
 rows.append({'object':name,'maximum_displacement_m':max((v.co-before[v.index]).length for v in o.data.vertices)})
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'changes':rows},indent=2))
