import bpy, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/ROMRepair/Updated_Medium')
def log(s):
 with (OUT/'preview.log').open('a') as f:f.write(s+'\n')
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene
 scene.render.resolution_x=640;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 build.view.camera(scene,(2.5,-4,2),(0,-.15,.94),2.3)
 for name in ['Frames','SideFrames']:(OUT/name).mkdir(exist_ok=True)
 for f in range(1,217,2):
  scene.frame_set(f);scene.render.filepath=str(OUT/'Frames'/f'{(f-1)//2:04d}.png');bpy.ops.render.render(write_still=True)
  if f>=145:
   build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25);scene.render.filepath=str(OUT/'SideFrames'/f'{(f-145)//2:04d}.png');bpy.ops.render.render(write_still=True)
   build.view.camera(scene,(2.5,-4,2),(0,-.15,.94),2.3)
  if f%24==1:log('RENDER '+str(f))
 log('COMPLETE')
except:log(traceback.format_exc());raise
