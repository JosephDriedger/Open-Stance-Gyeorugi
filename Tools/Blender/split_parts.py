"""Pass 3 of the part split: create one skinned mesh object per part from the "part" attribute.

Each part keeps the full vertex-group set, UVs, material and the Armature modifier, so every
piece deforms identically to the combined mesh. The combined SK_Fighter stays in the file
(hidden, excluded from part exports) as the reference.
"""
import bmesh
import bpy
import rig_config as cfg

log = cfg.open_log("split_parts")

PARTS = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]

src = bpy.data.objects[cfg.MESH_NAME]
arm = bpy.data.objects[cfg.ARMATURE_NAME]
coll = src.users_collection[0]
part_attr = [0] * len(src.data.polygons)
src.data.attributes["part"].data.foreach_get("value", part_attr)

for name in PARTS:
    old = bpy.data.objects.get(f"{cfg.MESH_NAME}_{name}")
    if old:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)

for pi, name in enumerate(PARTS):
    me = src.data.copy()
    me.name = f"{cfg.MESH_NAME}_{name}"
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if part_attr[f.index] != pi]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    for attr in ("patch", "colour_class"):
        if attr in me.attributes:
            me.attributes.remove(me.attributes[attr])

    obj = bpy.data.objects.new(me.name, me)
    coll.objects.link(obj)
    obj.parent = arm
    obj.matrix_world = src.matrix_world.copy()
    for g in src.vertex_groups:
        obj.vertex_groups.new(name=g.name)
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm

    # drop vertex groups this part never uses (keeps UE influence tables small)
    used = set()
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 0:
                used.add(g.group)
    unused = [g.name for g in obj.vertex_groups if g.index not in used]  # names first: removal shifts indices
    for n in unused:
        obj.vertex_groups.remove(obj.vertex_groups[n])
    log(name, "verts", len(me.vertices), "faces", len(me.polygons), "groups", len(obj.vertex_groups))

src.hide_set(True)
src.hide_render = True
log.close()
