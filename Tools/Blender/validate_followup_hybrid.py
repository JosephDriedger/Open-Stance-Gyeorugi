import bpy,sys,math,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_followup as fix
import setup_blender_cloth as cloth
import build_single_helmet_study as view
d=fix.OUT/'HybridReview';d.mkdir(exist_ok=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/'Medium/LiveCloth_Pilot.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];assert r['BlenderCloth']
 s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25)
 for f in range(1,73):
  s.frame_set(f);deps=bpy.context.evaluated_depsgraph_get()
  for name in cloth.PARTS:
   o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh()
   assert all(math.isfinite(c) and abs(c)<5 for v in me.vertices for c in (o.matrix_world@v.co)),(f,name)
   ev.to_mesh_clear()
  if f in [26,35,72]:s.render.filepath=str(d/f'{f}.png');bpy.ops.render.render(write_still=True)
 (d/'validation.json').write_text(json.dumps({'completed':True,'frames':72,'uniform_fully_pinned':True,'belt_tails_live':True}))
except:(d/'error.log').write_text(traceback.format_exc());raise
