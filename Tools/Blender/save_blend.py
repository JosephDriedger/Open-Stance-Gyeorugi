"""Final pipeline step: rest pose, pack images and save Fighter_Rigged.blend."""
import os
import bpy
import rig_config as cfg

log = cfg.open_log("save_blend")

arm = bpy.data.objects[cfg.ARMATURE_NAME]
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

bpy.ops.file.pack_all()
os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=cfg.OUTPUT_BLEND, copy=True)
log("saved", cfg.OUTPUT_BLEND, os.path.getsize(cfg.OUTPUT_BLEND))
log.close()
