import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/ClothStructureAudit';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Stocky_Wrap.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r['BlenderCloth']=False;r['Wear_Protector']=False;r['Wear_Helmet']=False;r.update_tag();s.frame_set(35)
rows=[]
for name in ['Pants','Jacket','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
 o=bpy.data.objects[name];k=o.data.shape_keys
 rows.append({'object':name,'vertices':len(o.data.vertices),'modifiers':[(m.name,m.type,m.show_viewport) for m in o.modifiers],'keys':[(x.name,x.value) for x in k.key_blocks] if k else [],'drivers':[(d.data_path,d.driver.expression) for d in k.animation_data.drivers] if k and k.animation_data else [],'groups':[g.name for g in o.vertex_groups]})
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
a.render(s,r,1,out,'Stocky_Kinematic35',(4,-.8,1.65),(0,-.25,.95),2.25,640,720)
(out/'stocky_structure.json').write_text(json.dumps(rows,indent=2))

