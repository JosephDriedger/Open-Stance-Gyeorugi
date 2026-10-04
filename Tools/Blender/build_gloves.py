"""Build the sparring gloves from the target body's own hand surface (used by fit_to_body.py).

The Meshy gloves are jagged shells whose triangles fold and spike when the hand closes into a fist
(the guard, every punch). These are carved from the MetaHuman body instead: each glove vertex is a
body vertex pushed out along its normal, so the glove has the body's topology and takes the body's
skin weights unchanged. It deforms exactly like the hand underneath, with no folds or spikes.

Coverage per hand: the palm and back of the hand (hand, metacarpal and thumb-base bones) plus a
wrist cuff running CUFF_LENGTH up the forearm. Fingers stay bare (fingerless sparring glove).
Textures: the hand part samples the atlas's white vinyl patch and the cuff its black trim patch
(Tools/Blender/make_gear_textures.py; no mask, so no side recolour).

    rebuild(glove_obj, body_obj, log)   replaces glove_obj's mesh and weights in place
"""
import bmesh
import bpy
import numpy as np
from mathutils import Vector

HAND_BONES = ("hand", "thumb_01", "index_metacarpal", "middle_metacarpal", "ring_metacarpal", "pinky_metacarpal")
CUFF_LENGTH = 0.085        # m up the forearm from the wrist joint
CUFF_RADIUS = 0.07         # m from the forearm axis (keeps the torso out)
KNUCKLE_REACH = 0.03       # m past the knuckle line that the glove covers
HAND_RADIUS = 0.075        # m from the wrist-to-knuckle axis
MIN_PIECE_FACES = 150      # smaller connected pieces are noise
FINGER_BASES = ("index_01", "middle_01", "ring_01", "pinky_01")
HAND_THICKNESS = 0.0055    # m of padding over the skin
CUFF_THICKNESS = 0.0045
UV_WHITE = (0.375, 0.625)    # 'vinyl' patch of the make_gear_textures.py atlas
UV_BLACK = (0.875, 0.875)    # 'trim' patch (black neoprene cuff)
MAX_INFLUENCES = 8


def _weights(body):
    me = body.data
    names = [g.name for g in body.vertex_groups]
    W = np.zeros((len(me.vertices), len(names)))
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def _smooth_region(mask, nbrs, passes):
    """Majority filter: drops single-vertex spurs and fills pinholes along the region's edge."""
    for _ in range(passes):
        nxt = mask.copy()
        for i, ns in enumerate(nbrs):
            if not ns:
                continue
            votes = sum(mask[j] for j in ns) + mask[i]
            nxt[i] = votes * 2 > len(ns) + 1
        mask = nxt
    return mask


def rebuild(glove, body, log):
    names, W = _weights(body)
    col = {n: i for i, n in enumerate(names)}
    mw = body.matrix_world

    bm = bmesh.new()
    bm.from_object(body, bpy.context.evaluated_depsgraph_get())
    bm.transform(mw)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    co = np.array([v.co[:] for v in bm.verts])
    normals = np.array([v.normal[:] for v in bm.verts])
    nbrs = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    # The body splits vertices along UV seams; give coincident vertices one shared normal and one
    # neighbourhood so the offset glove doesn't crack open along the seam.
    keys = [tuple(k) for k in np.round(co * 1e5).astype(np.int64)]
    twins = {}
    for i, k in enumerate(keys):
        twins.setdefault(k, []).append(i)
    for group in twins.values():
        if len(group) > 1:
            avg = normals[group].sum(0)
            avg /= np.linalg.norm(avg) or 1.0
            normals[group] = avg
            merged = sorted({j for i in group for j in nbrs[i]} | set(group))
            for i in group:
                nbrs[i] = [j for j in merged if j != i]

    # joint positions in world space
    arm = body.find_armature() or body.parent
    joints = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}

    region = np.zeros(n, bool)
    cuff_face_t = {}
    t_axis = np.zeros(n)
    for s, sign in (("l", 1), ("r", -1)):
        hand_cols = [col[f"{b}_{s}"] for b in HAND_BONES if f"{b}_{s}" in col]
        wrist = joints[f"hand_{s}"]
        axis = (wrist - joints[f"lowerarm_{s}"]).normalized()
        a = np.array(axis[:])
        rel = co - np.array(wrist[:])
        t = rel @ (-a)                                  # +: up the forearm from the wrist
        radial = np.linalg.norm(rel - np.outer(rel @ a, a), axis=1)
        on_side = (co[:, 0] * sign) > 0
        # Hand: skin weights say what is hand, but they blend raggedly at the finger bases, so the
        # far edge is a flat cut KNUCKLE_REACH past the knuckle line (the four finger base joints).
        bases = [np.array(joints[f"{b}_{s}"][:]) for b in FINGER_BASES if f"{b}_{s}" in joints]
        knuckles = np.mean(bases, axis=0)
        u = knuckles - np.array(wrist[:])
        reach = np.linalg.norm(u)
        u /= reach
        along = rel @ u
        across = np.linalg.norm(rel - np.outer(along, u), axis=1)
        cover_cols = hand_cols + [col[f"{b}_{s}"] for b in FINGER_BASES if f"{b}_{s}" in col]
        hand = ((W[:, cover_cols].sum(1) > 0.3) & on_side & (along > -0.01)
                & (along < reach + KNUCKLE_REACH) & (across < HAND_RADIUS))
        cuff = on_side & (t > -0.015) & (t < CUFF_LENGTH) & (radial < CUFF_RADIUS)
        region |= hand | cuff
        t_axis = np.where(on_side, t, t_axis)
    region = _smooth_region(region, nbrs, 4)

    # faces fully inside the region; stray islands are dropped
    faces = [f for f in bm.faces if all(region[v.index] for v in f.verts)]
    parent = list(range(len(bm.faces)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    inside = {f.index for f in faces}
    for f in faces:
        for e in f.edges:
            for g in e.link_faces:
                if g.index in inside:
                    parent[find(f.index)] = find(g.index)
    sizes = {}
    for f in faces:
        sizes[find(f.index)] = sizes.get(find(f.index), 0) + 1
    keep_roots = {r for r, size in sizes.items() if size >= MIN_PIECE_FACES}   # drops stray islands
    faces = [f for f in faces if find(f.index) in keep_roots]
    used = sorted({v.index for f in faces for v in f.verts})
    new_index = {old: i for i, old in enumerate(used)}
    log("gloves: body hand/cuff vertices", int(region.sum()), "-> glove", len(used), "vertices", len(faces), "faces")

    # offset: thicker over the hand, thinner at the cuff, blended across the wrist
    thick = np.where(t_axis > 0.0, CUFF_THICKNESS, HAND_THICKNESS)
    pos = co + normals * thick[:, None]

    out = bmesh.new()
    vmap = {old: out.verts.new(Vector(pos[old])) for old in used}
    uv_layer = out.loops.layers.uv.new("UVMap")
    for f in faces:
        nf = out.faces.new([vmap[v.index] for v in f.verts])
        nf.smooth = True
        centre_t = float(np.mean([t_axis[v.index] for v in f.verts]))
        u, v = UV_BLACK if centre_t > 0.0 else UV_WHITE
        for loop in nf.loops:
            loop[uv_layer].uv = (u, v)
    out.normal_update()

    # glove-local space; keep the material slots the importer expects
    mats = list(glove.data.materials)
    out.transform(glove.matrix_world.inverted())
    glove.data.clear_geometry()
    out.to_mesh(glove.data)
    out.free()
    bm.free()
    glove.data.materials.clear()
    for m in mats or [None]:
        glove.data.materials.append(m)
    for p in glove.data.polygons:
        p.material_index = 0

    # weights straight from the body vertices
    glove.vertex_groups.clear()
    groups = {}
    for old in used:
        w = W[old]
        top = np.argsort(-w)[:MAX_INFLUENCES]
        top = [j for j in top if w[j] > 0.01]
        total = float(sum(w[j] for j in top)) or 1.0
        for j in top:
            if j not in groups:
                groups[j] = glove.vertex_groups.new(name=names[j])
            groups[j].add([new_index[old]], float(w[j]) / total, 'REPLACE')
    log("gloves: weights from body,", len(groups), "bone groups")
