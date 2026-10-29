import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import setup_blender_cloth as c
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/ClothFreeHems';out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.ROOT/'Resources/Models/Animation/Samples/Front_Kick.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;s.frame_set(1)
from cloth_capsule_contact import capsules
contact=capsules(s,r)
for name in c.PARTS:
 o=bpy.data.objects[name];keys=o.data.shape_keys
 if keys:
  if keys.animation_data:keys.animation_data.action=None
  for k in keys.key_blocks:
   if k.name.startswith(('ClothBake','Pose_')):k.value=0
 pin=o.vertex_groups['LiveCloth_Pin'];pts=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in pts)
 for v,p in zip(o.data.vertices,pts):
  w=max(0,min(1,(p.z-top+.035)/.02)) if name.startswith('Belt_Tail') else (max(0,min(1,(p.z-top+.055)/.035)) if name.startswith('Jacket_') and name!='Jacket_WhiteVNeck' else (1 if p.z>top-.025 else (.25 if name=='Pants' and p.z<.2 else .9)))
  pin.add([v.index],w,'REPLACE')
 for m in o.modifiers:
  if m.type=='CLOTH':
   cs=m.settings;cs.quality=12;cs.pin_stiffness=50;cs.mass=.1;cs.use_dynamic_mesh=True;cs.tension_stiffness=100;cs.compression_stiffness=100;cs.shear_stiffness=50;cs.bending_stiffness=1;cs.air_damping=5
   m.collision_settings.collection=contact;m.collision_settings.use_collision=True;m.collision_settings.distance_min=.001;m.collision_settings.collision_quality=8;m.collision_settings.use_self_collision=False;m.point_cache.frame_start=1;m.point_cache.frame_end=72
r['BlenderCloth']=True;r.update_tag();s.frame_start=1;s.frame_end=72;s.frame_set(1);bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Pilot.blend'),compress=True)
s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True
for frame in range(1,73):
 s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
 for name in c.PARTS:
  o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();assert all(math.isfinite(x) and abs(x)<5 for v in me.vertices for x in o.matrix_world@v.co);ev.to_mesh_clear()
 if frame in [1,26,35,72]:a.render(s,r,1,out,'Frame_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,640,720)
 with (out/'progress.log').open('a') as f:f.write(str(frame)+'\n')

