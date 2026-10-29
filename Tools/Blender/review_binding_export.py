import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/BindingDelivery';d=out/'ExportReview';d.mkdir(exist_ok=True)
for kind in ['Medium','Female_Athletic','Tall']:
 for style in ['', 'WhiteVNeck']:
  native=out/'Files/Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
  bpy.ops.wm.open_mainfile(filepath=str(native));s=bpy.context.scene;s.cycles.samples=12
  for o in list(s.objects):
   if o.type in ['MESH','ARMATURE'] and o.name not in ['Ground','Mat','Floor']:bpy.data.objects.remove(o,do_unlink=True)
  path=out/'Files/Resources/Models/CharacterSuite'/kind/style/'Gameplay_High_Sparring.fbx'
  bpy.ops.import_scene.fbx(filepath=str(path));r=next(o for o in s.objects if o.type=='ARMATURE');scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  a.render(s,r,scale,d,kind+'_'+(style or 'Wrap'),(.2,-4,1.3),(0,0,1.15),.9,600,600)
(d/'complete.txt').write_text('Six independently imported FBX renders completed.\n')
