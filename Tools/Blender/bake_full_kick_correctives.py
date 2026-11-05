import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;BASE=ROOT/'Resources/Models/FinalRefinement';OUT=BASE/'StockyFullKickCorrectives';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'FootguardSmoothKickReview/Animation_Test.blend'))
samples={}
for frame in range(1,145):
 bpy.context.scene.frame_set(frame)
 samples[frame]={o.name:{k.name:k.value for k in o.data.shape_keys.key_blocks if k.name!='Basis'} for o in bpy.context.scene.objects if o.type=='MESH' and o.data.shape_keys and not o.get('SimulationOnly')}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'StockyFullKickReview/Full_Export_Kick.blend'))
mapped={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.data.shape_keys:continue
 name=o.name.rsplit('.',1)[0]
 if name not in samples[1]:continue
 mapped[o.name]=name
 for frame,values in samples.items():
  for key,value in values[name].items():
   if key in o.data.shape_keys.key_blocks:
    k=o.data.shape_keys.key_blocks[key];k.value=value;k.keyframe_insert('value',frame=frame)
s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE');scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
for frame in (26,35):
 s.frame_set(frame)
 review.render(s,r,scale,OUT,f'Full_{frame}',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
 review.render(s,r,scale,OUT,f'Hip_{frame}',(2,-.7,1.25),(0,-.1,.95),.85,800,800)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Full_Export_Kick.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'frames':144,'mapped_meshes':mapped,'scope':'Existing native shape values baked to full FBX reimport, alongside previously baked skeletal motion. No geometry edits or cloth simulation; visual acceptance separate.'},indent=2))
