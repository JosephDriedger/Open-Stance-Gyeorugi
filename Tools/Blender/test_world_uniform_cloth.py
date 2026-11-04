"""Isolated cloth trial using corrected mass and unit world transforms; never edit masters."""
import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
from rebuild_belt_solver_mesh import normalize_world_mesh
ROOT=review.ROOT;stiff='--stiff-capsules' in sys.argv
OUT=ROOT/('Resources/Models/FinalRefinement/WorldUniformClothStiff' if stiff else 'Resources/Models/FinalRefinement/WorldUniformCloth');OUT.mkdir(exist_ok=True)
assert not (OUT/'validation.json').exists(),'Preserve previous reviewed result'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Medium_Wrap.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;s.frame_set(1);bpy.context.view_layer.update()
parts=['Jacket','Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']
for o in list(s.objects):
 if o.type=='MESH' and (o.name in parts or o.get('SimulationOnly')):normalize_world_mesh(o)
 for m in list(o.modifiers) if o.type=='MESH' else []:
  if m.type=='CLOTH' and o.name not in parts:
   for prop in ('show_viewport','show_render'):m.driver_remove(prop);setattr(m,prop,False)
if stiff:
 from cloth_capsule_contact import capsules
 contact=capsules(s,r,radius_scale=1.15)
for name in parts:
 o=bpy.data.objects[name];cloth=next(m for m in o.modifiers if m.type=='CLOTH');cs=cloth.settings
 group=o.vertex_groups.get(cs.vertex_group_mass);assert group
 top=max(v.co.z for v in o.data.vertices)
 for v in o.data.vertices:
  p=v.co
  if name.startswith('Jacket_'):w=max(0,min(1,(p.z-top+.04)/.02))
  elif name=='Pants':w=1 if p.z>top-.035 else (.75 if p.z<.17 else .2)
  else:w=1 if abs(p.x)<.22 and p.z>1.35 else .4
  group.add([v.index],w,'REPLACE')
 cs.quality=24;cs.pin_stiffness=1;cs.bending_model='LINEAR';cs.bending_stiffness=2
 cs.tension_stiffness=120;cs.compression_stiffness=120;cs.shear_stiffness=60
 cs.air_damping=5;cs.use_dynamic_mesh=True
 cloth.collision_settings.distance_min=.002;cloth.collision_settings.collision_quality=8
 cloth.collision_settings.use_self_collision=True;cloth.collision_settings.self_distance_min=.002
 if stiff:
  cs.bending_model='ANGULAR';cs.bending_stiffness=15;cs.bending_damping=20
  cs.tension_stiffness=500;cs.compression_stiffness=500;cs.shear_stiffness=200;cs.air_damping=8
  cloth.collision_settings.use_self_collision=False
  if name!='Jacket':cloth.collision_settings.collection=contact
 cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=72
r['Wear_Protector']=False;r['Wear_Helmet']=False;r['BlenderCloth']=True;r.update_tag();s.frame_set(1);s.frame_end=72
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
for frame in range(1,73):
 s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
 for name in parts:
  o=bpy.data.objects[name];ev=o.evaluated_get(dg);mesh=ev.to_mesh()
  assert all(math.isfinite(x) and abs(x)<5 for v in mesh.vertices for x in o.matrix_world@v.co),(frame,name)
  ev.to_mesh_clear()
 if frame in (1,26,35,72):review.render(s,r,1,OUT,'Side_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,640,720)
 print('WORLD_UNIFORM_FRAME',frame,flush=True)
(OUT/'validation.json').write_text(json.dumps({'frames':72,'finite':True,'production_installed':False,'belt_simulation':'disabled to isolate garments'},indent=2))
