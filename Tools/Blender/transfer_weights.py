"""Skin a new gear/face mesh to the fighter skeleton by copying weights from the base body.

Usage (console):
    run("transfer_weights", TRANSFER_TARGETS=["MyNewHelmet"])

Each target must already be placed on the T-posed fighter in Blender's coordinates.
Weights are interpolated from the nearest faces of the combined SK_Fighter mesh; then
the target gets limited to 4 influences, normalised, parented to the armature, and
given the same body-type shape keys (offsets copied from the nearest base vertex) so
it follows BodyHeavy/BodyMuscular/BodySlim.
Target names come from TRANSFER_TARGETS in the caller's namespace, or the selected meshes.
"""
import bpy
from mathutils.kdtree import KDTree
import rig_config as cfg

log = cfg.open_log("transfer_weights")

base = bpy.data.objects[cfg.MESH_NAME]
arm = bpy.data.objects[cfg.ARMATURE_NAME]
names = globals().get("TRANSFER_TARGETS") or [o.name for o in bpy.context.selected_objects
                                              if o.type == 'MESH' and not o.name.startswith(cfg.MESH_NAME)]
if not names:
    raise RuntimeError("No targets: set TRANSFER_TARGETS or select the new meshes")

base_was_hidden = base.hide_get()
base.hide_set(False)

bw = base.matrix_world
kd = KDTree(len(base.data.vertices))
for v in base.data.vertices:
    kd.insert(bw @ v.co, v.index)
kd.balance()

for name in names:
    obj = bpy.data.objects[name]
    obj.vertex_groups.clear()
    for m in list(obj.modifiers):
        if m.type in ('ARMATURE', 'DATA_TRANSFER'):
            obj.modifiers.remove(m)

    dt = obj.modifiers.new("WeightTransfer", 'DATA_TRANSFER')
    dt.object = base
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'

    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(o == obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)

    # prune / limit / normalise
    me = obj.data
    idx_name = {g.index: g.name for g in obj.vertex_groups}
    for v in me.vertices:
        current = [(g.group, g.weight) for g in v.groups]   # snapshot: editing groups invalidates v.groups
        ws = sorted((t for t in current if t[1] >= 0.02), key=lambda t: -t[1])[:4]
        total = sum(w for _, w in ws) or 1.0
        keep = {gi: w / total for gi, w in ws}
        for gi, _ in current:
            vg = obj.vertex_groups[idx_name[gi]]
            if gi in keep:
                vg.add([v.index], keep[gi], 'REPLACE')
            else:
                vg.remove([v.index])
    used = {g.group for v in me.vertices for g in v.groups}
    for n in [g.name for g in obj.vertex_groups if g.index not in used]:
        obj.vertex_groups.remove(obj.vertex_groups[n])

    # body-type shape keys: copy the nearest base vertex's offset
    if base.data.shape_keys:
        ow = obj.matrix_world
        oinv = ow.inverted()
        if me.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        nearest = [kd.find(ow @ v.co)[1] for v in me.vertices]
        basis = base.data.shape_keys.key_blocks[0].data
        for kb in base.data.shape_keys.key_blocks[1:]:
            if kb.name in me.shape_keys.key_blocks:
                obj.shape_key_remove(me.shape_keys.key_blocks[kb.name])
            key = obj.shape_key_add(name=kb.name, from_mix=False)
            coords = []
            for v, ni in zip(me.vertices, nearest):
                offset = (bw @ kb.data[ni].co) - (bw @ basis[ni].co)
                coords.extend(oinv @ ((ow @ v.co) + offset))
            key.data.foreach_set("co", coords)

    mw = obj.matrix_world.copy()
    obj.parent = arm
    obj.matrix_world = mw
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    log(name, "verts", len(me.vertices), "groups", len(obj.vertex_groups),
        "morphs", [k.name for k in me.shape_keys.key_blocks[1:]] if me.shape_keys else [])

base.hide_set(base_was_hidden)
log.close()
