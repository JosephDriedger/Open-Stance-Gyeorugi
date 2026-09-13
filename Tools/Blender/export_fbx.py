"""Reset to rest pose, sanity-check the rig and export the combined Unreal-ready FBX."""
import os
import bpy
import rig_config as cfg

log = cfg.open_log("export_fbx")

arm = bpy.data.objects[cfg.ARMATURE_NAME]
mesh = bpy.data.objects[cfg.MESH_NAME]

for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
arm.hide_set(False)
bpy.context.view_layer.update()

log("armature modifiers:", [(m.name, m.object.name) for m in mesh.modifiers if m.type == 'ARMATURE'])
log("mesh parent:", mesh.parent.name if mesh.parent else None)
log("bones:", len(arm.data.bones), "deform:", sum(b.use_deform for b in arm.data.bones))
log("root children:", [c.name for c in arm.data.bones["root"].children])
log("deform bones without groups:", [b.name for b in arm.data.bones if b.use_deform and b.name not in mesh.vertex_groups])
counts = {g.index: 0 for g in mesh.vertex_groups}
maxinf = 0
for v in mesh.data.vertices:
    used = [g for g in v.groups if g.weight > 0]
    maxinf = max(maxinf, len(used))
    for g in used:
        counts[g.group] += 1
log("empty groups:", [g.name for g in mesh.vertex_groups if counts[g.index] == 0])
log("max influences:", maxinf)

bpy.ops.file.pack_all()
log("images:", [(i.name, i.packed_file is not None) for i in bpy.data.images if i.source == 'FILE'])
os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

for o in bpy.data.objects:
    if o.name in bpy.context.view_layer.objects:
        o.select_set(o in (arm, mesh))
bpy.context.view_layer.objects.active = arm

bpy.ops.export_scene.fbx(
    filepath=cfg.OUTPUT_FBX,
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',  # bake the m->cm conversion so UE sees scale 1 on every node
    axis_forward='-Z',
    axis_up='Y',
    mesh_smooth_type='FACE',
    use_mesh_modifiers=False,             # keep shape keys (morph targets); skinning is exported regardless
    add_leaf_bones=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    use_armature_deform_only=False,       # keep root and ik_* bones
    armature_nodetype='NULL',
    bake_anim=False,
    path_mode='COPY',
    embed_textures=True,
)
log("exported", cfg.OUTPUT_FBX, os.path.getsize(cfg.OUTPUT_FBX))
log.close()
