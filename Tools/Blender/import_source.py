"""Clear the scene and import the source Meshy FBX."""
import bpy
import rig_config as cfg

log = cfg.open_log("import_source")

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images, bpy.data.actions,
             bpy.data.cameras, bpy.data.lights):
    for block in list(coll):
        if block.users == 0:
            coll.remove(block)

bpy.ops.import_scene.fbx(filepath=cfg.SOURCE_FBX)
log("imported", cfg.SOURCE_FBX)
log("objects:", [(o.name, o.type) for o in bpy.data.objects])
log.close()
