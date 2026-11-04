import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCalfWeights';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery/SkinOverlap_16cm.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];body=bpy.data.objects['Body'];pants=bpy.data.objects['Pants'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in body.data.loop_triangles];points=[body.matrix_world@v.co for v in body.data.vertices];tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
bones=set(r.data.bones.keys())
def weights(o,v):return {o.vertex_groups[g.group].name:g.weight for g in v.groups if o.vertex_groups[g.group].name in bones}
body_weights=[weights(body,v) for v in body.data.vertices];changed=0;maximum=0
for vertex in pants.data.vertices:
 p=pants.matrix_world@vertex.co;blend=max(0,min(1,(.40*scale-p.z)/(.10*scale)));blend=blend*blend*(3-2*blend)
 if not blend:continue
 q,n,index,distance=tree.find_nearest(p);ids=triangles[index];a,b,c=[points[i] for i in ids];u=b-a;v=c-a;w=q-a;den=u.dot(u)*v.dot(v)-u.dot(v)**2
 if abs(den)<1e-16:continue
 y=(v.dot(v)*w.dot(u)-u.dot(v)*w.dot(v))/den;z=(u.dot(u)*w.dot(v)-u.dot(v)*w.dot(u))/den
 factors=[max(0,1-y-z),max(0,y),max(0,z)];total=sum(factors);factors=[x/total for x in factors];new={}
 for i,factor in zip(ids,factors):
  for bone,weight in body_weights[i].items():new[bone]=new.get(bone,0)+factor*weight
 old=weights(pants,vertex);mixed={bone:old.get(bone,0)*(1-blend)+new.get(bone,0)*blend for bone in set(old)|set(new)};mixed=dict(sorted(mixed.items(),key=lambda x:x[1],reverse=True)[:4]);total=sum(mixed.values());mixed={k:v/total for k,v in mixed.items() if v>1e-7}
 maximum=max(maximum,sum(abs(old.get(k,0)-mixed.get(k,0)) for k in set(old)|set(mixed)))
 for bone in old:pants.vertex_groups[bone].remove([vertex.index])
 for bone,weight in mixed.items():(pants.vertex_groups.get(bone) or pants.vertex_groups.new(name=bone)).add([vertex.index],weight,'REPLACE')
 changed+=1
review.audit.pose(r,'Front_Kick_L',scale);s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.065*scale));position=target+Vector((1,-.4,.2))*scale
review.render(s,r,1,OUT,'Front_Kick',tuple(position),tuple(target),.4*scale,600,600)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'changes.json').write_text(json.dumps({'vertices_reweighted':changed,'maximum_weight_L1_difference':maximum,'production_installed':False},indent=2))
