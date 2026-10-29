import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_crew_surface_finish as f
for kind,level in [('Medium','Crowd_Far'),('LeanTall','Gameplay_High')]:
 for rev,root in [('Before',f.f.ROOT/'Resources/Models/CharacterSuite'),('After',f.OUT)]:
  bpy.ops.wm.open_mainfile(filepath=str(root/kind/(level+'.blend')));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.animation_data.action=None
  for t in r.animation_data.nla_tracks:t.mute=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  r['HairStyle']=0;f.f.review.build.refresh(r);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;f.f.review.audit.pose(r,'Neutral',scale);s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
  f.f.review.render(s,r,scale,f.OUT,kind+'_'+level+'_'+rev+'64',(.4,-1,1.9),(0,0,1.65),.52,600,600)
