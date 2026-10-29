"""Optional live Blender cloth; base rig and export poses remain unchanged."""
import bpy,sys,json,traceback,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_hair_surface as hair
import build_single_helmet_study as view
OUT=hair.OUT
PARTS=['Jacket','Jacket_WhiteVNeck','Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back','Belt_Tail_Left','Belt_Tail_Right']
def setup(scene):
 r=next(o for o in scene.objects if o.name.startswith('RIG_Body_'));r['BlenderCloth']=False
 r.id_properties_ui('BlenderCloth').update(description='Live Blender cloth. Start playback at cache frame 1; clear cache after animation or wardrobe edits. Off for skeletal FBX export.')
 collection=bpy.data.collections.new('Cloth_Body_Contact');scene.collection.children.link(collection)
 body=bpy.data.objects['Body'];proxy=body.copy();proxy.data=body.data.copy();proxy.name='SIM_Body_Collider';collection.objects.link(proxy);proxy.animation_data_clear()
 if proxy.data.shape_keys:proxy.shape_key_clear()
 for m in list(proxy.modifiers):
  if m.type!='ARMATURE':proxy.modifiers.remove(m)
 proxy.hide_render=True;proxy.hide_viewport=False;proxy.hide_set(False);proxy.display_type='WIRE'
 # A contact-only mesh must not be exported with the character.
 proxy['SimulationOnly']=True
 proxy.modifiers.new('Body cloth contact','COLLISION');proxy.collision.thickness_outer=.002;proxy.collision.thickness_inner=.001;proxy.collision.cloth_friction=5
 belt_contact=bpy.data.collections.new('Cloth_Belt_Contact');scene.collection.children.link(belt_contact);belt_contact.objects.link(proxy)
 for part in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  source=bpy.data.objects.get(part)
  if not source:continue
  contact=source.copy();contact.data=source.data.copy();contact.name='SIM_'+part+'_Collider';belt_contact.objects.link(contact);contact.animation_data_clear()
  for m in list(contact.modifiers):
   if m.type not in ['ARMATURE']:contact.modifiers.remove(m)
  contact.hide_render=True;contact.hide_viewport=False;contact.hide_set(False);contact.display_type='WIRE';contact['SimulationOnly']=True
  contact.modifiers.new('Belt garment contact','COLLISION');contact.collision.thickness_outer=.002;contact.collision.thickness_inner=.001;contact.collision.cloth_friction=5
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;pelvis=(r.matrix_world@r.data.bones['pelvis'].head_local).z
 rows=[]
 for name in PARTS:
  o=bpy.data.objects.get(name)
  if not o:continue
  group=o.vertex_groups.get('LiveCloth_Pin') or o.vertex_groups.new(name='LiveCloth_Pin')
  pts=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in pts)
  for v,p in zip(o.data.vertices,pts):
   if name.startswith('Belt_Tail'):weight=max(0,min(1,(p.z-(top-.035*scale))/(.02*scale)))
   elif name.startswith('Jacket_') and name!='Jacket_WhiteVNeck':weight=max(.04,min(1,(p.z-(top-.055*scale))/(.035*scale)))
   elif name=='Pants':weight=1 if p.z>pelvis-.06*scale else .88
   else:weight=1 if abs(p.x)<.23*scale else .9
   group.add([v.index],weight,'REPLACE')
  cloth=o.modifiers.new('Live woven cloth','CLOTH');cs=cloth.settings;cs.quality=12;cs.mass=.24 if name.startswith('Belt') else .16
  cs.tension_stiffness=100;cs.compression_stiffness=80;cs.shear_stiffness=50;cs.bending_stiffness=1.2 if name.startswith('Belt') else .5
  cs.tension_damping=12;cs.compression_damping=12;cs.shear_damping=10;cs.bending_damping=8;cs.air_damping=3
  cs.vertex_group_mass=group.name;cs.pin_stiffness=1;cs.use_dynamic_mesh=True
  collision=cloth.collision_settings;collision.use_collision=True;collision.collection=belt_contact if name.startswith('Belt') else collection;collision.distance_min=.003;collision.collision_quality=6;collision.use_self_collision=False
  cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=max(120,scene.frame_end)
  for prop in ['show_viewport','show_render']:
   d=cloth.driver_add(prop).driver;v=d.variables.new();v.name='enabled';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';d.expression='enabled'
  # Thickness follows the cloth solver; it must not simulate as a double shell.
  bpy.context.view_layer.objects.active=o
  for m in list(o.modifiers):
   if m.type=='SOLIDIFY':bpy.ops.object.modifier_move_to_index(modifier=m.name,index=len(o.modifiers)-1)
  rows.append({'object':name,'vertices':len(o.data.vertices),'pin_group':group.name})
 for contact in scene.objects:
  if contact.get('SimulationOnly'):
   d=contact.driver_add('hide_viewport').driver;v=d.variables.new();v.name='enabled';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';d.expression='not enabled'
 # Cloth.mass is per solver vertex. Keep total garment-part mass independent
 # of topology density instead of assigning hundreds of kilograms to an LOD.
 from normalize_uniform_cloth_mass import configure as normalize_mass
 normalize_mass(scene)
 return rows
if __name__=='__main__':
 try:
  bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/Front_Kick.blend')
  s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];s.frame_set(1)
  # Existing baked panels must not be added a second time on top of dynamics.
  for o in s.objects:
   if o.type=='MESH' and o.data.shape_keys:
    keys=o.data.shape_keys
    if keys.animation_data:keys.animation_data.action=None
    for k in keys.key_blocks:
     if k.name.startswith(('ClothBake','Pose_')):k.value=0
  rows=setup(s);r['BlenderCloth']=True;r.update_tag();s.frame_set(1);s.frame_end=72
  s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
  view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25)
  bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LiveCloth_Pilot.blend'),compress=True)
  extremes=[]
  for frame in range(1,73):
   s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
   for name in PARTS:
    o=bpy.data.objects.get(name)
    if o and not o.hide_render:
     ev=o.evaluated_get(deps);me=ev.to_mesh();pts=[o.matrix_world@v.co for v in me.vertices]
     assert all(math.isfinite(c) and abs(c)<5 for p in pts for c in p),(frame,name,'unstable cloth')
     ev.to_mesh_clear()
   if frame in [1,18,26,35,55,72]:
    s.render.filepath=str(OUT/f'Cloth_{frame:03d}.png');bpy.ops.render.render(write_still=True)
   with (OUT/'cloth.log').open('a') as f:f.write(str(frame)+'\n')
  (OUT/'cloth_pilot.json').write_text(json.dumps({'completed':True,'objects':rows},indent=2))
 except:(OUT/'cloth_error.log').write_text(traceback.format_exc());raise
