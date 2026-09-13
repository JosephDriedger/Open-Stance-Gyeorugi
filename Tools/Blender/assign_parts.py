"""Pass 2 of the part split: assign segment_parts.py patches to customization parts.

Big patches are labelled by rules (colour class, position, whether they are covered by
another surface); small patches then take the label of the neighbours they share the
most edge length with. Result: face attribute "part" (index into PARTS) and a
"viz_part" colour attribute.
"""
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import rig_config as cfg

log = cfg.open_log("assign_parts")

PARTS = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]
PART_VIZ = {
    "Head": (0.95, 0.6, 0.45), "BodySkin": (0.85, 0.45, 0.3), "Helmet": (0.1, 0.3, 0.95),
    "Protector": (0.2, 0.8, 0.9), "Jacket": (0.95, 0.95, 0.95), "Pants": (0.7, 0.7, 0.5),
    "Belt": (0.1, 0.1, 0.1), "Gloves": (0.9, 0.2, 0.2), "FootGuards": (0.6, 0.2, 0.8),
}
CLASSES = ["white", "grey", "black", "blue", "skin"]
SMALL_PATCH = 60        # faces; patches below this are absorbed by neighbours
COVER_DIST = 0.06       # m; a surface with another surface this close along its normal is hidden

mesh = bpy.data.objects[cfg.MESH_NAME]
me = mesh.data
mw = mesh.matrix_world
cls = [0] * len(me.polygons)
patch = [0] * len(me.polygons)
me.attributes["colour_class"].data.foreach_get("value", cls)
me.attributes["patch"].data.foreach_get("value", patch)

bm = bmesh.new()
bm.from_mesh(me)
bm.transform(mw)
bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)

# --- per-patch stats ---
stats = {}
for f in bm.faces:
    p = patch[f.index]
    s = stats.setdefault(p, {"n": 0, "area": 0.0, "c": Vector(), "min": Vector((9, 9, 9)), "max": Vector((-9, -9, -9)),
                             "cls": CLASSES[cls[f.index]], "covered": 0.0, "faces": []})
    c = f.calc_center_median()
    a = f.calc_area()
    s["n"] += 1
    s["area"] += a
    s["c"] += c * a
    s["faces"].append(f.index)
    for i in range(3):
        s["min"][i] = min(s["min"][i], c[i])
        s["max"][i] = max(s["max"][i], c[i])
for p, s in stats.items():
    s["c"] /= max(s["area"], 1e-9)

# coverage: sample up to 40 faces per patch, ray along the normal
for p, s in stats.items():
    ids = s["faces"][:: max(1, len(s["faces"]) // 40)]
    hits = 0
    for i in ids:
        f = bm.faces[i]
        origin = f.calc_center_median() + f.normal * 0.002
        loc, nrm, idx, dist = bvh.ray_cast(origin, f.normal, COVER_DIST)
        hits += loc is not None
    s["covered"] = hits / len(ids)


def rule(s):
    c, cl = s["c"], s["cls"]
    x, y, z = c
    ax = abs(x)
    head_zone = z > 1.43 and (x * x + (y - 0.02) ** 2) ** 0.5 < 0.17
    if cl == "skin":
        if z > 1.3 and ax < 0.2:
            return "Head"
        return "BodySkin"                     # fingers, toes
    if ax > 0.645 and z > 1.2:
        return "Gloves"
    if cl == "black" and 1.3 < z < 1.46 and ax < 0.12:
        return "Jacket"                       # black dan collar (sits below the helmet's chin strap)
    if cl == "blue" and head_zone and z < 1.46:
        return "Protector"                    # protector neck binding
    if head_zone:
        return "Helmet" if cl in ("blue", "black", "grey") or z > 1.5 else None
    if z < 0.16 and s["max"].z < 0.22:
        return "FootGuards"
    if cl == "blue":
        return "Protector" if 0.8 < z < 1.5 else None
    if cl == "black" and s["min"].z > 0.55 and s["max"].z < 1.06 and ax < 0.16:
        return "Belt"                         # band, knot and hanging tails
    if cl in ("white", "grey"):
        if s["max"].x > 0.4 and s["min"].x < -0.4:
            return "Jacket"                   # one patch spanning both sleeves and the torso
        if 1.0 < z < 1.46 and s["max"].x < 0.23 and s["min"].x > -0.23:
            return "Jacket" if s["covered"] > 0.5 else "Protector"
        if ax > 0.2 and z > 1.2:
            return "Jacket"                   # sleeves
        if s["min"].z > 0.7 and z > 0.8 and s["max"].z < 1.02:
            return "Jacket"                   # skirt
        if z < 0.85:
            return "Pants"
    return None


label = {}
for p, s in stats.items():
    if s["n"] >= SMALL_PATCH:
        label[p] = rule(s)

big = sorted(stats.items(), key=lambda kv: -kv[1]["n"])[:60]
for p, s in big:
    log(p, s["n"], s["cls"], tuple(round(v, 3) for v in s["c"]),
        "zr", round(s["min"].z, 2), round(s["max"].z, 2), "xr", round(s["min"].x, 2), round(s["max"].x, 2),
        "cov", round(s["covered"], 2), "->", label.get(p))

# --- absorb small / unlabelled patches into neighbours by shared edge length ---
face_label = [None] * len(bm.faces)
for p, s in stats.items():
    for i in s["faces"]:
        face_label[i] = label.get(p)

for it in range(30):
    changed = 0
    votes = {}
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        a, b = e.link_faces
        la, lb = face_label[a.index], face_label[b.index]
        if patch[a.index] == patch[b.index] or (la is None) == (lb is None) and la == lb:
            continue
        L = e.calc_length()
        if la is not None:
            pv = votes.setdefault(patch[b.index], {})
            pv[la] = pv.get(la, 0.0) + L
        if lb is not None:
            pv = votes.setdefault(patch[a.index], {})
            pv[lb] = pv.get(lb, 0.0) + L
    for p, v in votes.items():
        if label.get(p) is None:
            label[p] = max(v.items(), key=lambda kv: kv[1])[0]
            for i in stats[p]["faces"]:
                face_label[i] = label[p]
            changed += 1
    if changed == 0:
        break
log("absorb iterations:", it + 1)

unlabelled = sum(1 for l in face_label if l is None)
face_label = [l or "Jacket" for l in face_label]

# --- stray fragment cleanup: small connected pieces of a part join the part they touch most,
#     or (if fully disconnected) the part whose large pieces are nearest ---
FRAGMENT = 40
centres = [f.calc_center_median() for f in bm.faces]
for rnd in range(4):
    comp = [-1] * len(bm.faces)
    comps = []
    for f in bm.faces:
        if comp[f.index] >= 0:
            continue
        cid = len(comps)
        members, stack = [], [f]
        comp[f.index] = cid
        while stack:
            a = stack.pop()
            members.append(a.index)
            for e in a.edges:
                for b in e.link_faces:
                    if comp[b.index] < 0 and face_label[b.index] == face_label[a.index]:
                        comp[b.index] = cid
                        stack.append(b)
        comps.append(members)

    anchors = {}
    for members in comps:
        if len(members) >= 500:
            lab = face_label[members[0]]
            anchors.setdefault(lab, []).extend(members[:: max(1, len(members) // 300)])
    kd_by_part = {}
    from mathutils.kdtree import KDTree
    for lab, ids in anchors.items():
        kd = KDTree(len(ids))
        for i in ids:
            kd.insert(centres[i], i)
        kd.balance()
        kd_by_part[lab] = kd

    moved = 0
    for members in comps:
        if len(members) >= FRAGMENT:
            continue
        own = face_label[members[0]]
        mset = set(members)
        touch = {}
        for i in members:
            for e in bm.faces[i].edges:
                for b in e.link_faces:
                    if b.index not in mset:
                        lb = face_label[b.index]
                        touch[lb] = touch.get(lb, 0.0) + e.calc_length()
        if touch:
            new = max(touch.items(), key=lambda kv: kv[1])[0]
        else:
            c = centres[members[0]]
            new = min(kd_by_part.items(), key=lambda kv: kv[1].find(c)[2])[0]
        if new != own:
            for i in members:
                face_label[i] = new
            moved += 1
    log("fragment cleanup round", rnd, "components", len(comps), "moved", moved)
    if moved == 0:
        break

# Collar override: every black face around the neck belongs to the jacket's collar so the
# collar recolours as one piece (small collar fragments otherwise end up on Protector/Head).
# The helmet chin strap sits higher at the front, so it is excluded by height.
collar_moved = 0
for f in bm.faces:
    # black only: shaded grey faces here belong to the protector's shoulder panel
    if CLASSES[cls[f.index]] != "black" or face_label[f.index] in ("Helmet", "Jacket", "Head"):
        continue
    x, y, z = centres[f.index]
    if (x * x + (y - 0.02) ** 2) ** 0.5 < 0.14 and 1.30 < z < (1.47 if y > 0 else 1.44):
        face_label[f.index] = "Jacket"
        collar_moved += 1
log("collar override faces:", collar_moved)
bm.free()

counts = {pt: face_label.count(pt) for pt in PARTS}
log("faces per part:", counts, "unlabelled->Jacket:", unlabelled)

if "part" in me.attributes:
    me.attributes.remove(me.attributes["part"])
me.attributes.new("part", 'INT', 'FACE').data.foreach_set("value", [PARTS.index(l) for l in face_label])
if "viz_part" in me.color_attributes:
    me.color_attributes.remove(me.color_attributes["viz_part"])
viz = me.color_attributes.new("viz_part", 'BYTE_COLOR', 'CORNER')
cols = []
for poly in me.polygons:
    cols.extend((PART_VIZ[face_label[poly.index]] + (1.0,)) * poly.loop_total)
viz.data.foreach_set("color", cols)
log.close()
