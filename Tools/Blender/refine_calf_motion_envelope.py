"""Bounded rest-space calf fitting against sampled animated body surfaces."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/CalfMotionEnvelopeV3';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardSmoothKickReview/Animation_Test.blend'))
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
frames=(1,12,26,35,54,72,96,120,144)
before=[]
for frame in frames:
 pp,tree=snapshot(frame);ds=[]
 for i in indices:
  hit,n,_,_=tree[side_for[i]].find_nearest(pp[i]);ds.append((pp[i]-hit).dot(n))
 before.append({'frame':frame,'minimum_m':min(ds),'inside_1mm':sum(d<-.001 for d in ds)})
for iteration in range(3):
 for frame in frames:
  pp,tree=snapshot(frame);transforms={n:(r.matrix_world@r.pose.bones[n].matrix@r.data.bones[n].matrix_local.inverted()@r.matrix_world.inverted()@pants.matrix_world).to_3x3() for row in weights.values() for n,w in row}
  for i in indices:
   hit,n,_,_=tree[side_for[i]].find_nearest(pp[i]);distance=(pp[i]-hit).dot(n)
   if distance>=.004*scale:continue
   blended=Matrix(((0,0,0),(0,0,0),(0,0,0)))
   for name,w in weights[i]:blended+=transforms[name]*w
   if abs(blended.determinant())<1e-8:continue
   delta=blended.inverted()@(n*min(.004*scale,.004*scale-distance))
   desired=total[i]+delta
   if desired.length>.015*scale:desired=desired.normalized()*.015*scale
   delta=desired-total[i];total[i]=desired
   pants.data.vertices[i].co+=delta
   if pants.data.shape_keys:
    for key in pants.data.shape_keys.key_blocks:key.data[i].co+=delta
  pants.data.update()
 print('ENVELOPE_PASS',iteration+1,flush=True)
after=[]
for frame in frames:
 pp,tree=snapshot(frame);ds=[]
 for i in indices:
  hit,n,_,_=tree[side_for[i]].find_nearest(pp[i]);ds.append((pp[i]-hit).dot(n))
 after.append({'frame':frame,'minimum_m':min(ds),'inside_1mm':sum(d<-.001 for d in ds)})
for m,enabled in disabled:m.show_viewport=enabled
bpy.data.objects.remove(probe,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for frame in (35,72):
 s.frame_set(frame);review.render(s,r,scale,OUT,f'Full_{frame}',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'before':before,'after':after,'changed_vertices':sum(d.length>1e-7 for d in total),'max_rest_offset_m':max(d.length for d in total),'scope':'Bounded rest calf offsets applied equally to all shape keys; unchanged weights/topology. Sampled vertex clearance only, not full surface collision certification.'},indent=2))
