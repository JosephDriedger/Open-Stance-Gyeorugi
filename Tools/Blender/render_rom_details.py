import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import audit_fighter_range as audit
OUT=audit.OUT
try:
 for kind in ['Updated_Medium','Stocky']:
  folder=OUT/kind;bpy.ops.wm.open_mainfile(filepath=str(folder/'ROM_Audit.blend'));s=bpy.context.scene;s.render.resolution_x=720;s.render.resolution_y=720;s.cycles.samples=12
  for label,f in [('Overhead',25),('Squat',145),('Wrist',241),('Hip',97)]:
   s.frame_set(f);target=(0,-.03,1.38) if label in ['Overhead','Wrist'] else (0,-.05,.77 if label=='Squat' else .94)
   audit.build.view.camera(s,(3,-1,1.5),target,.86);s.render.filepath=str(folder/f'Detail_{label}.png');bpy.ops.render.render(write_still=True)
 if not all(json.loads((p/'audit.json').read_text()).get('cross_body_fixture') for p in OUT.iterdir() if (p/'audit.json').exists()):raise RuntimeError('Wait for cross-body fixture updates before video')
 folder=OUT/'Updated_Medium';bpy.ops.wm.open_mainfile(filepath=str(folder/'ROM_Audit.blend'));s=bpy.context.scene;s.render.resolution_x=480;s.render.resolution_y=540;s.cycles.samples=4
 frames=folder/'Frames';frames.mkdir(exist_ok=True)
 audit.build.view.camera(s,(2.5,-4,2),(0,-.1,.96),2.35)
 for f in range(1,277,3):
  s.frame_set(f);s.render.filepath=str(frames/f'{f:04d}.png');bpy.ops.render.render(write_still=True)
 (OUT/'detail_video.log').write_text('COMPLETE')
except:(OUT/'detail_video.log').write_text(traceback.format_exc());raise
