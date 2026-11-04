import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardRemeshRefined';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardShellRebuildV4/Candidate.blend'))
o=bpy.data.objects['FootGuards'];o.data.calc_loop_triangles();points=[v.co.copy() for v in o.data.vertices];tris=[tuple(t.vertices) for t in o.data.loop_triangles];weights=[{o.vertex_groups[g.group].name:g.weight for g in v.groups} for v in o.data.vertices];tree=BVHTree.FromPolygons(points,tris,all_triangles=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardRemeshReview/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;rows=[]
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name]
 for m in list(o.modifiers):o.modifiers.remove(m)
 mod=o.modifiers.new('Reduce_voxel_surface','DECIMATE');mod.ratio=.06;mod.use_collapse_triangulate=True
 with bpy.context.temp_override(object=o,active_object=o):bpy.ops.object.modifier_apply(modifier=mod.name)
 o.vertex_groups.clear();groups={}
 for v in o.data.vertices:
  q,n,ti,d=tree.find_nearest(v.co);ids=tris[ti];a,b,c=[points[i] for i in ids];u=b-a;w=c-a;t=q-a;den=u.dot(u)*w.dot(w)-u.dot(w)**2
  if abs(den)<1e-18:factors=[1,0,0]
  else:
   y=(w.dot(w)*t.dot(u)-u.dot(w)*t.dot(w))/den;z=(u.dot(u)*t.dot(w)-u.dot(w)*t.dot(u))/den;factors=[max(0,1-y-z),max(0,y),max(0,z)]
  mixed={}
  for i,factor in zip(ids,factors):
   for bone,weight in weights[i].items():mixed[bone]=mixed.get(bone,0)+factor*weight
  mixed=sorted(mixed.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in mixed)
  for bone,weight in mixed:
   if bone not in groups:groups[bone]=o.vertex_groups.new(name=bone)
   groups[bone].add([v.index],weight/total,'REPLACE')
 for p in o.data.polygons:p.use_smooth=True
 arm=o.modifiers.new('Deform','ARMATURE');arm.object=r
 rows.append({'object':name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons)})
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'weight_transfer':'barycentric interpolation, normalized four influences','changes':rows},indent=2))
