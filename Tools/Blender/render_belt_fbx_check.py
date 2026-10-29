import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import rebuild_updated_characters as build
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/BeltFit')
bpy.ops.wm.open_mainfile(filepath=str(out/'Medium_Sparring_Samples.blend'))
for o in list(bpy.data.objects):
 if o.type in {'MESH','ARMATURE'} and o.name not in {'Mat','MatBorder'}:bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(out/'Front_Kick.fbx'))
s=bpy.context.scene
for f in [1,26,35]:
 s.frame_set(f);build.view.camera(s,(3,-1,1.55),(0,-.02,1.01),.83);s.render.filepath=str(out/f'FBX_Waist_{f}.png');bpy.ops.render.render(write_still=True)
(out/'fbx_render.log').write_text('COMPLETE')
