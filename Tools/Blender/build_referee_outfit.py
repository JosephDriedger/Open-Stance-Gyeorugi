"""Referee uniform (Resources/Images/Referee_Ref.png) built on a referee MetaHuman body.

    run("build_referee_outfit", REFEREE="Kelvin")
    for p in ["Kelvin", "Bo", "Jorge", "Omari", "Walter", "Vivian"]: run("build_referee_outfit", REFEREE=p)

Needs Resources/Models/MetaHuman/MH_Referee_<P>_Body.fbx (Tools/Unreal/create_referee.py). Works in a
separate "Referee_<P>" scene. Garments are grown from the body surface, so they fit this body exactly and
are skinned to the MetaHuman body skeleton like the fighter gear:

  SK_Referee_Shirt     light-blue long-sleeve dress shirt with collar and chest pocket
  SK_Referee_Tie       navy tie
  SK_Referee_Trousers  beige trousers
  SK_Referee_Belt      brown leather belt with buckle
  SK_Referee_Shoes     white sneakers

Exports Resources/Models/Referee/<P>/SK_Referee_<Part>.fbx (centimetres, armature "root"), then bakes
body hidden face maps (T_HFM_Shirt/Trousers/Shoes.png) with hidden_face_maps.py.
"""
import math
import os

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import rig_config as cfg

REFEREE = globals().get("REFEREE", "Kelvin")
log = cfg.open_log(f"build_referee_outfit_{REFEREE}")
MH_DIR = os.path.join(cfg.OUTPUT_DIR, "MetaHuman")
OUT_DIR = os.path.join(cfg.OUTPUT_DIR, "Referee", REFEREE)
os.makedirs(OUT_DIR, exist_ok=True)
BODY_NAME = f"MH_Referee_{REFEREE}_Body"
BODY_FBX = os.path.join(MH_DIR, f"{BODY_NAME}.fbx")
COLL = f"Referee_{REFEREE}"

previous_scene = bpy.context.window.scene
scene = bpy.data.scenes.get(COLL) or bpy.data.scenes.new(COLL)
bpy.context.window.scene = scene
for o in list(scene.collection.objects):
    bpy.data.objects.remove(o, do_unlink=True)
coll = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
if coll.name not in scene.collection.children:
    scene.collection.children.link(coll)
for o in list(coll.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=BODY_FBX, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
new = [o for o in bpy.data.objects if o not in before]
arm = next(o for o in new if o.type == 'ARMATURE')
body = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
body.name = BODY_NAME
log("armature", arm.name, "body", body.name, len(body.data.vertices))


def J(name):
    return arm.matrix_world @ arm.data.bones[name].head_local


PELVIS, NECK, HEAD = J("pelvis"), J("neck_01"), J("head")
FOOT_L, FOOT_R = J("foot_l"), J("foot_r")
HAND_L, HAND_R = J("hand_l"), J("hand_r")
LOWER_L, LOWER_R = J("lowerarm_l"), J("lowerarm_r")
WAIST_Z = PELVIS.z + 0.07
ANKLE_Z = (FOOT_L.z + FOOT_R.z) / 2
log("pelvis", tuple(round(c, 3) for c in PELVIS), "neck", tuple(round(c, 3) for c in NECK), "waist z", round(WAIST_Z, 3),
    "ankle z", round(ANKLE_Z, 3))

# body in world space, evaluated rest pose
dg = bpy.context.evaluated_depsgraph_get()
body_bm = bmesh.new()
body_bm.from_object(body, dg)
body_bm.transform(body.matrix_world)
body_bm.normal_update()
body_bm.verts.ensure_lookup_table()
body_bm.faces.ensure_lookup_table()
gnames = {g.index: g.name for g in body.vertex_groups}
dominant = []
for v in body.data.vertices:
    g = max(v.groups, key=lambda g: g.weight, default=None)
    dominant.append(gnames[g.group] if g else "pelvis")


def along(p, a, b):
    ab = b - a
    return (p - a).dot(ab) / ab.length_squared


def region(face):
    """Which garment covers a body face (by dominant bone and height)."""
    c = face.calc_center_median()
    bones = [dominant[v.index] for v in face.verts]
    bone = max(set(bones), key=bones.count)
    side = bone[-2:] if bone.endswith(("_l", "_r")) else ""
    out = set()
    if bone.startswith(("foot", "ball")) or "toe" in bone or (bone.startswith("calf") and c.z < ANKLE_Z + 0.05):
        out.add("Shoes")
    if bone.startswith(("thigh", "calf")) and c.z > ANKLE_Z + 0.015:
        out.add("Trousers")
    if bone.startswith(("pelvis", "spine_01", "spine_02")) and c.z < WAIST_Z + 0.015:
        out.add("Trousers")
    if bone.startswith(("spine", "clavicle", "upperarm")) and c.z > WAIST_Z - 0.07:
        out.add("Shirt")
    if bone.startswith("pelvis") and c.z > WAIST_Z - 0.07:
        out.add("Shirt")
    if bone.startswith("neck") and c.z < NECK.z + 0.02:
        out.add("Shirt")   # a buttoned dress-shirt collar sits on the base of the neck
    if bone.startswith("lowerarm"):
        hand, lower = (HAND_L, LOWER_L) if side == "_l" else (HAND_R, LOWER_R)
        if along(c, lower, hand) < 0.96:
            out.add("Shirt")
    if bone.startswith(("pelvis", "spine_01", "spine_02")) and abs(c.z - WAIST_Z) < 0.022:
        out.add("Belt")
    return out


GARMENTS = {
    # offset from skin (m), extra torso looseness, smoothing iterations, material
    "Shirt":    dict(offset=0.010, loose=0.012, smooth=4, mat="MI_RefShirt"),
    "Trousers": dict(offset=0.016, loose=0.010, smooth=4, mat="MI_RefTrousers"),
    "Belt":     dict(offset=0.026, loose=0.012, smooth=2, mat="MI_RefBelt"),
    "Shoes":    dict(offset=0.020, loose=0.0, smooth=3, mat="MI_RefShoe"),
}

face_regions = [region(f) for f in body_bm.faces]
body_bvh = BVHTree.FromBMesh(body_bm)
objects = {}
PREVIEW_COLOURS = {   # Blender viewport only; Unreal colours are set in import_referee_outfit.py
    "MI_RefShirt": (0.55, 0.68, 0.9), "MI_RefTie": (0.03, 0.06, 0.2), "MI_RefTrousers": (0.72, 0.68, 0.58),
    "MI_RefBelt": (0.25, 0.12, 0.05), "MI_RefBuckle": (0.7, 0.7, 0.7), "MI_RefShoe": (0.95, 0.95, 0.95),
    "MI_RefSole": (0.85, 0.85, 0.85),
}
for name, rgb in PREVIEW_COLOURS.items():
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)


def spine_axis_point(p):
    a, b = PELVIS, NECK
    t = max(0.0, min(1.0, along(p, a, b)))
    return a + (b - a) * t


for gname, s in GARMENTS.items():
    bm = body_bm.copy()
    orig = bm.verts.layers.int.new("orig")
    for i, v in enumerate(bm.verts):
        v[orig] = i
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for i, f in enumerate(bm.faces) if gname not in face_regions[i]], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # the exported body is split along UV seams; weld so offsetting doesn't open cracks there
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bm.normal_update()
    # offset along the skin normal; the torso gets extra room (shirt and trouser seat aren't skin-tight)
    moves = []
    for v in bm.verts:
        d = v.normal * s["offset"]
        if s["loose"]:
            axis = spine_axis_point(v.co)
            radial = Vector((v.co.x - axis.x, v.co.y - axis.y, 0))
            if radial.length > 1e-4 and PELVIS.z - 0.25 < v.co.z < NECK.z - 0.04:
                d += radial.normalized() * s["loose"]
        moves.append(d)
    for v, d in zip(bm.verts, moves):
        v.co += d
    # straight-cut legs and relaxed sleeves: keep a minimum distance from the limb axis
    if gname in ("Trousers", "Shirt"):
        for v in bm.verts:
            bone = dominant[v[orig]]
            side = bone[-2:] if bone.endswith(("_l", "_r")) else ""
            if not side:
                continue
            if gname == "Trousers" and bone.startswith(("thigh", "calf")):
                a, b_, r_min = J(f"thigh{side}"), J(f"foot{side}"), 0.088
            elif gname == "Shirt" and bone.startswith("upperarm"):
                a, b_, r_min = J(f"upperarm{side}"), J(f"lowerarm{side}"), 0.058
            elif gname == "Shirt" and bone.startswith("lowerarm"):
                a, b_, r_min = J(f"lowerarm{side}"), J(f"hand{side}"), 0.046
            else:
                continue
            t = max(0.0, min(1.0, along(v.co, a, b_)))
            q = a + (b_ - a) * t
            radial = v.co - q
            radial -= (b_ - a).normalized() * radial.dot((b_ - a).normalized())
            if gname == "Trousers" and t < 0.35:
                continue   # hips and upper thigh keep their shape
            if gname == "Shirt" and bone.startswith("upperarm") and t < 0.25:
                continue   # shoulder/armpit keep their shape
            if 1e-4 < radial.length < r_min:
                v.co = q + radial.normalized() * r_min
    for _ in range(s["smooth"]):
        bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    if gname == "Shoes":
        # sneaker toe box: toe-region vertices go onto the convex hull of that foot's toes (no toe crevices)
        for side in ("_l", "_r"):
            pts = [body_bm.verts[i].co.copy() for i, b_ in enumerate(dominant)
                   if b_.endswith(side) and ("toe" in b_ or b_.startswith("ball"))]
            if len(pts) < 8:
                continue
            hb = bmesh.new()
            for p in pts:
                hb.verts.new(p)
            hull = bmesh.ops.convex_hull(hb, input=list(hb.verts))
            inside = {g for g in hull["geom_interior"] + hull["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
            bmesh.ops.delete(hb, geom=list(inside), context='VERTS')
            hb.normal_update()
            hull_bvh = BVHTree.FromBMesh(hb)
            for v in bm.verts:
                b_ = dominant[v[orig]]
                if b_.endswith(side) and ("toe" in b_ or b_.startswith("ball")):
                    p, n, _i, _d = hull_bvh.find_nearest(v.co)
                    if p is not None:
                        v.co = p + n * s["offset"]
            hb.free()
        for _ in range(2):
            bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
            toe = max(0.0, -(v.co.y - (FOOT_L.y + FOOT_R.y) / 2) - 0.05)
            v.co.y -= toe * 0.15                      # slightly longer toe box
        sole_idx = 1
    me = bpy.data.meshes.new(f"SK_Referee_{gname}")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(me.name, me)
    coll.objects.link(obj)
    me.materials.append(bpy.data.materials.get(s["mat"]) or bpy.data.materials.new(s["mat"]))
    if gname == "Shoes":
        me.materials.append(bpy.data.materials.get("MI_RefSole") or bpy.data.materials.new("MI_RefSole"))
        for p in me.polygons:
            if p.center.z < 0.025:
                p.material_index = 1
    objects[gname] = obj
    log(gname, "verts", len(me.vertices), "faces", len(me.polygons))

# --- shirt details: stand collar at the neck opening, chest pocket --------------------------------
shirt = objects["Shirt"]
bm = bmesh.new()
bm.from_mesh(shirt.data)
bm.verts.ensure_lookup_table()
def horiz(v_co):
    return Vector((v_co.x - NECK.x, v_co.y - NECK.y, 0))


# neck opening = boundary edges close to the neck axis (sleeve cuffs and the hem are far from it)
neck_edges = [e for e in bm.edges if e.is_boundary
              and all(horiz(v.co).length < 0.2 and v.co.z > NECK.z - 0.22 for v in e.verts)]
COLLAR_Z = NECK.z - 0.03          # where the collar band starts (dips 2 cm at the front)
if neck_edges:
    # ring 1 closes the (often wide) body opening in to the collar line around the neck
    ext = bmesh.ops.extrude_edge_only(bm, edges=neck_edges)
    ring1 = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    ring1_edges = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMEdge)
                   and all(v in set(ring1) for v in g.verts)]
    for v in ring1:
        d = horiz(v.co)
        d = d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))
        front = max(0.0, -d.y)
        v.co = Vector((NECK.x, NECK.y, 0)) + d * 0.084 + Vector((0, 0, COLLAR_Z - 0.02 * front))
    # ring 2 is the collar band itself, standing up around the neck
    ext2 = bmesh.ops.extrude_edge_only(bm, edges=ring1_edges)
    ring2 = [g for g in ext2["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in ring2:
        d = horiz(v.co)
        d = d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))
        v.co = Vector((NECK.x, NECK.y, v.co.z + 0.038)) + d * 0.078
    bm.normal_update()
    log("collar verts", len(ring1) + len(ring2))
bm.to_mesh(shirt.data)
bm.free()
shirt_bvh = BVHTree.FromObject(shirt, bpy.context.evaluated_depsgraph_get())

pocket_mat = len(shirt.data.materials)
shirt.data.materials.append(bpy.data.materials["MI_RefShirt"])


def surface_point(x, z, from_front=True):
    origin = Vector((x, -1.0, z))
    hit = shirt_bvh.ray_cast(origin, Vector((0, 1, 0)), 2.0)
    if hit[0] is None:
        # centre seam / collar opening: fall back to the nearest shirt point in front of the body
        hit = shirt_bvh.find_nearest(Vector((x, -0.4, z)))
    return hit[0], hit[1]


def add_patch(obj, x0, x1, z0, z1, lift, mat_index, nx=6, nz=6, max_depth=None):
    """Grid patch following the shirt front surface, lifted `lift` m (pocket, placket)."""
    me = obj.data
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    grid = []
    for iz in range(nz + 1):
        row = []
        for ix in range(nx + 1):
            x = x0 + (x1 - x0) * ix / nx
            z = z0 + (z1 - z0) * iz / nz
            p, n = surface_point(x, z)
            if p is None:
                bm2.free()
                return False
            row.append(bm2.verts.new(p + n * lift))
        grid.append(row)
    depth = [v.co.y for row in grid for v in row]
    log("patch depth range", round(max(depth) - min(depth), 3), "limit", max_depth)
    if max_depth is not None and max(depth) - min(depth) > max_depth:
        bm2.free()      # too curved for a flat patch (e.g. a pocket over a bust): leave it off
        return False
    for iz in range(nz):
        for ix in range(nx):
            # x to the viewer's right, z up: this order is counter-clockwise from the front, so it faces out
            f = bm2.faces.new([grid[iz][ix], grid[iz][ix + 1], grid[iz + 1][ix + 1], grid[iz + 1][ix]])
            f.material_index = mat_index
            f.smooth = True
    bm2.to_mesh(me)
    bm2.free()
    return True


chest_z = NECK.z - 0.17
ok_pocket = add_patch(shirt, 0.04, 0.14, chest_z - 0.12, chest_z, 0.007, pocket_mat, max_depth=0.09)   # flat chests measure ~7 cm, a bust ~12 cm
ok_placket = add_patch(shirt, -0.016, 0.016, WAIST_Z - 0.04, COLLAR_Z - 0.05, 0.005, pocket_mat, nx=2, nz=16,
                       max_depth=0.18)   # mostly hidden by the tie
log("pocket", ok_pocket, "placket", ok_placket)

# --- tie: follows the shirt front from the collar to just above the belt -----------------------------
tie_me = bpy.data.meshes.new("SK_Referee_Tie")
tbm = bmesh.new()
top_z, tip_z = COLLAR_Z - 0.03, WAIST_Z + 0.05
steps = 24
left, right = [], []
tie_top = None
for i in range(steps + 1):
    t = i / steps
    z = top_z + (tip_z - top_z) * t
    w = 0.036 + (0.086 - 0.036) * min(1.0, t * 1.15)
    # direct hits only (keeps it centred); the whole width must clear the shirt, not just the centre line
    hits = [shirt_bvh.ray_cast(Vector((hx, -1.0, z)), Vector((0, 1, 0)), 2.0)[0] for hx in (-w / 2 - 0.005, 0.0, w / 2 + 0.005)]
    if hits[1] is None:
        continue
    y = min(h.y for h in hits if h is not None) - 0.009
    if left:
        # a tie hangs: it never tucks back in behind the chest, only eases back 15 cm per metre of drop
        prev_y, prev_z = left[-1].co.y, left[-1].co.z
        y = min(y, prev_y + (prev_z - z) * 0.15)
    c = Vector((0.0, y, z))
    if tie_top is None:
        tie_top = c
    left.append(tbm.verts.new(c + Vector((-w / 2, 0, 0))))
    right.append(tbm.verts.new(c + Vector((w / 2, 0, 0))))
tip = tbm.verts.new(Vector((0.0, left[-1].co.y, tip_z - 0.045)))
for i in range(len(left) - 1):
    # top-left, bottom-left, bottom-right, top-right: counter-clockwise from the front
    tbm.faces.new([left[i], left[i + 1], right[i + 1], right[i]])
tbm.faces.new([left[-1], tip, right[-1]])
tbm.normal_update()
front = list(tbm.faces)
ext = bmesh.ops.extrude_face_region(tbm, geom=front)
bmesh.ops.translate(tbm, vec=(0, 0.004, 0), verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
bmesh.ops.recalc_face_normals(tbm, faces=tbm.faces)
# knot
kp = tie_top + Vector((0, -0.004, 0.022))   # knot sits at the top of the tie, in the collar's V
knot = bmesh.ops.create_cube(tbm, size=1.0)
for v in knot["verts"]:
    taper = 0.046 if v.co.z > 0 else 0.03          # wider at the top, like a four-in-hand knot
    v.co = Vector((v.co.x * taper, v.co.y * 0.024, v.co.z * 0.045)) + kp
tbm.to_mesh(tie_me)
tbm.free()
tie = bpy.data.objects.new("SK_Referee_Tie", tie_me)
coll.objects.link(tie)
tie_me.materials.append(bpy.data.materials.get("MI_RefTie") or bpy.data.materials.new("MI_RefTie"))
objects["Tie"] = tie

# --- belt buckle ------------------------------------------------------------------------------------
belt = objects["Belt"]
bp, bn = surface_point(0.0, WAIST_Z)
if bp is not None:
    bbm = bmesh.new()
    bbm.from_mesh(belt.data)
    cube = bmesh.ops.create_cube(bbm, size=1.0)
    for v in cube["verts"]:
        v.co = Vector((v.co.x * 0.05, v.co.y * 0.008, v.co.z * 0.038)) + bp + Vector((0, -0.022, 0))
    if "MI_RefBuckle" not in belt.data.materials:
        belt.data.materials.append(bpy.data.materials.get("MI_RefBuckle") or bpy.data.materials.new("MI_RefBuckle"))
    idx = len(belt.data.materials) - 1
    for f in {f for v in cube["verts"] for f in v.link_faces}:
        f.material_index = idx
    bbm.to_mesh(belt.data)
    bbm.free()

# --- weights: copied from the body, rigid-ish rules for tie and belt, smoothed ---------------------
PARENTS = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
ALLOWED = {
    "Tie": {"spine_03", "spine_04", "spine_05", "neck_01"},
    "Belt": {"pelvis", "spine_01", "spine_02"},
}
SMOOTH = {"Shirt": 6, "Trousers": 4, "Belt": 10, "Tie": 20, "Shoes": 2}


def remap(w, allowed):
    out = {}
    for bone, val in w.items():
        b = bone
        while b is not None and b not in allowed:
            b = PARENTS.get(b)
        if b is not None:
            out[b] = out.get(b, 0.0) + val
    return out


for gname, obj in objects.items():
    for o in bpy.context.view_layer.objects:
        o.select_set(o == obj)
    bpy.context.view_layer.objects.active = obj
    dt = obj.modifiers.new("WeightTransfer", 'DATA_TRANSFER')
    dt.object = body
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    W = [{names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in me.vertices]
    if gname in ALLOWED:
        W = [remap(w, ALLOWED[gname]) or {"spine_05" if gname == "Tie" else "pelvis": 1.0} for w in W]
    nbrs = [[] for _ in me.vertices]
    for e in me.edges:
        a, b_ = e.vertices
        nbrs[a].append(b_)
        nbrs[b_].append(a)
    for _ in range(SMOOTH[gname]):
        nxt = []
        for i, w in enumerate(W):
            if not nbrs[i]:
                nxt.append(w)
                continue
            acc = {k: v * 0.5 for k, v in w.items()}
            f = 0.5 / len(nbrs[i])
            for j in nbrs[i]:
                for k, v in W[j].items():
                    acc[k] = acc.get(k, 0.0) + v * f
            nxt.append(acc)
        W = nxt
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        keep = sorted(((k, v) for k, v in w.items() if v >= 0.02), key=lambda t: -t[1])[:4]
        total = sum(v for _, v in keep) or 1.0
        for k, v in keep:
            if k not in groups:
                groups[k] = obj.vertex_groups.new(name=k)
            groups[k].add([i], v / total, 'REPLACE')
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    log(gname, "weights", len(groups))

# --- export ------------------------------------------------------------------------------------------
original = arm.name
clash = bpy.data.objects.get("root")
if clash and clash != arm:
    clash.name = "root_tmp_referee"
arm.name = "root"
for gname, obj in objects.items():
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (arm, obj))
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(OUT_DIR, f"SK_Referee_{gname}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=False, add_leaf_bones=False,
        primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
        armature_nodetype='NULL', bake_anim=False, path_mode='STRIP')
    log("exported", path)
arm.name = original
if clash and clash.name == "root_tmp_referee":
    clash.name = "root"

# --- body hidden face maps for the pieces that cover skin -------------------------------------------
hfm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hidden_face_maps.py")
exec(compile(open(hfm_path, encoding="utf-8").read(), hfm_path, "exec"), {
    "__name__": "__main__", "__file__": hfm_path,
    "TARGET_NAME": BODY_NAME, "COLLECTION": COLL, "OUT_DIR": OUT_DIR, "PART_PREFIX": "SK_Referee_",
    "PART_SETTINGS": {"Shirt": dict(max_gap=0.08, erode=3), "Trousers": dict(max_gap=0.12, erode=3),
                      "Shoes": dict(max_gap=0.05, erode=1)},
})
log("hidden face maps baked")
log("DONE")
log.close()
bpy.context.window.scene = previous_scene
