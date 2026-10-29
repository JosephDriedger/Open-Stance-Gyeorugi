import bpy,sys,json,traceback,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=build.ROOT/'Resources/Models/FollowupFix/Medium'
chunk=int(sys.argv[sys.argv.index('--')+1])
try:
 deadline=time.monotonic()+3600
 while not (OUT/'Sample_Demo_validation.json').exists():
  assert time.monotonic()<deadline
  time.sleep(5)
 for folder in ['Frames','SideFrames']:(OUT/folder).mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'));s=bpy.context.scene
 s.cycles.samples=8;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 side=chunk==3
 build.view.camera(s,(4,-.8,1.65) if side else (2.5,-4,2),(0,-.3,.95) if side else (0,-.15,.94),2.25 if side else 2.3)
 for f in range(145 if side else 1+72*chunk,217 if side else 73+72*chunk,2):
  folder='SideFrames' if side else 'Frames';index=(f-145)//2 if side else (f-1)//2;dest=OUT/folder/f'{index:04d}.png'
  if dest.exists():continue
  s.frame_set(f);s.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
 (OUT/f'preview_chunk_{chunk}.done').write_text('Complete')
except:(OUT/f'preview_chunk_{chunk}.error').write_text(traceback.format_exc());raise

