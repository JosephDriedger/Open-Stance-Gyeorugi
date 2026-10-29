import bpy,sys,json,math,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_followup as fix
import setup_blender_cloth as cloth
import build_single_helmet_study as view
OUT=fix.OUT/'Physics';OUT.mkdir(exist_ok=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/'Medium/Front_Kick.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False
 for o in s.objects:
  if o.type=='MESH' and o.data.shape_keys and o.name in cloth.PARTS:
   keys=o.data.shape_keys
   if keys.animation_data:keys.animation_data.action=None
   for k in keys.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
 for name in cloth.PARTS:
  o=bpy.data.objects[name];pin=o.vertex_groups['LiveCloth_Pin'];pts=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in pts)
  for v,p in zip(o.data.vertices,pts):
   if name.startswith('Belt_Tail'):w=max(0,min(1,(p.z-top+.035)/.02))
   elif name.startswith('Jacket_') and name!='Jacket_WhiteVNeck':w=1 if p.z>top-.035 else .78
   elif name=='Pants':w=1 if p.z>.90 else .90
   else:w=1 if abs(p.x)<.26 else .88
   pin.add([v.index],w,'REPLACE')
  for m in o.modifiers:
   if m.type=='CLOTH':
    m.settings.quality=16;m.settings.pin_stiffness=1;m.point_cache.frame_start=1;m.point_cache.frame_end=72
    m.collision_settings.collision_quality=8
 s.frame_start=1;s.frame_end=72
 frames=[1,18,26,35,55,72];baseline={}
 def positions(o):
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pts=[o.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear();return pts
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();baseline[f]={n:positions(bpy.data.objects[n]) for n in cloth.PARTS}
 r['BlenderCloth']=True;r.update_tag();s.frame_set(1);bpy.context.view_layer.update()
 s['ClothDemoPreset']='Live secondary cloth: anchored seams, partially constrained panels and trousers, free belt tails; no clip-specific cloth keyframes'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LiveCloth_Pilot.blend'),compress=True)
 s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25)
 rows=[]
 for f in range(1,73):
  s.frame_set(f);bpy.context.view_layer.update()
  for n in cloth.PARTS:
   pts=positions(bpy.data.objects[n]);assert all(math.isfinite(c) and abs(c)<5 for p in pts for c in p),(f,n,'unstable')
   if f in frames:
    ref=baseline[f][n];assert len(ref)==len(pts)
    rows.append({'frame':f,'part':n,'max_secondary_motion_m':max((p-q).length for p,q in zip(pts,ref))})
  if f in frames:s.render.filepath=str(OUT/f'Cloth_{f:03d}.png');bpy.ops.render.render(write_still=True)
  with (OUT/'progress.log').open('a') as log:log.write(str(f)+'\n')
 (OUT/'simulation.json').write_text(json.dumps({'completed':True,'frames':72,'measurements':rows,'requires_visual_review':True},indent=2))
except:(OUT/'error.log').write_text(traceback.format_exc());raise
