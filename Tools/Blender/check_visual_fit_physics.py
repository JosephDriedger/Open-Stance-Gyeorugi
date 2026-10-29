import bpy,sys,json,math,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_visual_fit as fix
import setup_blender_cloth as cloth
import repair_hair_surface as hair
import build_single_helmet_study as view
OUT=fix.OUT
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium/Front_Kick.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];s.frame_set(1);rows=fix.repair(s)
 # Preserve the reviewed uniform animation; only belt-tail secondary motion
 # is free in this demo. Fully pinned uniform cloth follows its baked shape.
 for o in s.objects:
  if o.type=='MESH' and o.data.shape_keys and o.name.startswith('Belt_Tail'):
   keys=o.data.shape_keys
   if keys.animation_data:keys.animation_data.action=None
   for k in keys.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
 for name in cloth.PARTS:
  if name.startswith('Belt_Tail'):continue
  o=bpy.data.objects[name];o.vertex_groups['LiveCloth_Pin'].add(list(range(len(o.data.vertices))),1,'REPLACE')
 s['ClothDemoPreset']='Hybrid kick: reviewed baked uniform, fully pinned uniform cloth, live belt tails'
 r['BlenderCloth']=True;r.update_tag();s.frame_set(1)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'LiveCloth_Pilot.blend'),compress=True)
 s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25)
 for frame in range(1,73):
  s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
  for name in cloth.PARTS:
   o=bpy.data.objects.get(name)
   if o and not o.hide_render:
    ev=o.evaluated_get(deps);me=ev.to_mesh();assert all(math.isfinite(c) and abs(c)<5 for v in me.vertices for c in (o.matrix_world@v.co)),(frame,name);ev.to_mesh_clear()
  if frame in [1,18,26,35,55,72]:s.render.filepath=str(OUT/f'Cloth_{frame:03d}.png');bpy.ops.render.render(write_still=True)
  with (OUT/'cloth.log').open('a') as f:f.write(str(frame)+'\n')
 (OUT/'cloth_pilot.json').write_text(json.dumps({'completed':True,'frames':72,'repair':rows},indent=2))
except:(OUT/'cloth_error.log').write_text(traceback.format_exc());raise
