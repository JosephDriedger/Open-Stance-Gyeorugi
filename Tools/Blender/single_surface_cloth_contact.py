"""Expose the simulated single surface while rendering thickness separately."""
import bpy

def drive(owner,prop,rig,expression,wardrobe=False):
    owner.driver_remove(prop)
    driver=owner.driver_add(prop).driver
    variable=driver.variables.new();variable.name='live';variable.targets[0].id=rig;variable.targets[0].data_path='["BlenderCloth"]';driver.expression=expression
    if wardrobe:
        variable=driver.variables.new();variable.name='pants';variable.targets[0].id=rig;variable.targets[0].data_path='["Wear_Pants"]'

def separate_render_thickness(scene,source,rig):
    thickness=next(m for m in source.modifiers if m.type=='SOLIDIFY')
    helper=bpy.data.objects.new('SIM_Render_'+source.name,bpy.data.meshes.new('Physical garment render surface'))
    scene.collection.objects.link(helper);helper['SimulationOnly']=True
    group=bpy.data.node_groups.new('Physical surface '+source.name,'GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    info=group.nodes.new('GeometryNodeObjectInfo');info.inputs['Object'].default_value=source;info.transform_space='RELATIVE'
    output=group.nodes.new('NodeGroupOutput');group.links.new(info.outputs['Geometry'],output.inputs['Geometry'])
    helper.modifiers.new('Simulated garment surface','NODES').node_group=group
    shell=helper.modifiers.new('Rendered fabric thickness','SOLIDIFY')
    shell.thickness=thickness.thickness*source.matrix_world.to_scale().x;shell.offset=thickness.offset
    shell.use_rim=thickness.use_rim;shell.use_even_offset=thickness.use_even_offset
    for prop in ['show_viewport','show_render']:drive(thickness,prop,rig,'not live')
    for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:drive(source,prop,rig,'not live')
    for prop in ['hide_render','hide_viewport']:
        drive(helper,prop,rig,'not live or not pants',True)
        drive(source,prop,rig,'live or not pants',True)
    return helper.name
