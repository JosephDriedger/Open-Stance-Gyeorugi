"""Bounded rest-space calf fitting against sampled animated body surfaces."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/KneeWeightReview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/CalfKneeCorrectiveV2/Candidate.blend'))
pants=bpy.data.objects['Pants'];rig=bpy.data.objects['RIG_Body_Stocky']
k=pants.data.shape_keys.key_blocks.get('KneeFlex_Calf_Clearance_l')
if k:pants.shape_key_remove(k)
changed=0
for v in pants.data.vertices:
 z=(pants.matrix_world@v.co).z
 blend=min(1,max(0,(z-.36)/.04),max(0,(.58-z)/.04))
 if not blend:continue
 old={pants.vertex_groups[g.group].name:g.weight for g in v.groups if pants.vertex_groups[g.group].name in rig.data.bones};new={}
 for name,w in old.items():
  dst=('calf_'+name[-1] if name.startswith('calf_') else 'thigh_'+name[-1] if name.startswith('thigh_') else name)
  new[name]=new.get(name,0)+w*(1-blend);new[dst]=new.get(dst,0)+w*blend
 new=dict(sorted(new.items(),key=lambda p:-p[1])[:4]);total=sum(new.values())
 for name in old:pants.vertex_groups[name].remove([v.index])
 for name,w in new.items():
  if w>1e-7:(pants.vertex_groups.get(name) or pants.vertex_groups.new(name=name)).add([v.index],w/total,'REPLACE')
 changed+=1
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];pants=bpy.data.objects['Pants'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body=bpy.data.objects['Body'];probe=body.copy();probe.data=body.data.copy();s.collection.objects.link(probe);probe.hide_render=True
for m in list(probe.modifiers):
 if m.type=='MASK':probe.modifiers.remove(m)
disabled=[]
for m in pants.modifiers:
 if m.type!='ARMATURE':disabled.append((m,m.show_viewport));m.show_viewport=False
rest=[v.co.copy() for v in pants.data.vertices];total=[Vector((0,0,0)) for _ in rest]
indices=[i for i,p in enumerate(rest) if .16*scale<(pants.matrix_world@p).z<.50*scale]
weights={i:[(pants.vertex_groups[g.group].name,g.weight) for g in pants.data.vertices[i].groups if pants.vertex_groups[g.group].name in r.data.bones] for i in indices}
side_for={i:max('lr',key=lambda side:sum(w for n,w in weights[i] if n.endswith('_'+side))) for i in indices}
body_weights=[{probe.vertex_groups[g.group].name:g.weight for g in v.groups} for v in probe.data.vertices]
def geometry(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles();pts=[o.matrix_world@v.co for v in m.vertices];tris=[tuple(t.vertices) for t in m.loop_triangles];ev.to_mesh_clear();return pts,tris
def snapshot(frame):
 s.frame_set(frame);bpy.context.view_layer.update();bp,bt=geometry(probe);pp,_=geometry(pants)
 trees={side:BVHTree.FromPolygons(bp,[t for t in bt if sum(sum(w for n,w in body_weights[i].items() if n.endswith('_'+side) and n.startswith(('calf_','foot_','ball_'))) for i in t)/3>.5],all_triangles=True) for side in 'lr'}
 return pp,trees
rows=[]
for frame in range(1,145):
 pp,tree=snapshot(frame);ds=[]
 for i in indices:
  hit,n,_,_=tree[side_for[i]].find_nearest(pp[i]);ds.append((pp[i]-hit).dot(n))
 rows.append({'frame':frame,'minimum_m':min(ds),'inside_1mm':sum(d<-.001 for d in ds)})
(OUT/'all_frames.json').write_text(json.dumps({'passed':all(x['inside_1mm']==0 for x in rows),'scope':'Lower-leg-region vertex checks against matching lower-leg surface; not whole-body or cloth collision acceptance','checks':rows},indent=2))

for m,enabled in disabled:m.show_viewport=enabled
bpy.data.objects.remove(probe,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
for frame in (17,26,35):
 s.frame_set(frame);review.render(s,r,scale,OUT,'Full_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
