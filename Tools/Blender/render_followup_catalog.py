import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_followup as fix
import audit_sparring_styles as a
for kind in sys.argv[sys.argv.index('--')+1:]:
 for level in ['Gameplay_High','Preview','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
  bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/kind/(level+'.blend')))
  s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.animation_data_create();r.animation_data.action=None
  for t in r.animation_data.nla_tracks:t.mute=True
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','BlenderCloth']:r[prop]=False
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True
  for style in [0,1]:
   r['JacketStyle']=style;a.build.refresh(r)
   label='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
   if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions['Crowd_StandingIdle'];s.frame_set(16)
   else:a.audit.pose(r,'Neutral',scale)
   a.render(s,r,scale,fix.OUT/kind,f'{level}_{style}_{label}',(.8,-4,1.7),(0,0,.96),2.35,480,540)
