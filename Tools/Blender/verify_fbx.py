"""Re-import the exported FBX into a throwaway scene and report scale, hierarchy and skin data."""
import bpy
import rig_config as cfg

log = cfg.open_log("verify_fbx")

main_scene = bpy.context.window.scene if bpy.context.window else bpy.context.scene
tmp = bpy.data.scenes.new("FBX_Verify")
if bpy.context.window:
    bpy.context.window.scene = tmp
before = set(bpy.data.objects)
with bpy.context.temp_override(scene=tmp, view_layer=tmp.view_layers[0], collection=tmp.collection):
    bpy.ops.import_scene.fbx(filepath=cfg.OUTPUT_FBX)
new = [o for o in bpy.data.objects if o not in before]

for o in new:
    log(o.name, o.type, "parent", o.parent.name if o.parent else None, "scale", tuple(round(s, 3) for s in o.scale))
    if o.type == 'MESH':
        cs = [o.matrix_world @ v.co for v in o.data.vertices]
        log("  bbox z", round(min(c.z for c in cs), 3), round(max(c.z for c in cs), 3),
            "x", round(min(c.x for c in cs), 3), round(max(c.x for c in cs), 3),
            "groups", len(o.vertex_groups),
            "images", [n.image.name for m in o.data.materials if m and m.node_tree
                       for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image])
    if o.type == 'ARMATURE':
        bones = o.data.bones
        log("  bones", len(bones), "roots", [b.name for b in bones if not b.parent])
        for n in ("pelvis", "hand_l", "middle_03_l", "foot_r", "ball_r", "head"):
            b = bones[n]
            log("   ", n, tuple(round(c, 3) for c in (o.matrix_world @ b.head_local)), "parent", b.parent.name)

if bpy.context.window:
    bpy.context.window.scene = main_scene
for o in new:
    data = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if isinstance(data, bpy.types.Mesh) and data.users == 0:
        bpy.data.meshes.remove(data)
    elif isinstance(data, bpy.types.Armature) and data.users == 0:
        bpy.data.armatures.remove(data)
bpy.data.scenes.remove(tmp)
for a in list(bpy.data.actions):
    if a.users == 0:
        bpy.data.actions.remove(a)
log("cleanup ok; scenes:", [s.name for s in bpy.data.scenes])
log.close()
