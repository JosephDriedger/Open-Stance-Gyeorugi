"""Compare local cloth changes against the delivered Medium study."""
import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import extend_garment_repairs as base
mode=sys.argv[-1]
assert mode in ['WideAnchor','DampedBelt','FlexibleHem','UnifiedBelt','MassScaledBelt','ConvexContact','ThinContact','ThinUnified','ThinSharedProxy','SharedAppliedScale','SharedRootExclusion','SharedGarmentContact']
out=a.ROOT/'Resources/Models/FinalRefinement'/('ClothRefinement_'+mode);out.mkdir(exist_ok=True)
source=a.ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Medium_Wrap.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium']
original=base.signature(r);actions=base.actions();s.frame_set(1)
r['BlenderCloth']=False;r.update_tag();bpy.context.view_layer.update()
names=['Belt_Tail_Left','Belt_Tail_Right']
if mode in ['ThinContact','ThinUnified','ThinSharedProxy','SharedAppliedScale','SharedRootExclusion','SharedGarmentContact']:
 from mathutils import Vector
 proxy=bpy.data.objects['SIM_Belt_Fitted_Contact'];source=bpy.data.objects['Pants']
 inverse=proxy.matrix_world.inverted().to_3x3();normal_matrix=source.matrix_world.to_3x3().inverted().transposed()
 for v,sv in zip(proxy.data.vertices,source.data.vertices):
  z=(source.matrix_world@sv.co).z;delta=inverse@((normal_matrix@sv.normal).normalized()*(.002+.003*max(0,min(1,(z-.65)/.15))))
  v.co=sv.co+delta
  if proxy.data.shape_keys:
   for key in proxy.data.shape_keys.key_blocks:key.data[v.index].co=source.data.shape_keys.key_blocks[key.name].data[v.index].co+delta
if mode=='ConvexContact':
 proxy=bpy.data.objects['SIM_Belt_Fitted_Contact'];group=bpy.data.node_groups.new('Belt convex contact','GeometryNodeTree')
 group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
 inp=group.nodes.new('NodeGroupInput');hull=group.nodes.new('GeometryNodeConvexHull');output=group.nodes.new('NodeGroupOutput')
 group.links.new(inp.outputs['Geometry'],hull.inputs['Geometry']);group.links.new(hull.outputs['Convex Hull'],output.inputs['Geometry'])
 mod=proxy.modifiers.new('Continuous belt contact','NODES');mod.node_group=group
 bpy.context.view_layer.objects.active=proxy;bpy.ops.object.modifier_move_to_index(modifier=mod.name,index=1)
if mode in ['UnifiedBelt','ThinUnified']:
 bpy.ops.object.select_all(action='DESELECT')
 for name in names:bpy.data.objects[name].hide_set(False);bpy.data.objects[name].select_set(True)
 bpy.context.view_layer.objects.active=bpy.data.objects[names[0]]
 bpy.ops.object.join();o=bpy.context.object;o.name='Belt_Tails_Simulation';names=[o.name]
 cloth=next(m for m in o.modifiers if m.type=='CLOTH')
 cloth.collision_settings.use_self_collision=True;cloth.collision_settings.self_distance_min=.0015;cloth.collision_settings.self_friction=0;cloth.collision_settings.collision_quality=16
 cloth.settings.quality=35
for name in names:
 o=bpy.data.objects[name];cloth=next(m for m in o.modifiers if m.type=='CLOTH')
 if mode=='WideAnchor':
  pin=o.vertex_groups['LiveCloth_Pin'];top=max((o.matrix_world@v.co).z for v in o.data.vertices)
  for v in o.data.vertices:pin.add([v.index],max(0,min(1,((o.matrix_world@v.co).z-top+.065)/.025)),'REPLACE')
 if mode=='DampedBelt':
  cloth.settings.bending_stiffness=12;cloth.settings.bending_damping=25;cloth.settings.air_damping=12
 if mode=='MassScaledBelt':
  cs=cloth.settings;cs.mass=.06/len(o.data.vertices);cs.bending_stiffness=.2;cs.bending_damping=.5;cs.air_damping=1;cs.quality=50
  cs.tension_damping=5;cs.compression_damping=5;cs.shear_damping=5
if mode=='FlexibleHem':
 for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  o=bpy.data.objects[name];pin=o.vertex_groups['LiveCloth_Pin'];points=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in points);bottom=min(p.z for p in points)
  for v,p in zip(o.data.vertices,points):
   t=(p.z-bottom)/max(.001,top-bottom)
   pin.add([v.index],1 if t>.88 else .82+.14*t,'REPLACE')
  cloth=next(m for m in o.modifiers if m.type=='CLOTH');cloth.settings.quality=20;cloth.settings.bending_stiffness=3
if mode in ['ThinSharedProxy','SharedAppliedScale','SharedRootExclusion','SharedGarmentContact']:
 from shared_belt_simulation import configure as shared
 shared(s,r)
if mode in ['SharedAppliedScale','SharedRootExclusion','SharedGarmentContact']:
 for name in ['SIM_Shared_Belt_Tails','SIM_Belt_Fitted_Contact']:
  o=bpy.data.objects[name];before=[o.matrix_world@v.co for v in o.data.vertices]
  bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  assert max((p-o.matrix_world@v.co).length for p,v in zip(before,o.data.vertices))<1e-5
if mode in ['SharedRootExclusion','SharedGarmentContact']:
 o=bpy.data.objects['SIM_Shared_Belt_Tails'];pin=o.vertex_groups['LiveCloth_Pin'];exclude=o.vertex_groups.new(name='Fixed_Knot_Contact_Exclusion')
 indices=[v.index for v in o.data.vertices if pin.weight(v.index)>.3];exclude.add(indices,1,'REPLACE')
 cc=next(m.collision_settings for m in o.modifiers if m.type=='CLOTH');cc.vertex_group_self_collisions=exclude.name;cc.vertex_group_object_collisions=exclude.name
if mode=='SharedGarmentContact':
 from visible_garment_contact import configure as contact
 contact(s,next(m for m in bpy.data.objects['SIM_Shared_Belt_Tails'].modifiers if m.type=='CLOTH'))
r['BlenderCloth']=True;r.update_tag();bpy.context.view_layer.update();s.cycles.samples=12
for frame in range(1,145):
 s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
 for name in names+['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();assert all(math.isfinite(x) and abs(x)<5 for v in me.vertices for x in o.matrix_world@v.co);ev.to_mesh_clear()
 if frame in [1,26,35,72,144]:
  a.render(s,r,1,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,640,720)
  a.render(s,r,1,out,'Side_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,640,720)
s.frame_set(1);assert base.signature(r)==original and base.actions()==actions
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True)
(out/'validation.json').write_text(json.dumps({'candidate':mode,'finite':True,'frames':144,'rig_actions_preserved':True,'production_installed':False},indent=2))
