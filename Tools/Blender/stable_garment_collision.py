"""Use a skinned collision surface without feedback from another cloth solver."""
import bpy
from rebuild_belt_solver_mesh import normalize_world_mesh

def replace_pants(scene,cloth):
    collection=cloth.collision_settings.collection
    old=bpy.data.objects.get('SIM_Contact_Pants')
    if old and old.name in collection.objects:collection.objects.unlink(old)
    source=bpy.data.objects['Pants'];proxy=source.copy();proxy.data=source.data.copy()
    proxy.name='SIM_Stable_Pants_Contact';collection.objects.link(proxy)
    proxy.animation_data_clear();proxy.hide_viewport=False;proxy.hide_render=False;proxy.hide_set(False)
    proxy['SimulationOnly']=True;proxy.display_type='WIRE'
    for modifier in list(proxy.modifiers):
        if modifier.type not in ['ARMATURE','SUBSURF','SMOOTH','CORRECTIVE_SMOOTH','MASK']:proxy.modifiers.remove(modifier)
    normalize_world_mesh(proxy)
    proxy.modifiers.new('Stable garment contact','COLLISION')
    settings=proxy.collision;settings.thickness_outer=.002;settings.thickness_inner=.001;settings.cloth_friction=0
    settings.use_normal=True;settings.use_culling=False
    for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
    return proxy.name
