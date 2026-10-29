import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.ROOT/'Resources/Models/CharacterSuite/LeanTall/Gameplay_High.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_LeanTall'];r.animation_data.action=None
for t in r.animation_data.nla_tracks:t.mute=True
for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
r['HairStyle']=0;a.build.refresh(r);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;a.audit.pose(r,'Neutral',scale)
for o in s.objects:
 if o.type=='MESH' and o.name.startswith('Hair_'):
  for mat in o.data.materials:
   if mat and mat.use_nodes:
    for n in mat.node_tree.nodes:
     if n.type=='TEX_IMAGE':n.extension='REPEAT'
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
a.render(s,r,scale,out,'Repeat_Seam',(.4,-1,1.9),(0,0,1.65),.52,600,600)
