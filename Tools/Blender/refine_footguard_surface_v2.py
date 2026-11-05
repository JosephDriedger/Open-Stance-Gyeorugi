"""Constrained instep smoothing, isolated from the production library."""
import bpy,sys,json
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardSurfaceReviewV2';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardPanelRebuildV2/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
axes=[]
for side in 'lr':
 foot=r.matrix_world@r.data.bones['foot_'+side].head_local;ball=r.matrix_world@r.data.bones['ball_'+side].head_local
 forward=ball-foot;forward.z=0;forward.normalize();axes.append((foot,forward,(ball-foot).dot(forward)))
from mathutils.bvhtree import BVHTree
body=bpy.data.objects['Body'];bodytree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons])
rows=[]
for o in s.objects:
 if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
 m=o.data;old=[v.co.copy() for v in m.vertices];coords=[p.copy() for p in old];links=defaultdict(set);mobility={}
 for edge in m.edges:
  a,b=edge.vertices;links[a].add(b);links[b].add(a)
 for v in m.vertices:
  p=o.matrix_world@v.co;foot,forward,length=min(axes,key=lambda a:abs(p.x-a[0].x));along=(p-foot).dot(forward)
  # Protect sole, toe opening and upper cuff; blend out over 15 mm.
  margin=min(p.z-.035*scale,foot.z+.055*scale-p.z,along+.025*scale,length-.025*scale-along)
  mobility[v.index]=max(0,min(1,margin/(.015*scale)))
 for iteration in range(12):
  new=[p.copy() for p in coords]
  for i,neighbors in links.items():
   if not mobility[i]:continue
   average=sum((coords[j] for j in neighbors),Vector())/len(neighbors)
   delta=(average-coords[i])*.35*mobility[i]
   candidate=coords[i]+delta;total=candidate-old[i]
   if total.length>.004*scale:candidate=old[i]+total.normalized()*.004*scale
   new[i]=candidate
  coords=new
 for i in range(len(coords)):
  if not mobility[i]:continue
  oldworld=o.matrix_world@old[i];hit,n,_,_=bodytree.find_nearest(oldworld);baseline=(oldworld-hit).dot(n)
  world=o.matrix_world@coords[i];hit,n,_,_=bodytree.find_nearest(world);clearance=(world-hit).dot(n)
  if clearance<baseline:coords[i]=o.matrix_world.inverted()@(world+n*(baseline-clearance))
 m.calc_loop_triangles();triangles=[]
 for tri in m.loop_triangles:
  ids=tuple(tri.vertices);a,b,c=[old[i] for i in ids];triangles.append((ids,(b-a).cross(c-a)))
 for iteration in range(100):
  bad=set()
  for ids,before in triangles:
   if before.length<1e-10:continue
   a,b,c=[coords[j] for j in ids];after=(b-a).cross(c-a)
   if after.dot(before)<.2*before.length_squared or after.length<.2*before.length:bad.update(ids)
  if not bad:break
  for i in bad:coords[i]=old[i].lerp(coords[i],.7)
 assert not bad,'Unresolved triangle constraints'
 maximum=0;count=0
 for i in range(len(coords)):
  delta=coords[i]-old[i];maximum=max(maximum,delta.length);count+=delta.length>1e-7
  if m.shape_keys:
   for key in m.shape_keys.key_blocks:key.data[i].co+=delta
  else:m.vertices[i].co+=delta
 if m.has_custom_normals:m.normals_split_custom_set([(0,0,0)]*len(m.loops))
 m.update();rows.append({'object':o.name,'moved_vertices':count,'maximum_displacement_m':maximum})
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'changes':rows},indent=2))

