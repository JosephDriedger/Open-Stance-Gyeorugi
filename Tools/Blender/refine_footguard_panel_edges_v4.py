"""Staged panel-border smoothing, preserving topology, UVs and skin weights."""
import bpy,sys,json
from pathlib import Path
from collections import defaultdict
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardPanelReviewV4';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend'))
rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
 mesh=o.data;uv=mesh.uv_layers['UVMap'];edge_roles=defaultdict(set)
 for p in mesh.polygons:
  role=uv.data[p.loop_start].uv.x>.75
  for edge in p.edge_keys:edge_roles[tuple(sorted(edge))].add(role)
 adjacent=defaultdict(set)
 for (a,b),roles in edge_roles.items():
  if len(roles)>1:adjacent[a].add(b);adjacent[b].add(a)
 original=[v.co.copy() for v in mesh.vertices];coords=[p.copy() for p in original]
 tree=BVHTree.FromPolygons(original,[tuple(p.vertices) for p in mesh.polygons])
 for step in range(8):
  updated={}
  for i,neighbors in adjacent.items():
   if len(neighbors)!=2:continue
   a,b=neighbors;target=coords[i].lerp((coords[a]+coords[b])*.5,.4)
   point,normal,index,distance=tree.find_nearest(target)
   if point is not None:updated[i]=target
  for i,p in updated.items():coords[i]=p
 # Spread the border displacement into a narrow surrounding mesh band.
 links=defaultdict(set)
 for edge in mesh.edges:
  a,b=edge.vertices;links[a].add(b);links[b].add(a)
 band=set(adjacent);front=set(adjacent)
 for ring in range(4):
  front={j for i in front for j in links[i]}-band;band.update(front)
 movable=band-set(front)-set(adjacent)
 offsets={i:coords[i]-original[i] for i in band}
 for step in range(40):
  updates={}
  for i in movable:
   neighbors=links[i]
   value=sum((offsets.get(j,original[j]*0) for j in neighbors),original[i]*0)/len(neighbors)
   updates[i]=offsets[i].lerp(value,.6)
  offsets.update(updates)
 for i in movable:coords[i]=original[i]+offsets[i]
 # Backtrack local movements that fold or collapse incident triangles.
 mesh.calc_loop_triangles()
 incident=defaultdict(list);triangles=[]
 for tri in mesh.loop_triangles:
  ids=tuple(tri.vertices);a,b,c=[original[j] for j in ids];normal=(b-a).cross(c-a)
  triangles.append((ids,normal))
  for j in ids:incident[j].append(len(triangles)-1)
 target_coords=coords;coords=[p.copy() for p in original];limited=0
 for i in sorted(band):
  delta=target_coords[i]-original[i];factor=1.0
  for attempt in range(18):
   coords[i]=original[i]+delta*factor;valid=True
   for ti in incident[i]:
    ids,before=triangles[ti]
    if before.length<1e-10:continue
    a,b,c=[coords[j] for j in ids];after=(b-a).cross(c-a)
    if after.dot(before)<.15*before.length_squared or after.length<.15*before.length:
     valid=False;break
   if valid:break
   factor*=.5
  if not valid:coords[i]=original[i]
  if factor<1:limited+=1
 maximum=0
 for i in band:
  delta=coords[i]-original[i];maximum=max(maximum,delta.length)
  if mesh.shape_keys:
   for key in mesh.shape_keys.key_blocks:key.data[i].co+=delta
  else:mesh.vertices[i].co+=delta
 if mesh.has_custom_normals:mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops))
 mesh.update();rows.append({'object':o.name,'border_vertices':len(adjacent),'max_displacement_m':maximum})
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
from mathutils import Vector
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale)
 target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'changes':rows},indent=2))



