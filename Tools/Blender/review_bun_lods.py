import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
sroot=a.ROOT/'Resources/Models/HairFormRefinement';d=sroot/'LODReview';d.mkdir(exist_ok=True)
for level in ['Gameplay_Far','Crowd_Near','Crowd_Far']:
 bpy.ops.wm.open_mainfile(filepath=str(sroot/'Medium'/(level+'.blend')));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r.animation_data_create();r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 r['HairStyle']=5;r['Wear_Helmet']=False;r['Wear_Protector']=False;a.build.refresh(r);z=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;s.cycles.samples=16
 a.render(s,r,z,d,level,(.45,1,1.8),(0,.05,1.65),.45,480,480)
