"""Export each customization part as its own skeletal-mesh FBX on the shared skeleton.

Output: <output>/Modular/SK_Fighter_<Part>.fbx, plus the textures from make_masks.py.
In Unreal, import one part first (it creates the Skeleton asset), then import the rest
with that Skeleton selected so every part shares it.
"""
import os
import bpy
import rig_config as cfg

log = cfg.open_log("export_parts")

PARTS = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]
arm = bpy.data.objects[cfg.ARMATURE_NAME]
out_dir = os.path.join(cfg.OUTPUT_DIR, "Modular")
os.makedirs(out_dir, exist_ok=True)

for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

parts = [bpy.data.objects[f"{cfg.MESH_NAME}_{p}"] for p in PARTS]
hidden = {o.name: o.hide_get() for o in [arm] + parts}
for o in [arm] + parts:
    o.hide_set(False)

for obj in parts:
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(o in (arm, obj))
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(out_dir, obj.name + ".fbx")
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        mesh_smooth_type='FACE',
        use_mesh_modifiers=False,      # keep shape keys (morph targets); the armature is exported as skinning anyway
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_armature_deform_only=False,
        armature_nodetype='NULL',
        bake_anim=False,
        path_mode='COPY',
        embed_textures=False,          # textures ship once, in Textures/
    )
    keys = [k.name for k in obj.data.shape_keys.key_blocks[1:]] if obj.data.shape_keys else []
    log(obj.name, "faces", len(obj.data.polygons), "groups", len(obj.vertex_groups), "morphs", keys,
        "->", path, os.path.getsize(path))

for name, h in hidden.items():
    bpy.data.objects[name].hide_set(h)
log.close()
