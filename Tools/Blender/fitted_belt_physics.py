"""Experimental fitted belt contact and constrained uniform secondary motion."""
import bpy
from cloth_capsule_contact import capsules
from setup_blender_cloth import PARTS
from belt_surface_finish import apply as smooth_belts

def configure(scene,rig,contact_range=(.005,.018)):
 assert 0<contact_range[0]<=contact_range[1]<.05
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 rig['BlenderCloth']=False;rig.update_tag();scene.frame_set(1);bpy.context.view_layer.update()
 limb_contact=capsules(scene,rig)
 outer=bpy.data.collections.new('SIM_Belt_Fitted_Contact');scene.collection.children.link(outer)
 source=bpy.data.objects['Pants'];proxy=source.copy();proxy.data=source.data.copy();proxy.animation_data_clear();proxy.name='SIM_Belt_Fitted_Contact';outer.objects.link(proxy)
 for modifier in list(proxy.modifiers):
  if modifier.type!='ARMATURE':proxy.modifiers.remove(modifier)
 keys=proxy.data.shape_keys
 if keys:
  if keys.animation_data:
   keys.animation_data.action=None
   for track in keys.animation_data.nla_tracks:track.mute=True
  for key in keys.key_blocks:
   if key.name.startswith(('ClothBake','Pose_')):key.value=0
 inverse=proxy.matrix_world.inverted().to_3x3();normal_matrix=proxy.matrix_world.to_3x3().inverted().transposed()
 offsets=[]
 for v in proxy.data.vertices:
  z=(proxy.matrix_world@v.co).z/scale
  amount=(contact_range[0]+(contact_range[1]-contact_range[0])*max(0,min(1,(z-.65)/.15)))*scale
  offsets.append(inverse@((normal_matrix@v.normal).normalized()*amount))
 for v,delta in zip(proxy.data.vertices,offsets):
  v.co+=delta
  if keys:
   for key in keys.key_blocks:key.data[v.index].co+=delta
 proxy.modifiers.new('Belt sliding contact','COLLISION');proxy.collision.thickness_outer=.002;proxy.collision.thickness_inner=.001;proxy.collision.cloth_friction=0
 proxy.hide_render=False;proxy.hide_viewport=False;proxy.hide_set(False);proxy.display_type='WIRE';proxy['SimulationOnly']=True
 for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
 changes=[]
 for name in PARTS:
  o=bpy.data.objects.get(name)
  if not o:continue
  keys=o.data.shape_keys
  if keys:
   if keys.animation_data:
    keys.animation_data.action=None
    for track in keys.animation_data.nla_tracks:track.mute=True
   for key in keys.key_blocks:
    if key.name.startswith(('ClothBake','Pose_')):key.value=0
  pin=o.vertex_groups.get('LiveCloth_Pin');cloth=next((m for m in o.modifiers if m.type=='CLOTH'),None)
  assert pin and cloth,(name,'Missing existing cloth setup')
  points=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in points);belt=name.startswith('Belt_Tail')
  for v,p in zip(o.data.vertices,points):
   weight=max(0,min(1,(p.z-top+.035*scale)/(.02*scale))) if belt else (1 if p.z>top-.025*scale else .96)
   pin.add([v.index],weight,'REPLACE')
  cs=cloth.settings;cs.quality=30 if belt else 12;cs.pin_stiffness=50;cs.mass=.03 if belt else .1;cs.use_dynamic_mesh=True
  cs.tension_stiffness=100;cs.compression_stiffness=100;cs.shear_stiffness=50;cs.bending_stiffness=50 if belt else 1;cs.air_damping=8 if belt else 5
  if belt:cs.bending_damping=10
  cc=cloth.collision_settings;cc.collection=outer if belt else limb_contact;cc.use_collision=True;cc.distance_min=.001;cc.collision_quality=12 if belt else 8;cc.use_self_collision=False
  cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=144
  changes.append(name)
 smooth_belts(scene)
 from normalize_uniform_cloth_mass import configure as normalize_mass
 uniform_mass=normalize_mass(scene)
 rig['BlenderCloth']=True;rig.update_tag();scene.frame_set(1);bpy.context.view_layer.update()
 return {'parts':changes,'scale':scale,'belt_contact':proxy.name,'contact_range_at_medium_scale':list(contact_range),'uniform_mass':uniform_mass,'experimental':True}
