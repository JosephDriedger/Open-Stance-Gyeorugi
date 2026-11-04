"""Bounded rest-space calf fitting against sampled animated body surfaces."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/CalfCuffFit';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/CalfCuffFit/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];pants=bpy.data.objects['Pants'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body=bpy.data.objects['Body'];probe=body.copy();probe.data=body.data.copy();s.collection.objects.link(probe);probe.hide_render=True
for m in list(probe.modifiers):
 if m.type=='MASK':probe.modifiers.remove(m)
disabled=[]
for m in pants.modifiers:
 if m.type!='ARMATURE':disabled.append((m,m.show_viewport));m.show_viewport=False
rest=[v.co.copy() for v in pants.data.vertices];total=[Vector((0,0,0)) for _ in rest]
indices=[i for i,p in enumerate(rest) if .16*scale<(pants.matrix_world@p).z<.43*scale]
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
