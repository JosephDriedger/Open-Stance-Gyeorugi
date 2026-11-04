"""Physics-only secondary motion trial on the complete corrected export."""
import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;belt_only='--belt-only' in sys.argv
native='--native' in sys.argv
OUT=ROOT/'Resources/Models/FinalRefinement'/('NativeUniformPhysics' if native else 'IntegratedBeltPhysics' if belt_only else 'IntegratedUniformPhysics');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement'/('FootguardSmoothKickReview/Animation_Test.blend' if native else 'StockyFullKickCorrectives/Full_Export_Kick.blend')))
if native:
 for obj in list(bpy.context.scene.objects):
  if obj.get('SimulationOnly'):bpy.data.objects.remove(obj,do_unlink=True)
s=bpy.context.scene;s.frame_set(1);r=next(o for o in s.objects if o.type=='ARMATURE');scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
objects={o.name.split('.')[0]:o for o in s.objects if o.type=='MESH'}
contact=bpy.data.collections.new('Uniform_Leg_Contact');s.collection.children.link(contact)
for name in ('Pants','Body'):
 o=objects[name];contact.objects.link(o);o.modifiers.new('Uniform collision','COLLISION');o.collision.thickness_outer=.002*scale;o.collision.thickness_inner=.001*scale;o.collision.cloth_friction=2
beltcontact=bpy.data.collections.new('Belt_Outer_Contact');s.collection.children.link(beltcontact)
for o in contact.objects:beltcontact.objects.link(o)
parts=('Jacket_Front_Left','Jacket_Front_Right','Jacket_Back','Belt_Tail_Left','Belt_Tail_Right')
if belt_only:
 for name in parts[:3]:
  o=objects[name];beltcontact.objects.link(o);o.modifiers.new('Belt garment contact','COLLISION');o.collision.thickness_outer=.002*scale;o.collision.cloth_friction=2
 parts=parts[3:]
rows=[]
for name in parts:
 o=objects[name];belt=name.startswith('Belt');points=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in points)
 if native:
  for mod in list(o.modifiers):
   if mod.type in ('CLOTH','SOLIDIFY'):o.modifiers.remove(mod)
 pin=o.vertex_groups.new(name='Physical_Attachment')
 for v,p in zip(o.data.vertices,points):
  depth=top-p.z
  weight=max(0,min(1,(.025*scale-depth)/(.012*scale))) if belt else max(0,min(1,(.045*scale-depth)/(.02*scale)))
  pin.add([v.index],weight,'REPLACE')
 cloth=o.modifiers.new('Physical woven motion','CLOTH');cs=cloth.settings
 cs.quality=30;cs.mass=(.035 if belt else .09)/len(o.data.vertices);cs.vertex_group_mass=pin.name;cs.pin_stiffness=30
 cs.use_dynamic_mesh=True;cs.tension_stiffness=100;cs.compression_stiffness=100;cs.shear_stiffness=60;cs.bending_stiffness=4 if belt else 1
 if native:cs.use_dynamic_mesh=False
 cs.tension_damping=12;cs.compression_damping=12;cs.shear_damping=10;cs.bending_damping=6;cs.air_damping=4
 cc=cloth.collision_settings;cc.use_collision=True;cc.collection=beltcontact if belt else contact;cc.distance_min=.003*scale;cc.collision_quality=10;cc.use_self_collision=True;cc.self_distance_min=.002*scale
 cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=144
 thick=o.modifiers.new('Woven thickness','SOLIDIFY');thick.thickness=(.002 if belt else .001)*scale;thick.offset=0
 if not belt:
  o.modifiers.new('Belt contact surface','COLLISION');beltcontact.objects.link(o);o.collision.thickness_outer=.002*scale;o.collision.cloth_friction=2
 rows.append({'part':name,'vertices':len(o.data.vertices),'total_mass_kg':cs.mass*len(o.data.vertices)})
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
for frame in range(1,145):
 s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
 for name in parts:
  ev=objects[name].evaluated_get(dg);mesh=ev.to_mesh();assert all(math.isfinite(x) and abs(x)<5 for v in mesh.vertices for x in v.co),(name,frame);ev.to_mesh_clear()
 if frame%12==0:print('PHYSICS',frame,flush=True)
 if frame in (26,35,72,144):
  review.render(s,r,scale,OUT,f'Full_{frame}',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
  review.render(s,r,scale,OUT,f'Hip_{frame}',(2,-.7,1.25),(0,-.1,.95),.85,700,700)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'frames':144,'finite_geometry':True,'parts':rows,'scope':'Live Blender cloth trial, not collision or visual acceptance. Candidate requires sequential playback from frame 1; cache not packaged.'},indent=2))
