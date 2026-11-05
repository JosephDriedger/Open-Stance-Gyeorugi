import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardCollisionAnimationReview';OUT.mkdir(exist_ok=True)
source=ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Stocky_Wrap.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));action_name=bpy.data.objects['RIG_Body_Stocky'].animation_data.action.name
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardSurfaceCollision/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.actions=[action_name]
r.animation_data_create();r.animation_data.action=dst.actions[0]
if dst.actions[0].slots:r.animation_data.action_slot=dst.actions[0].slots[0]
for track in r.animation_data.nla_tracks:track.mute=True
r['BlenderCloth']=False;r['Wear_FootGuards']=True;review.build.refresh(r)
body=bpy.data.objects['Body'];probe=body.copy();probe.data=body.data.copy();probe.name='AUDIT_FullBody';s.collection.objects.link(probe);probe.hide_render=True
for m in list(probe.modifiers):
 if m.type=='MASK':probe.modifiers.remove(m)
guard=bpy.data.objects['FootGuards'];rows=[]
def geometry(o,dg):
 ev=o.evaluated_get(dg);mesh=ev.to_mesh();mesh.calc_loop_triangles();points=[o.matrix_world@v.co for v in mesh.vertices];tris=[tuple(t.vertices) for t in mesh.loop_triangles];ev.to_mesh_clear();return points,tris
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for frame in range(1,145):
 s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get();bp,bt=geometry(probe,dg);gp,gt=geometry(guard,dg);tree=BVHTree.FromPolygons(bp,bt,all_triangles=True);distances=[]
 for p in gp:
  hit,n,_,_=tree.find_nearest(p);distances.append((p-hit).dot(n))
 row={'frame':frame,'minimum_vertex_clearance_m':min(distances),'vertices_inside_over_1mm':sum(d<-.001 for d in distances)}
 if frame%6==0 or frame in (1,26,35):
  own=BVHTree.FromPolygons(gp,gt,all_triangles=True);row['self_overlap_pairs']=sum(a<b and not set(gt[a])&set(gt[b]) for a,b in own.overlap(own))
 rows.append(row)
 if frame in (26,35,54,72):
  target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
  review.render(s,r,1,OUT,'Frame_'+str(frame),tuple(position),tuple(target),.42*scale,600,600)
 if frame%24==0:print('GUARD_FRAME',frame,flush=True)
bpy.data.objects.remove(probe,do_unlink=True);s.frame_start=1;s.frame_end=144;s.frame_set(1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Animation_Test.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'action':action_name,'frames':144,'cloth_enabled':False,'worst_frame':min(rows,key=lambda x:x['minimum_vertex_clearance_m']),'checks':rows,'scope':'Standard guard only. Vertex clearance every frame; self-overlap sampled every sixth frame plus 1/26/35. Not continuous swept collision validation.'},indent=2))

