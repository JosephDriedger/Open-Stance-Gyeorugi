"""Smooth the rendered live belt while keeping the cloth solver mesh unchanged."""
import bpy

def apply(scene):
 changes=[]
 for o in scene.objects:
  if o.type!='MESH' or 'Belt_Tail_' not in o.name or o.get('SimulationOnly'):continue
  cloth=next((m for m in o.modifiers if m.type=='CLOTH'),None)
  rig=next((m.object for m in o.modifiers if m.type=='ARMATURE' and m.object),None)
  if not cloth or not rig or 'BlenderCloth' not in rig:continue
  if o.modifiers.get('Live belt surface smoothing'):continue
  sub=o.modifiers.new('Live belt surface smoothing','SUBSURF')
  sub.subdivision_type='CATMULL_CLARK';sub.levels=2;sub.render_levels=2
  bpy.context.view_layer.objects.active=o
  index=list(o.modifiers).index(cloth)+1
  bpy.ops.object.modifier_move_to_index(modifier=sub.name,index=index)
  for prop in ['show_viewport','show_render']:
   driver=sub.driver_add(prop).driver;v=driver.variables.new();v.name='live_cloth';v.targets[0].id=rig;v.targets[0].data_path='["BlenderCloth"]';driver.expression='live_cloth'
  changes.append({'object':o.name,'rig':rig.name,'after_cloth':True,'disabled_for_skeletal_export':True})
 return changes

def apply_all():
 previous=bpy.context.window.scene;rows=[]
 for scene in bpy.data.scenes:
  bpy.context.window.scene=scene;rows.extend(apply(scene))
 bpy.context.window.scene=previous;bpy.context.view_layer.update()
 return rows
