"""Sample actual triangle crossings, not only nearest-surface distances."""
import bpy,sys,json,time
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/BodyPhysicsThin';rows=[];all_frames=False;gear=False
def mesh(name,deps):
 o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
 pts=[o.matrix_world@v.co for v in me.vertices];faces=[tuple(t.vertices) for t in me.loop_triangles];ev.to_mesh_clear()
 return pts,faces,BVHTree.FromPolygons(pts,faces,all_triangles=True)
def crossing(a,b):
 for source,target in [(a,b),(b,a)]:
  for i in range(3):
   p=source[i];d=source[(i+1)%3]-p
   if d.length_squared<1e-16:continue
   q=intersect_ray_tri(*target,d,p,True)
   if q is not None:
    t=(q-p).dot(d)/d.length_squared
    if 1e-5<t<1-1e-5:return True
 return False
cases=[('old',ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Medium_Wrap.blend'),('thin',OUT/'Medium/SecondaryCloth_Medium_Wrap.blend')]
if '--' in sys.argv:
 args=sys.argv[sys.argv.index('--')+1:]
 all_frames='all' in args
 gear='gear' in args
 if args[0]=='folder':
  OUT=Path(args[1]).resolve();label=OUT.name
 else:
  label=args[0];OUT=OUT.parent/('ClothRefinement_'+label)
 cases=[(label,OUT/'Candidate.blend')]
for label,path in cases:
 deadline=time.monotonic()+1200
 if label!='old':
  while not (path.parent/'validation.json').exists():
   assert time.monotonic()<deadline
   time.sleep(2)
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
 end_frame=s.frame_end if all_frames else 144
 for frame in range(1,end_frame+1):
  s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
  # Force every sequential cloth evaluation, including frames not sampled.
  for name in ['Belt_Tail_Left','Belt_Tail_Right','Pants','Jacket_Front_Left','Jacket_Front_Right']:
   ev=bpy.data.objects[name].evaluated_get(deps);ev.to_mesh();ev.to_mesh_clear()
  if not all_frames and frame not in [1,26,35,72,144]:continue
  pants='SIM_Render_Pants' if 'SIM_Render_Pants' in bpy.data.objects else 'Pants'
  names=['Belt_Tail_Left','Belt_Tail_Right',pants,'Jacket_Front_Left','Jacket_Front_Right']
  if gear:names.extend(o.name for o in s.objects if o.type=='MESH' and not o.hide_render and o.name.endswith(('__Padded_Torso_Shell','__Bound_Hem')))
  data={n:mesh(n,deps) for n in names}
  for belt in names[:2]:
   for garment in names[2:]+(['Belt_Tail_Right'] if belt=='Belt_Tail_Left' else []):
    av,af,at=data[belt];bv,bf,bt=data[garment];pairs=at.overlap(bt);count=0;hit_points=[]
    for i,j in pairs:
     if crossing([av[k] for k in af[i]],[bv[k] for k in bf[j]]):
      count+=1;hit_points.extend(av[k] for k in af[i])
    rows.append({'version':label,'frame':frame,'belt':belt,'garment':garment,'crossing_triangle_pairs':count,
                 'crossing_belt_triangle_bounds':[[min(p[i] for p in hit_points),max(p[i] for p in hit_points)] for i in range(3)] if hit_points else None})
  if not all_frames or frame%24==0:print('INTERSECTIONS',label,frame,flush=True)
 filename='intersection_review_all_frames.json' if all_frames else 'intersection_review.json'
 if gear:filename=filename.replace('.json','_with_gear.json')
 scope=f'Every integer frame 1–{end_frame}; no coplanar or between-frame collision guarantee' if all_frames else 'Sampled surface crossings; no coplanar or continuous-time collision guarantee'
 (OUT/filename).write_text(json.dumps({'scope':scope,'tested_objects':names,'rows':rows},indent=2))
