"""Pass 1 of the part split: classify faces by texture colour and over-segment the mesh.

Faces are grown into patches across edges that are both smooth (dihedral below
CREASE_DEG) and colour-consistent. Results are stored as face attributes
("colour_class", "patch") and visualised as face-corner colour attributes
("viz_colour", "viz_patch") for checking in Solid shading.
"""
import math
import random

import bmesh
import bpy
import numpy as np
import rig_config as cfg

log = cfg.open_log("segment_parts")

CREASE_DEG = 55.0
CLASSES = ["white", "grey", "black", "blue", "skin"]
CLASS_VIZ = {
    "white": (0.95, 0.95, 0.95),
    "grey": (0.5, 0.5, 0.5),
    "black": (0.05, 0.05, 0.05),
    "blue": (0.1, 0.25, 0.9),
    "skin": (0.95, 0.55, 0.35),
}

mesh = bpy.data.objects[cfg.MESH_NAME]
me = mesh.data
img = next(n.image for m in me.materials if m and m.node_tree
           for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
W, H = img.size
px = np.empty(W * H * 4, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(H, W, 4)[:, :, :3]
log("texture", img.name, W, H)


def classify(rgb):
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = (mx - mn) / mx if mx > 1e-4 else 0.0
    if b > r + 0.12 and b > g + 0.05 and sat > 0.35:
        return "blue"
    if r > g > b and (r - b) > 0.10 and sat > 0.18 and lum > 0.15:
        return "skin"
    if lum < 0.12:
        return "black"
    if lum < 0.55 or sat > 0.15:
        return "grey"
    return "white"


def sample(u, v):
    x = min(W - 1, max(0, int(u * W)))
    y = min(H - 1, max(0, int(v * H)))
    return px[y, x]


bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
uv = bm.loops.layers.uv.active

face_class = []
for f in bm.faces:
    uvs = [l[uv].uv for l in f.loops]
    cu = sum(t.x for t in uvs) / len(uvs)
    cv = sum(t.y for t in uvs) / len(uvs)
    # centroid plus points pulled 2/3 toward it from each corner (avoids chart-edge bleed)
    pts = [(cu, cv)] + [(cu + (t.x - cu) / 3, cv + (t.y - cv) / 3) for t in uvs]
    votes = {}
    for u, v in pts:
        c = classify(sample(u, v))
        votes[c] = votes.get(c, 0) + 1
    face_class.append(max(votes.items(), key=lambda kv: (kv[1], kv[0] == classify(sample(cu, cv))))[0])

counts = {c: face_class.count(c) for c in CLASSES}
log("face colour classes:", counts)

# --- patch growing ---
crease = math.radians(CREASE_DEG)
patch = [-1] * len(bm.faces)
n_patches = 0
for f in bm.faces:
    if patch[f.index] >= 0:
        continue
    stack = [f]
    patch[f.index] = n_patches
    while stack:
        a = stack.pop()
        for e in a.edges:
            if len(e.link_faces) != 2:
                continue
            b = e.link_faces[0] if e.link_faces[1] is a else e.link_faces[1]
            if patch[b.index] >= 0:
                continue
            if face_class[b.index] != face_class[a.index]:
                continue
            if a.normal.angle(b.normal, 0.0) > crease:
                continue
            patch[b.index] = n_patches
            stack.append(b)
    n_patches += 1

sizes = {}
for p in patch:
    sizes[p] = sizes.get(p, 0) + 1
big = sorted(sizes.values(), reverse=True)
log("patches:", n_patches, "largest:", big[:20], "single-face patches:", sum(1 for s in big if s == 1))
bm.free()

# --- store attributes ---
for name in ("colour_class", "patch"):
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
a_cls = me.attributes.new("colour_class", 'INT', 'FACE')
a_cls.data.foreach_set("value", [CLASSES.index(c) for c in face_class])
a_patch = me.attributes.new("patch", 'INT', 'FACE')
a_patch.data.foreach_set("value", patch)

rng = random.Random(7)
patch_col = [(rng.random(), rng.random(), rng.random()) for _ in range(n_patches)]
for name in ("viz_colour", "viz_patch"):
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
viz_c = me.color_attributes.new("viz_colour", 'BYTE_COLOR', 'CORNER')
viz_p = me.color_attributes.new("viz_patch", 'BYTE_COLOR', 'CORNER')
col_c = []
col_p = []
for poly in me.polygons:
    cc = CLASS_VIZ[face_class[poly.index]] + (1.0,)
    pc = patch_col[patch[poly.index]] + (1.0,)
    for _ in range(poly.loop_total):
        col_c.extend(cc)
        col_p.extend(pc)
viz_c.data.foreach_set("color", col_c)
viz_p.data.foreach_set("color", col_p)
log.close()
