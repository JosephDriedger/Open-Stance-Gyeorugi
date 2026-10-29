import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_hair_surface as hair
import build_single_helmet_study as view
OUT=hair.OUT
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Hair_Pilot.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium']
 s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100;s.cycles.samples=12
 rows=[]
 for style in range(6):
  for helmet in [False,True]:
   r['HairStyle']=style;r['Wear_Helmet']=helmet;r.update_tag();s.frame_set(2);s.frame_set(1)
   view.camera(s,(.3,-.6,1.9),(0,0,1.66),.43)
   path=OUT/f'HairStyle_{style}_Helmet_{int(helmet)}.png';s.render.filepath=str(path);bpy.ops.render.render(write_still=True);rows.append(path.name)
 (OUT/'hair_style_renders.json').write_text(json.dumps(rows))
except:(OUT/'hair_style_error.log').write_text(traceback.format_exc());raise
