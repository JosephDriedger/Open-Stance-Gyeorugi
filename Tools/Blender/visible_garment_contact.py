"""Unit-scale collision proxies read the actual evaluated clothing surfaces."""
import bpy

def configure(scene,cloth,names=None):
 collection=bpy.data.collections.new('SIM_Visible_Garment_Contact');scene.collection.children.link(collection)
 for name in (names or ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']):
  source=bpy.data.objects[name];proxy=bpy.data.objects.new('SIM_Contact_'+name,bpy.data.meshes.new('Contact geometry'));collection.objects.link(proxy);proxy['SimulationOnly']=True
  group=bpy.data.node_groups.new('Evaluated contact '+name,'GeometryNodeTree');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
  info=group.nodes.new('GeometryNodeObjectInfo');info.inputs['Object'].default_value=source;info.transform_space='RELATIVE';output=group.nodes.new('NodeGroupOutput');group.links.new(info.outputs['Geometry'],output.inputs['Geometry'])
  mod=proxy.modifiers.new('Evaluated clothing','NODES');mod.node_group=group
  proxy.modifiers.new('Garment contact','COLLISION');proxy.collision.thickness_outer=.001;proxy.collision.thickness_inner=.0005;proxy.collision.cloth_friction=0
  proxy.display_type='WIRE'
  for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
  bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();bounds=[]
  for o in [source,proxy]:
   ev=o.evaluated_get(deps);me=ev.to_mesh();points=[o.matrix_world@v.co for v in me.vertices];assert points
   bounds.append([func(p[i] for p in points) for func in [min,max] for i in range(3)]);ev.to_mesh_clear()
  assert max(abs(a-b) for a,b in zip(*bounds))<1e-5,(name,bounds)
 cloth.collision_settings.collection=collection
 return collection.name
