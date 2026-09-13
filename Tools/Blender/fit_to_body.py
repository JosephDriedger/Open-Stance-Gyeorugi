"""Refit the fighter's dobok and gear onto another body (e.g. a MetaHuman export).

Run in a scene that already contains the split parts (run("pipeline") or open
Fighter_Rigged.blend), then:

    run("fit_to_body",
        TARGET_FBX=r"D:/Open-Stance-Gyeorugi/Resources/Models/MetaHuman/MH_FighterBase_Body.fbx",
        TARGET_HEAD_FBX=r"D:/Open-Stance-Gyeorugi/Resources/Models/MetaHuman/MH_FighterBase_Head.fbx")

Steps
1. Import the target body and head (keeping leaf bones: "head" is a leaf in the body skeleton).
   Joints missing from the body skeleton are taken from the head skeleton.
2. Pose our skeleton so each shared joint sits on the target's joint and points at the target's
   child joint (length-stretched). Rigid gear (protector, belt, helmet) only follows torso/head
   bones during this step, so leg and arm poses don't drag it.
3. Bake each part's posed shape.
4. Radial fit, repeated for several passes: for every vertex, cast a ray from the axis of the bone
   it belongs to (thigh, calf, spine, head centre...) out through the vertex, find the body
   surface along that ray, and move the vertex so it sits at least `clearance` outside it.
   Measuring from bone axes works on open meshes (MetaHuman bodies have no head, so
   inside/outside tests from normals are unreliable). Corrections are smoothed over the mesh;
   rigid parts smooth much harder so they inflate evenly instead of denting.
   The shirt shell that sat under the chest protector is also pulled in to hug the torso, so
   the jacket reads as a dobok when the protector is off.
5. Weights copied from the target body; the helmet is rigid on the head skeleton's head bone.
6. Export to <output>/Fitted/<TargetName>/SK_Fighter_<Part>.fbx (helmet on the head skeleton).
"""
import os

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import rig_config as cfg

log = cfg.open_log("fit_to_body")

FIT_PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
PART_SETTINGS = {
    # clearance: minimum gap outside the skin (m); smooth: correction smoothing iterations
    "Jacket":     dict(clearance=0.012, smooth=10),
    "Pants":      dict(clearance=0.015, smooth=10),
    "Belt":       dict(clearance=0.030, smooth=30),
    "Protector":  dict(clearance=0.030, smooth=40),
    "Helmet":     dict(clearance=0.006, smooth=60),
    "Gloves":     dict(clearance=0.003, smooth=6),
    "FootGuards": dict(clearance=0.004, smooth=6),
}
# Bones a rigid part may follow while being posed onto the target body.
TORSO = {"root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05"}
RIGID_BONES = {
    "Protector": TORSO | {"clavicle_l", "clavicle_r"},
    "Belt": {"root", "pelvis", "spine_01", "spine_02"},
    "Helmet": {"head"},
}
# Bones allowed while posing onto the target. The protector's shoulder straps are weighted to the
# upper arms in the T-posed source; without them they'd stay up where the T-pose shoulder was.
# Its neck edge is weighted to the neck; falling back to a stretched spine_05 lifted it ~15 cm.
POSE_BONES = dict(RIGID_BONES, Protector=RIGID_BONES["Protector"] | {"upperarm_l", "upperarm_r", "neck_01", "neck_02"})
SHELL_OFFSET = 0.020   # gap between torso skin and the gear-free dobok top (m)
PASSES = 4
MAX_PUSH = 0.18        # ignore hits that would move a vertex further than this in one pass (armpit/crotch gaps)

target_fbx = globals().get("TARGET_FBX")
target_head_fbx = globals().get("TARGET_HEAD_FBX")
if not target_fbx:
    raise RuntimeError('Pass TARGET_FBX: run("fit_to_body", TARGET_FBX=r"...")')
target_name = os.path.splitext(os.path.basename(target_fbx))[0]
coll_name = f"Target_{target_name}"

src_arm = bpy.data.objects[cfg.ARMATURE_NAME]


def reset_src_pose():
    for pb in src_arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


reset_src_pose()

# --- clear a previous run for the same target ---
old = bpy.data.collections.get(coll_name)
if old:
    for o in list(old.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)
    bpy.data.collections.remove(old)


def import_fbx(path):
    coll = bpy.data.collections.get(coll_name) or bpy.data.collections.new(coll_name)
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
    before = set(bpy.data.objects)
    # keep leaf bones: in a MetaHuman body skeleton "head" is a leaf, and the helmet binds to it
    bpy.ops.import_scene.fbx(filepath=path, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


new = import_fbx(target_fbx)
tgt_arm = next(o for o in new if o.type == 'ARMATURE')
tgt_body = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
log("target body armature", tgt_arm.name, len(tgt_arm.data.bones), "bones; mesh", tgt_body.name, len(tgt_body.data.vertices))

head_arm, head_mesh = None, None
if target_head_fbx:
    head_new = import_fbx(target_head_fbx)
    head_arm = next((o for o in head_new if o.type == 'ARMATURE'), None)
    head_mesh = max((o for o in head_new if o.type == 'MESH'), key=lambda o: len(o.data.vertices), default=None)
    log("target head armature", head_arm.name if head_arm else None, "mesh", head_mesh.name if head_mesh else None)
for o in bpy.data.collections[coll_name].objects:
    if o.type == 'ARMATURE':
        o.hide_set(True)

# --- target joints: body skeleton first, head skeleton fills in what the body lacks (head) ---
J_HEAD, J_TAIL = {}, {}
for arm in [a for a in (tgt_arm, head_arm) if a]:
    for b in arm.data.bones:
        if b.name not in J_HEAD:
            J_HEAD[b.name] = arm.matrix_world @ b.head_local
            J_TAIL[b.name] = arm.matrix_world @ b.tail_local
missing = [b.name for b in src_arm.data.bones if b.name not in J_HEAD]
log("joints available", len(J_HEAD), "source bones without a target joint", missing)

# --- pose our skeleton onto the target joints ---
MAIN_CHILD = {}
for b in src_arm.data.bones:
    kids = [c for c in b.children if c.name in J_HEAD and not c.name.startswith("ik_") and "twist" not in c.name]
    if kids:
        MAIN_CHILD[b.name] = min(kids, key=lambda c: (c.head_local - b.tail_local).length).name

sw = src_arm.matrix_world
swi = sw.inverted()
ROT = {}  # world rotation applied to each posed bone
for b in src_arm.data.bones:  # parents before children
    name = b.name
    if name not in J_HEAD or name.startswith("ik_"):
        continue
    r_head = sw @ b.head_local
    r_dir = sw.to_3x3() @ (b.tail_local - b.head_local)
    t_head = J_HEAD[name]
    if name in MAIN_CHILD:
        t_dir = J_HEAD[MAIN_CHILD[name]] - t_head
        src_len = ((sw @ src_arm.data.bones[MAIN_CHILD[name]].head_local) - r_head).length
        if t_dir.length < 1e-6 or r_dir.length < 1e-6:
            continue
        rot = r_dir.normalized().rotation_difference(t_dir.normalized()).to_matrix()
        stretch = t_dir.length / src_len
        axis = t_dir.normalized()
    else:
        # Leaf bone (head, ball, fingertips): imported leaf tails are arbitrary, so keep the
        # parent's rotation and only move the joint.
        rot = ROT.get(b.parent.name, Matrix.Identity(3)) if b.parent else Matrix.Identity(3)
        stretch, axis = 1.0, Vector((0, 0, 1))
    ROT[name] = rot
    outer = Matrix(((axis.x * axis.x, axis.x * axis.y, axis.x * axis.z),
                    (axis.y * axis.x, axis.y * axis.y, axis.y * axis.z),
                    (axis.z * axis.x, axis.z * axis.y, axis.z * axis.z)))
    deform = (Matrix.Identity(3) + (stretch - 1.0) * outer) @ rot
    m = Matrix.Translation(t_head) @ deform.to_4x4() @ Matrix.Translation(-r_head) @ (sw @ b.matrix_local)
    src_arm.pose.bones[name].matrix = swi @ m
    bpy.context.view_layer.update()
log("posed source skeleton onto target joints")

# --- target surface ---
depsgraph = bpy.context.evaluated_depsgraph_get()


def world_bmesh(obj):
    bm = bmesh.new()
    bm.from_object(obj, depsgraph)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    return bm


surface = world_bmesh(tgt_body)
if head_mesh:
    hb = world_bmesh(head_mesh)
    tmp = bpy.data.meshes.new("tmp_head_surface")
    hb.to_mesh(tmp)
    surface.from_mesh(tmp)   # appends the head faces
    bpy.data.meshes.remove(tmp)
    hb.free()
bvh = BVHTree.FromBMesh(surface)
surface.free()


# --- bone axes used for radial measurement ---
def extend(a, b, length):
    d = b - a
    return b + d.normalized() * length if d.length > 1e-6 else b + Vector((0, 0, length))


def J(name, fallback=None):
    return J_HEAD.get(name, fallback)


SEGMENTS = {}
if J("pelvis") is not None and J("neck_01") is not None:
    SEGMENTS["spine"] = (J("pelvis"), J("neck_01"))
if J("neck_01") is not None:
    SEGMENTS["neck"] = (J("neck_01"), J("head", J("neck_02")))
if J("head") is not None:
    c = J("head") + Vector((0.0, -0.01, 0.09))
    SEGMENTS["head"] = (c, c)
for s in ("l", "r"):
    for key, a, b in (("clavicle", f"clavicle_{s}", f"upperarm_{s}"), ("upperarm", f"upperarm_{s}", f"lowerarm_{s}"),
                      ("lowerarm", f"lowerarm_{s}", f"hand_{s}"), ("thigh", f"thigh_{s}", f"calf_{s}"),
                      ("calf", f"calf_{s}", f"foot_{s}"), ("foot", f"foot_{s}", f"ball_{s}")):
        if J(a) is not None and J(b) is not None:
            SEGMENTS[f"{key}_{s}"] = (J(a), J(b))
    if J(f"hand_{s}") is not None and J(f"lowerarm_{s}") is not None:
        SEGMENTS[f"hand_{s}"] = (J(f"hand_{s}"), extend(J(f"lowerarm_{s}"), J(f"hand_{s}"), 0.09))
    if J(f"ball_{s}") is not None and J(f"foot_{s}") is not None:
        SEGMENTS[f"ball_{s}"] = (J(f"ball_{s}"), extend(J(f"foot_{s}"), J(f"ball_{s}"), 0.06))


def segment_for_group(g):
    side = g[-2:] if g.endswith(("_l", "_r")) else ""
    base = g[:-2] if side else g
    if g == "head":
        return "head"
    if g.startswith("neck"):
        return "neck"
    for prefix, key in (("clavicle", "clavicle"), ("upperarm", "upperarm"), ("lowerarm", "lowerarm"),
                        ("thigh", "thigh"), ("calf", "calf"), ("foot", "foot"), ("ball", "ball")):
        if base.startswith(prefix):
            return key + side
    if base.startswith(("hand", "index", "middle", "ring", "pinky", "thumb")):
        return "hand" + side
    return "spine"


def closest_on_segment(p, a, b):
    ab = b - a
    if ab.length_squared < 1e-10:
        return a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return a + ab * t


out_dir = os.path.join(cfg.OUTPUT_DIR, "Fitted", target_name)
os.makedirs(out_dir, exist_ok=True)
fitted = []

for pname in FIT_PARTS:
    src = bpy.data.objects[f"{cfg.MESH_NAME}_{pname}"]
    s = PART_SETTINGS[pname]

    # evaluate the posed part, restricting rigid gear to its allowed bones
    allowed = POSE_BONES.get(pname)
    disabled = []
    if allowed:
        for b in src_arm.data.bones:
            if b.use_deform and b.name not in allowed:
                b.use_deform = False
                disabled.append(b)
    was_hidden = src.hide_get()
    src.hide_set(False)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    src.hide_set(was_hidden)
    for b in disabled:
        b.use_deform = True
    me.transform(src.matrix_world)
    me.name = f"SK_Fighter_{pname}_{target_name}"
    obj = bpy.data.objects.new(me.name, me)
    bpy.data.collections[coll_name].objects.link(obj)

    # which bone axis each vertex is measured from (dominant source weight)
    gname = {g.index: g.name for g in src.vertex_groups}
    seg_of = []
    for v in src.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        key = segment_for_group(gname[best.group]) if best else "spine"
        if pname in ("Protector", "Belt") and not (key == "spine" or key.startswith("clavicle")):
            # Rigid torso gear: measuring its neck/arm-weighted edges from the neck or arm axes
            # pushed them up toward the head.
            key = "spine"
        seg_of.append(key if key in SEGMENTS else "spine")

    n = len(me.vertices)
    nbrs = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices
        nbrs[a].append(b)
        nbrs[b].append(a)

    pelvis_z = J("pelvis").z if J("pelvis") is not None else 0.9
    neck_z = J("neck_01").z if J("neck_01") is not None else 1.45
    shoulder_x = abs(J("upperarm_l").x) if J("upperarm_l") is not None else 0.18

    for pass_i in range(PASSES):
        need = [0.0] * n
        dirs = [None] * n
        pinned = [False] * n      # vertices that must reach their exact target (push-outs)
        pushed = pulled = 0
        for i, v in enumerate(me.vertices):
            key = seg_of[i]
            a, b = SEGMENTS[key]
            q = closest_on_segment(v.co, a, b)
            d = v.co - q
            if key == "spine":
                # Measure the torso perpendicular to the spine. Past the segment ends the clamped
                # direction points up/down, which pushed collar and protector edges up to the head.
                axis = (b - a).normalized()
                d = d - axis * d.dot(axis)
                q = v.co - d   # on the spine line at the vertex's own height
            r_v = d.length
            if r_v < 1e-4:
                continue
            d /= r_v
            hit, nrm, idx, dist = bvh.ray_cast(q, d, r_v + MAX_PUSH)
            if hit is None:
                continue
            r_body = dist
            want = r_body + s["clearance"] - r_v
            shell = (pname == "Jacket" and key == "spine" and pelvis_z + 0.05 < v.co.z < neck_z - 0.03
                     and abs(v.co.x) < shoulder_x)
            if shell and r_v > r_body + SHELL_OFFSET:
                want = r_body + SHELL_OFFSET - r_v
                pulled += 1
            elif want > 0:
                pushed += 1
                pinned[i] = True
            else:
                continue
            need[i] = want
            dirs[i] = d

        # Smooth the correction *vectors* so neighbours measured from different bone axes
        # (e.g. spine vs thigh at the jacket skirt) move together instead of tearing apart.
        # A pushed vertex keeps at least the outward distance it needed along its own ray.
        zero = Vector((0.0, 0.0, 0.0))
        target = [dirs[i] * need[i] if dirs[i] is not None else zero.copy() for i in range(n)]
        disp = [t.copy() for t in target]
        for _ in range(s["smooth"]):
            nxt = disp[:]
            for i in range(n):
                if not nbrs[i]:
                    continue
                avg = sum((disp[j] for j in nbrs[i]), Vector()) / len(nbrs[i])
                val = disp[i] * 0.5 + avg * 0.5
                if pinned[i]:
                    along = val.dot(dirs[i])
                    if along < need[i]:
                        val = val + dirs[i] * (need[i] - along)
                nxt[i] = val
            disp = nxt
        moved = 0
        for i, v in enumerate(me.vertices):
            if disp[i].length < 1e-5:
                continue
            v.co += disp[i]
            moved += 1
        me.update()
        log(pname, "pass", pass_i + 1, "pushed", pushed, "shell pulled", pulled, "moved", moved,
            "max push", round(max(need), 4) if n else 0)
    fitted.append((pname, obj))


# --- normals: Meshy's mesh has inconsistently wound faces. Blender draws both sides, but Unreal
# culls back faces, so inward-facing patches showed the body through the dobok. Make winding
# consistent per connected island, then flip any island that faces the bone axes on average.
def nearest_axis_point(p):
    best, best_d = None, 1e9
    for a, b in SEGMENTS.values():
        q = closest_on_segment(p, a, b)
        d = (p - q).length_squared
        if d < best_d:
            best, best_d = q, d
    return best


def orient_normals_outward(obj):
    me = obj.data
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    seen = set()
    islands = flipped = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        seen.add(f.index)
        stack, island = [f], []
        while stack:
            g = stack.pop()
            island.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        islands += 1
        score = 0.0
        for g in island:
            c = g.calc_center_median()
            out = c - nearest_axis_point(c)
            if out.length > 1e-6:
                score += g.normal.dot(out.normalized()) * g.calc_area()
        if score < 0:
            bmesh.ops.reverse_faces(bm, faces=island)
            flipped += len(island)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return islands, flipped


for pname, obj in fitted:
    islands, flipped = orient_normals_outward(obj)
    log(pname, "normals: islands", islands, "faces flipped", flipped, "of", len(obj.data.polygons))

# --- weights ---
# Copied body weights make loose cloth follow whatever skin is nearest (collar -> shoulder/arm,
# skirt -> thigh), which warps it in extreme poses. Rules below keep each region on sensible
# bones, then weights are smoothed over the garment so neighbours move together.
WEIGHT_SMOOTH = {"Jacket": 20, "Pants": 4, "Belt": 12, "Protector": 25, "Gloves": 2, "FootGuards": 2}
ARM_PARENTS = {b.name: (b.parent.name if b.parent else None) for b in tgt_arm.data.bones}
COLLAR_BONES = {"spine_04", "spine_05", "neck_01", "neck_02", "clavicle_l", "clavicle_r"}
SKIRT_TO_PELVIS = 0.5   # share of thigh influence moved to the pelvis on the jacket skirt


def smoothstep(edge0, edge1, x):
    """0 at edge0, 1 at edge1 (either order)."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def blend_weights(a, b, t):
    out = {k: v * (1.0 - t) for k, v in a.items()}
    for k, v in b.items():
        out[k] = out.get(k, 0.0) + v * t
    return out


def remap_to_allowed(w, allowed):
    """Move weight on disallowed bones to their nearest allowed ancestor."""
    out = {}
    for bone, val in w.items():
        b = bone
        while b is not None and b not in allowed:
            b = ARM_PARENTS.get(b)
        if b is not None:
            out[b] = out.get(b, 0.0) + val
    return out


def postprocess_weights(pname, obj):
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    W = [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0} for v in me.vertices]
    neck = J("neck_01")
    pelvis = J("pelvis")
    rules = {"collar": 0, "skirt": 0}
    for i, v in enumerate(me.vertices):
        w = W[i]
        if pname in RIGID_BONES:
            w = remap_to_allowed(w, RIGID_BONES[pname] - {"root"})
        elif pname == "Jacket":
            # Soft regions: a hard boundary between rule and no-rule weights folds the cloth.
            t_collar = 0.0
            if neck is not None:
                horiz = Vector((v.co.x - neck.x, v.co.y - neck.y, 0)).length
                t_collar = smoothstep(0.20, 0.10, horiz) * smoothstep(neck.z - 0.12, neck.z - 0.05, v.co.z)
            if t_collar > 0.0:
                w = blend_weights(w, remap_to_allowed(w, COLLAR_BONES), t_collar)
                rules["collar"] += 1
            if pelvis is not None:
                t_skirt = smoothstep(pelvis.z + 0.06, pelvis.z - 0.02, v.co.z) * SKIRT_TO_PELVIS
                moved = 0.0
                for bone in list(w):
                    if bone.startswith("thigh") and t_skirt > 0.0:
                        share = w[bone] * t_skirt
                        w[bone] -= share
                        moved += share
                if moved:
                    w["pelvis"] = w.get("pelvis", 0.0) + moved
                    rules["skirt"] += 1
        W[i] = w or {"pelvis": 1.0}

    nbrs = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        nbrs[a].append(b)
        nbrs[b].append(a)
    for _ in range(WEIGHT_SMOOTH.get(pname, 0)):
        nxt = []
        for i, w in enumerate(W):
            if not nbrs[i]:
                nxt.append(w)
                continue
            acc = {k: val * 0.5 for k, val in w.items()}
            f = 0.5 / len(nbrs[i])
            for j in nbrs[i]:
                for k, val in W[j].items():
                    acc[k] = acc.get(k, 0.0) + val * f
            nxt.append(acc)
        W = nxt

    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        keep = sorted(((k, val) for k, val in w.items() if val >= 0.02), key=lambda t: -t[1])[:4]
        total = sum(val for _, val in keep) or 1.0
        for k, val in keep:
            if k not in groups:
                groups[k] = obj.vertex_groups.new(name=k)
            groups[k].add([i], val / total, 'REPLACE')
    log(pname, "weight rules", rules, "smooth", WEIGHT_SMOOTH.get(pname, 0))


# --- weights and parenting ---
for pname, obj in fitted:
    obj.vertex_groups.clear()
    obj.shape_key_clear()
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    if pname == "Helmet":
        # prefer the body skeleton so the helmet follows the body component in Unreal
        parent_arm = tgt_arm if "head" in tgt_arm.data.bones else (head_arm or tgt_arm)
        g = obj.vertex_groups.new(name="head")
        g.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    else:
        parent_arm = tgt_arm
        dt = obj.modifiers.new("WeightTransfer", 'DATA_TRANSFER')
        dt.object = tgt_body
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
        postprocess_weights(pname, obj)
        used = {g.group for v in obj.data.vertices for g in v.groups}
        for gn in [g.name for g in obj.vertex_groups if g.index not in used]:
            obj.vertex_groups.remove(obj.vertex_groups[gn])
    mwld = obj.matrix_world.copy()
    obj.parent = parent_arm
    obj.matrix_world = mwld
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = parent_arm
    log(pname, "weights:", len(obj.vertex_groups), "groups; parent", parent_arm.name)

reset_src_pose()

# --- export ---
# Unreal turns the armature object's name into the top bone, so whichever armature is being
# exported must be called "root" (Blender imports the head skeleton as "root.001").
ARM_NAMES = {a: a.name for a in (tgt_arm, head_arm) if a}
for pname, obj in fitted:
    arm = obj.parent
    for other in ARM_NAMES:
        other.name = f"tmp_{ARM_NAMES[other]}"
    arm.name = "root"
    was = arm.hide_get()
    arm.hide_set(False)
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(o in (arm, obj))
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(out_dir, f"SK_Fighter_{pname}.fbx")
    # FBX_SCALE_NONE bakes metres -> centimetres into the file (UnitScaleFactor 1, root scale 1),
    # matching the MetaHuman FBX. FBX_SCALE_ALL wrote metre geometry under a 0.01-scaled root,
    # which Unreal imports 100x too small because it doesn't convert scene units by default.
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=False, add_leaf_bones=False,
        primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
        armature_nodetype='NULL', bake_anim=False, path_mode='COPY', embed_textures=False)
    arm.hide_set(was)
    log("exported", path, "armature exported as", arm.name)
for a, n in ARM_NAMES.items():
    a.name = f"tmp_restore_{n}"
for a, n in ARM_NAMES.items():
    a.name = n
log.close()
