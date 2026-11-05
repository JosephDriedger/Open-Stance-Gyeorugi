import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;smooth='--smooth' in sys.argv
OUT=ROOT/'Resources/Models/FinalRefinement'/('FootguardSmoothExportReview' if smooth else 'FootguardExportReview');rows=[]
def points(o,evaluated=False):
 if not evaluated:return [o.matrix_world@v.co for v in o.data.vertices]
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();result=[o.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();return result
def maximum_distance(a,b):
 tree=KDTree(len(a))
 for i,p in enumerate(a):tree.insert(p,i)
 tree.balance();return max(tree.find(p)[2] for p in b)
for style,label in enumerate(('Standard','Padded')):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement'/('FootguardLocalROMSmooth' if smooth else 'FootguardVariantReview')/'Candidate.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r['FootGuardsStyle']=style;review.build.refresh(r);name='FootGuards' if style==0 else 'FootGuards_PaddedInstep';native=bpy.data.objects[name];rest=points(native)
 before=set(s.objects);bpy.ops.import_scene.fbx(filepath=str(OUT/('Stocky_'+label+'_Guard.fbx')),use_anim=False)
 imported=[o for o in s.objects if o not in before];rig=next(o for o in imported if o.type=='ARMATURE');guard=next(o for o in imported if o.type=='MESH');rest_error=maximum_distance(rest,points(guard));assert rest_error<1e-5,rest_error
 missing=set(r.data.bones.keys())-set(rig.data.bones.keys());assert not missing,missing
 assert len(guard.data.uv_layers)==1
 bad_weights=[v.index for v in guard.data.vertices if abs(sum(g.weight for g in v.groups)-1)>.001 or len(v.groups)>4];assert not bad_weights
 images=[node.image for mat in guard.data.materials if mat and mat.use_nodes for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image];assert images and all(im.size[0]>0 for im in images)
 ordered=sorted(rig.pose.bones,key=lambda p:len(p.parent_recursive))
 pose_checks=[]
 for frame in sorted(set(range(1,145,6))|{26,35,54,72,144}):
  s.frame_set(frame);bpy.context.view_layer.update();expected=points(native,True)
  for p in ordered:
   if p.name in r.pose.bones:p.matrix=rig.matrix_world.inverted()@r.matrix_world@r.pose.bones[p.name].matrix
   bpy.context.view_layer.update()
  actual=points(guard,True)
  error=max(maximum_distance(expected,actual),maximum_distance(actual,expected))
  assert error<.0001,(label,frame,error)
  pose_checks.append({'frame':frame,'symmetric_max_error_m':error})
 posed_error=max(row['symmetric_max_error_m'] for row in pose_checks)
 s.frame_set(35);bpy.context.view_layer.update()
 for p in ordered:
  if p.name in r.pose.bones:p.matrix=rig.matrix_world.inverted()@r.matrix_world@r.pose.bones[p.name].matrix
  bpy.context.view_layer.update()
 for n in ('FootGuards','FootGuards_PaddedInstep'):bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label+'_Reimport_Kick',tuple(position),tuple(target),.42*scale,600,600)
 rows.append({'style':label,'rest_max_error_m':rest_error,'posed_max_error_m':posed_error,'sampled_pose_checks':pose_checks,'vertices':len(guard.data.vertices),'bones':len(rig.data.bones),'uv_layers':[x.name for x in guard.data.uv_layers],'textures':[{'name':im.name,'size':list(im.size),'path':im.filepath} for im in images],'normalized_four_influence_weights':True})
(OUT/'roundtrip.json').write_text(json.dumps({'passed':True,'production_installed':False,'checks':rows,'scope':'Blender FBX mesh/UV/texture/weight roundtrip; compared at rest and identical global bone pose. Not action retargeting, MotionBuilder or Unreal acceptance.'},indent=2))
