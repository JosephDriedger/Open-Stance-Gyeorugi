"""Inspect and test a small outward clearance for chest protector edge binding."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/ProtectorBindingClearance';out.mkdir(exist_ok=True)
s,r,scale,src=a.load('Medium','Gameplay_High');s.cycles.samples=16
rows=[]
for o in s.objects:
 if o.type!='MESH' or not o.name.startswith(('Smooth_Buckle_Back__','Quilted_Lace_Back__')):continue
 rows.append({'name':o.name,'vertices':len(o.data.vertices)})
 if not any(word in o.name for word in ['Bound_Hem','Bound_Upper_Edge','Rear_Wing_Binding']):continue
 inverse=o.matrix_world.inverted().to_3x3()
 for v in o.data.vertices:
  p=o.matrix_world@v.co;direction=Vector((p.x,p.y+.006*scale,0)).normalized();delta=inverse@(direction*.003*scale);v.co+=delta
  if o.data.shape_keys:
   for key in o.data.shape_keys.key_blocks:key.data[v.index].co+=delta
r['Wear_Protector']=True;r['Wear_Helmet']=True
for design in [0,1]:
 r['ProtectorDesign']=design;a.build.refresh(r)
 a.render(s,r,scale,out,'Design_'+str(design),(.2,-4,1.3),(0,0,1.15),.9,720,720)
(out/'objects.json').write_text(json.dumps(rows,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True)
