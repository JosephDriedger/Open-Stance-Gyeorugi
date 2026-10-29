import bpy,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
ROOT=a.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/UniformGeometryDelivery'
kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
rows=[]
for kind in ([] if '--review-only' in sys.argv else kinds):
 rel=f'Resources/Models/Animation/MotionBuilder_BeltChain/{kind}/OpenStance_{kind}_Sparring.fbx'
 path=OUT/'Files'/rel
 deadline=time.time()+1800
 while not path.exists():
  assert time.time()<deadline,rel
  time.sleep(2)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path))
 checks=[]
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  name=o.name.split('.')[0]
  if name not in ('Body','Jacket','Pants'):continue
  o.data.calc_loop_triangles();zero=0;zero_uv=0
  for tri in o.data.loop_triangles:
   p,q,r=[o.matrix_world@o.data.vertices[i].co for i in tri.vertices]
   if (q-p).cross(r-p).length<1e-12:zero+=1
   if name!='Body':
    p,q,r=[o.data.uv_layers.active.data[i].uv.copy() for i in tri.loops];u,v=q-p,r-p
    if abs(u.x*v.y-u.y*v.x)<1e-12:zero_uv+=1
  assert zero==0,(rel,name,'zero geometry',zero)
  if name!='Body':assert zero_uv==0,(rel,name,'zero UV',zero_uv)
  checks.append({'mesh':name,'zero_area_triangles':zero,'zero_uv_triangles':zero_uv})
 assert len(checks)==3,(rel,checks)
 rows.append({'file':rel,'checks':checks});print('UNIFORM_GEOMETRY_REIMPORT_PASS',kind,flush=True)
if rows:(OUT/'reimport_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
review=OUT/'Review';review.mkdir(exist_ok=True)
for label,base in [('Before',ROOT),('After',OUT/'Files')]:
 rel='Resources/Models/CharacterSuite/Medium/Gameplay_High_Dobok.fbx';path=base/rel
 while not path.exists():time.sleep(2)
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'))
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
 for o in list(s.objects):
  if o.type in ('MESH','ARMATURE') and o.name not in ('Ground','Mat','Floor'):bpy.data.objects.remove(o,do_unlink=True)
 bpy.ops.import_scene.fbx(filepath=str(path));r=next(o for o in s.objects if o.type=='ARMATURE')
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 a.render(s,r,scale,review,label+'_Full',(.9,-4,1.65),(0,0,.96),2.2,650,780)
 a.render(s,r,scale,review,label+'_Fabric',(.35,-2,1.3),(0,0,1.12),.6,700,700)
print('UNIFORM_REVIEW_COMPLETE',flush=True)
