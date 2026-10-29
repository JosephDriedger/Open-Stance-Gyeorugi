"""One cloth solver for mutual tail contact; retain two editable/exportable parts."""
import bpy
from mathutils import Vector

def configure(scene,rig):
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 originals=[bpy.data.objects[n] for n in ['Belt_Tail_Left','Belt_Tail_Right']];copies=[]
 for side,o in enumerate(originals):
  mean=sum((o.matrix_world@v.co).x for v in o.data.vertices)/len(o.data.vertices)
  delta=o.matrix_world.inverted().to_3x3()@Vector(((.003 if mean>0 else -.003)*scale,0,0))
  proxy=o.copy();proxy.data=o.data.copy();scene.collection.objects.link(proxy);proxy.shape_key_clear()
  # Clearance belongs to the simulation surface, not the editable/export mesh.
  # Moving the original also moved every shape key and changed cloth-off exports.
  for v in proxy.data.vertices:v.co+=delta
  for m in list(proxy.modifiers):
   if m.type not in ['ARMATURE','CLOTH']:proxy.modifiers.remove(m)
  # Remove wardrobe visibility drivers on the simulation-only copy.
  for prop in ['hide_render','hide_viewport']:proxy.driver_remove(prop)
  proxy.hide_set(False);proxy.hide_viewport=False;proxy.hide_render=False
  attr=proxy.data.attributes.new('BeltSide','INT','POINT')
  for value in attr.data:value.value=side
  copies.append(proxy)
 bpy.ops.object.select_all(action='DESELECT')
 for o in copies:o.select_set(True)
 bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();proxy=bpy.context.object;proxy.name='SIM_Shared_Belt_Tails';proxy['SimulationOnly']=True;proxy.display_type='WIRE'
 for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
 assert set(x.value for x in proxy.data.attributes['BeltSide'].data)=={0,1}
 cloth=next(m for m in proxy.modifiers if m.type=='CLOTH');cloth.settings.quality=40
 cloth.collision_settings.use_self_collision=True;cloth.collision_settings.self_distance_min=.0025*scale;cloth.collision_settings.self_friction=0;cloth.collision_settings.collision_quality=16
 for side,o in enumerate(originals):
  for m in list(o.modifiers):
   if m.type=='CLOTH':
    # Removing its modifier also requires removing the corresponding drivers.
    for prop in ['show_viewport','show_render']:m.driver_remove(prop)
    o.modifiers.remove(m)
  group=bpy.data.node_groups.new('Shared cloth output '+str(side),'GeometryNodeTree')
  group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
  info=group.nodes.new('GeometryNodeObjectInfo');info.inputs['Object'].default_value=proxy;info.transform_space='RELATIVE'
  attr=group.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='INT';attr.inputs['Name'].default_value='BeltSide'
  compare=group.nodes.new('FunctionNodeCompare');compare.data_type='INT';compare.operation='NOT_EQUAL'
  group.links.new(attr.outputs['Attribute'],next(x for x in compare.inputs if x.name=='A' and x.type=='INT'))
  next(x for x in compare.inputs if x.name=='B' and x.type=='INT').default_value=side
  delete=group.nodes.new('GeometryNodeDeleteGeometry');delete.domain='POINT';output=group.nodes.new('NodeGroupOutput')
  group.links.new(info.outputs['Geometry'],delete.inputs['Geometry']);group.links.new(compare.outputs['Result'],delete.inputs['Selection']);group.links.new(delete.outputs['Geometry'],output.inputs['Geometry'])
  mod=o.modifiers.new('Shared physical belt output','NODES');mod.node_group=group
  bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_to_index(modifier=mod.name,index=1)
  for prop in ['show_viewport','show_render']:
   driver=mod.driver_add(prop).driver;v=driver.variables.new();v.name='live';v.targets[0].id=rig;v.targets[0].data_path='["BlenderCloth"]';driver.expression='live'
 return proxy.name
