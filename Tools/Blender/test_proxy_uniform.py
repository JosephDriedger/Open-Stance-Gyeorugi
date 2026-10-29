"""Experimental low-density cloth cages; never writes production assets."""
import bpy,sys,json,math,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import setup_blender_cloth as cloth
import build_single_helmet_study as view
OUT=build.ROOT/'Resources/Models/CrowdFaceRefinement/ClothProxyTrial';OUT.mkdir(parents=True,exist_ok=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(build.ROOT/'Resources/Models/Animation/Samples/Front_Kick.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;s.frame_set(1)
 r.data.pose_position='REST';bpy.context.view_layer.update()
 for name in cloth.PARTS:
  high=bpy.data.objects[name]
  if high.data.shape_keys:
   keys=high.data.shape_keys
   if keys.animation_data:keys.animation_data.action=None
   for k in keys.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
  if name.startswith('Belt_Tail'):continue
  proxy=high.copy();proxy.data=high.data.copy();proxy.name='SIM_Cage_'+name;s.collection.objects.link(proxy)
  proxy.animation_data_clear();proxy.hide_render=True;proxy.hide_viewport=False;proxy.hide_set(False);proxy.display_type='WIRE';proxy['SimulationOnly']=True
  for m in list(proxy.modifiers):
   if m.type!='ARMATURE':proxy.modifiers.remove(m)
  if proxy.data.shape_keys:proxy.shape_key_clear()
  build.reduce_mesh(proxy,900 if name in ['Pants','Jacket','Jacket_WhiteVNeck'] else 320)
  pin=proxy.vertex_groups.get('LiveCloth_Pin') or proxy.vertex_groups.new(name='LiveCloth_Pin')
  pts=[proxy.matrix_world@v.co for v in proxy.data.vertices];top=max(p.z for p in pts)
  for v,p in zip(proxy.data.vertices,pts):
   if name=='Pants':w=1 if p.z>.90 else .75
   elif name in ['Jacket','Jacket_WhiteVNeck']:w=1 if abs(p.x)<.26 else .75
   else:w=1 if p.z>top-.035 else .65
   pin.add([v.index],w,'REPLACE')
  mod=proxy.modifiers.new('Coarse cloth','CLOTH');cs=mod.settings;cs.quality=16;cs.mass=.16;cs.vertex_group_mass=pin.name;cs.pin_stiffness=20;cs.use_dynamic_mesh=True
  cs.tension_stiffness=100;cs.compression_stiffness=80;cs.shear_stiffness=50;cs.bending_stiffness=5
  cs.tension_damping=20;cs.compression_damping=20;cs.shear_damping=20;cs.bending_damping=12
  mod.collision_settings.use_collision=True;mod.collision_settings.collection=bpy.data.collections.get('Cloth_Body_Contact');mod.collision_settings.distance_min=.002;mod.collision_settings.collision_quality=6
  mod.point_cache.frame_start=1;mod.point_cache.frame_end=72
  mod.show_viewport=False;mod.show_render=False
  if high.data.shape_keys:high.shape_key_clear()
  for m in list(high.modifiers):
   if m.type in ['ARMATURE','CLOTH']:high.modifiers.remove(m)
  deform=high.modifiers.new('Simulated cloth cage','SURFACE_DEFORM');deform.target=proxy
  bpy.context.view_layer.objects.active=high
  bpy.ops.object.modifier_move_to_index(modifier=deform.name,index=0)
  hidden=high.hide_viewport;high.hide_viewport=False;high.hide_set(False)
  bpy.ops.object.surfacedeform_bind(modifier=deform.name)
  assert deform.is_bound,name
  high.hide_viewport=hidden
  mod.show_viewport=True;mod.show_render=True
 r.data.pose_position='POSE';r['BlenderCloth']=True;r.update_tag();s.frame_set(1);bpy.context.view_layer.update()
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prototype.blend'),compress=True)
 s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100;view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25)
 for f in range(1,73):
  s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get()
  for name in cloth.PARTS:
   o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();assert all(math.isfinite(c) and abs(c)<5 for v in me.vertices for c in o.matrix_world@v.co),(f,name);ev.to_mesh_clear()
  if f in [1,18,26,35,55,72]:s.render.filepath=str(OUT/f'{f}.png');bpy.ops.render.render(write_still=True)
 (OUT/'validation.json').write_text(json.dumps({'completed':True,'frames':72,'requires_visual_review':True}))
except:(OUT/'error.log').write_text(traceback.format_exc());raise
