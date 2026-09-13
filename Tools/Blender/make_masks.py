"""Bake customization masks aligned to the fighter's baked texture.

Output textures (in <output>/Textures):
  T_Fighter_BaseColor.png  the original baked texture
  T_Fighter_Masks.png      R = team colour (blue on helmet/protector)
                           G = belt
                           B = dark dan collar on the jacket
                           A = skin (face, fingers, toes)

Part IDs are baked from the "part" face attribute with Cycles (handles the fragmented UV
atlas and chart margins); pixel colour then gates each mask so trim and stitching keep
their original colour.
"""
import os

import bpy
import numpy as np
import rig_config as cfg

log = cfg.open_log("make_masks")

PARTS = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]
ID_SCALE = 16.0

src = bpy.data.objects[cfg.MESH_NAME]
me = src.data
base_img = next(n.image for m in me.materials if m and m.node_tree
                for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
W, H = base_img.size
tex_dir = os.path.join(cfg.OUTPUT_DIR, "Textures")
os.makedirs(tex_dir, exist_ok=True)

# --- part id as a linear float colour attribute ---
part = [0] * len(me.polygons)
me.attributes["part"].data.foreach_get("value", part)
if "bake_part_id" in me.color_attributes:
    me.color_attributes.remove(me.color_attributes["bake_part_id"])
attr = me.color_attributes.new("bake_part_id", 'FLOAT_COLOR', 'CORNER')

# G channel: faces of the shirt shell that sits under the chest protector (same zone that
# fit_to_body pulls in for the gear-free dobok). Its texture has the protector's rim shadows and
# a partial black collar V baked in, which show once the protector comes off.
arm = bpy.data.objects.get(cfg.ARMATURE_NAME)


def joint(name, fallback):
    if arm and name in arm.data.bones:
        return arm.matrix_world @ arm.data.bones[name].head_local
    return fallback


from mathutils import Vector
PELVIS_Z = joint("pelvis", Vector((0, 0, 0.95))).z
NECK_Z = joint("neck_01", Vector((0, 0, 1.45))).z
SHOULDER_X = abs(joint("upperarm_l", Vector((0.18, 0, 0))).x)
jacket_id = PARTS.index("Jacket")
cols = []
shell_faces = 0
for poly in me.polygons:
    v = (part[poly.index] + 1) / ID_SCALE
    c = src.matrix_world @ poly.center
    shell = float(part[poly.index] == jacket_id and PELVIS_Z + 0.05 < c.z < NECK_Z - 0.03 and abs(c.x) < SHOULDER_X)
    shell_faces += int(shell)
    cols.extend((v, shell, 0.0, 1.0) * poly.loop_total)
attr.data.foreach_set("color", cols)
log("shell faces (under protector):", shell_faces)

# --- temporary emission material + bake target ---
bake_img = bpy.data.images.new("bake_part_id", W, H, alpha=False, float_buffer=True)
bake_img.colorspace_settings.name = 'Non-Color'
mat = bpy.data.materials.new("TMP_BakePartId")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
n_attr = nt.nodes.new("ShaderNodeVertexColor")
n_attr.layer_name = "bake_part_id"
n_emit = nt.nodes.new("ShaderNodeEmission")
n_out = nt.nodes.new("ShaderNodeOutputMaterial")
n_img = nt.nodes.new("ShaderNodeTexImage")
n_img.image = bake_img
nt.links.new(n_attr.outputs["Color"], n_emit.inputs["Color"])
nt.links.new(n_emit.outputs["Emission"], n_out.inputs["Surface"])
nt.nodes.active = n_img

orig_mats = [m for m in me.materials]
me.materials.clear()
me.materials.append(mat)

scene = bpy.context.scene
orig_engine = scene.render.engine
was_hidden, was_hide_render = src.hide_get(), src.hide_render
try:
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    src.hide_set(False)
    src.hide_render = False
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(o == src)
    bpy.context.view_layer.objects.active = src
    log("bake:", bpy.ops.object.bake(type='EMIT', margin=8, margin_type='EXTEND', use_clear=True))
finally:
    me.materials.clear()
    for m in orig_mats:
        me.materials.append(m)
    bpy.data.materials.remove(mat)
    me.color_attributes.remove(me.color_attributes["bake_part_id"])
    scene.render.engine = orig_engine
    src.hide_set(was_hidden)
    src.hide_render = was_hide_render

baked = np.empty(W * H * 4, dtype=np.float32)
bake_img.pixels.foreach_get(baked)
baked = baked.reshape(H, W, 4)
ids = np.rint(baked[:, :, 0] * ID_SCALE).astype(np.int32) - 1   # -1 = no surface
shell_px = baked[:, :, 1] > 0.5
bpy.data.images.remove(bake_img)

base = np.empty(W * H * 4, dtype=np.float32)
base_img.pixels.foreach_get(base)
base = base.reshape(H, W, 4)
r, g, b = base[:, :, 0], base[:, :, 1], base[:, :, 2]
lum = 0.2126 * r + 0.7152 * g + 0.0722 * b


def ss(x, a, c):
    t = np.clip((x - a) / (c - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


blue = ss(b - np.maximum(r, g), 0.08, 0.25)
dark = 1.0 - ss(lum, 0.12, 0.30)
skin = ss(r - b, 0.05, 0.15) * ss(lum, 0.12, 0.25)


def in_parts(*names):
    """Part membership, requiring 5 of the 3x3 neighbourhood to agree.

    Chart-edge pixels can average two part ids into a third (e.g. Pants+Gloves -> Belt);
    those form 1-2 px lines that fail the neighbourhood vote.
    """
    hit = np.isin(ids, [PARTS.index(n) for n in names]).astype(np.float32)
    padded = np.pad(hit, 1, mode='edge')
    votes = sum(padded[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    return (votes >= 5).astype(np.float32)


collar_dark = 1.0 - ss(lum, 0.35, 0.60)       # black collar vs white jacket cloth

# --- gear-off cleanup: the shirt shell under the protector has the protector's blue trim baked
#     onto its edges. Repaint jacket-owned blue pixels as the jacket's own white cloth, keeping
#     their relative shading, so the dobok reads clean when the protector is removed.
jacket = in_parts("Jacket") > 0.5
cloth = jacket & (lum > 0.6) & (blue < 0.05)
white = np.median(base[:, :, :3][cloth], axis=0) if cloth.any() else np.array([0.92, 0.92, 0.94], dtype=np.float32)
fringe = jacket * ss(b - np.maximum(r, g), 0.02, 0.12)
shade = np.clip(0.75 + 0.35 * np.maximum(r, np.maximum(g, b)), 0.75, 1.05)
repaint = white[None, None, :] * shade[:, :, None]
base[:, :, :3] = base[:, :, :3] * (1 - fringe[:, :, None]) + repaint * fringe[:, :, None]
lum = 0.2126 * base[:, :, 0] + 0.7152 * base[:, :, 1] + 0.0722 * base[:, :, 2]
log("jacket fringe repaint coverage:", round(float((fringe > 0.5).mean()), 4), "cloth white:", [round(float(c), 3) for c in white])

# Dark marks on the shell (protector rim shadows, collar fragments) become plain cloth; the real
# collar around the neck is outside the shell zone and stays black.
shell_dark = (jacket & shell_px).astype(np.float32) * (1.0 - ss(lum, 0.35, 0.65))
shade = np.clip(0.80 + 0.25 * lum, 0.80, 1.0)   # keep a hint of fold shading
repaint = white[None, None, :] * shade[:, :, None]
base[:, :, :3] = base[:, :, :3] * (1 - shell_dark[:, :, None]) + repaint * shell_dark[:, :, None]
lum = 0.2126 * base[:, :, 0] + 0.7152 * base[:, :, 1] + 0.0722 * base[:, :, 2]
log("shell dark repaint coverage:", round(float((shell_dark > 0.5).mean()), 4))

masks = np.zeros((H, W, 4), dtype=np.float32)
masks[:, :, 0] = in_parts("Helmet", "Protector") * blue
masks[:, :, 1] = in_parts("Belt")
masks[:, :, 2] = in_parts("Jacket") * (1.0 - ss(lum, 0.35, 0.60))   # after the repaints above
masks[:, :, 3] = in_parts("Head", "BodySkin") * skin

coverage = {n: float((ids == i).mean()) for i, n in enumerate(PARTS)}
log("uv coverage by part:", {k: round(v, 4) for k, v in coverage.items()}, "empty:", round(float((ids < 0).mean()), 4))
log("mask coverage R/G/B/A:", [round(float((masks[:, :, c] > 0.5).mean()), 4) for c in range(4)])


def save(name, arr, non_color):
    img = bpy.data.images.get(name) or bpy.data.images.new(name, W, H, alpha=True)
    if img.size[0] != W:
        img.scale(W, H)
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    img.alpha_mode = 'CHANNEL_PACKED'   # alpha is a mask, not transparency: keep RGB untouched
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.update()                        # refresh the GPU copy so the viewport shows the new pixels
    path = os.path.join(tex_dir, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    # reload from disk so the in-memory/GPU copy matches the file exactly, then pack it into the .blend
    img.filepath = path
    img.reload()
    img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    img.alpha_mode = 'CHANNEL_PACKED'
    img.pack()
    log("saved", path)
    return img


save("T_Fighter_BaseColor", base, non_color=False)
save("T_Fighter_Masks", masks, non_color=True)
log.close()
