"""Check that fitted gear survives the extreme poses in Docs/Open_Stance_Mocap_Shot_List.docx.

Reads the exported FBX files Unreal imports (no Blender or Unreal session needed), poses the
MetaHuman body skeleton into one pose per demanding shot, skins every mesh with the same linear
blend skinning Unreal uses, and reports per garment:

- torn edges: edges that grow by more than TEAR_CM and to more than TEAR_RATIO times their rest
  length (the long spikes that show when weights disagree across a joint);
- show-through (advisory): points covered by the garment at rest (visible skin, the jacket under
  the protector and belt, the pants under the jacket, the head under the helmet) that end up more
  than POKE_MM outside it. Skin removed by the hidden face maps (T_HFM_<Part>.png) is ignored, as
  in game. It also counts layers that legitimately slide out from under an edge (a sleeve leaving
  the protector's armhole when the arms go up), so look at --render images before acting on it.

The bare body is checked the same way as a control: if the body tears too, the pose is wrong.

    py Tools/Validation/check_gear_poses.py                       all poses, base fighter
    py Tools/Validation/check_gear_poses.py --body MH_FighterBase_Body --only KCK-12 RES-08
    py Tools/Validation/check_gear_poses.py --render OUT_DIR      also save a PNG per pose

Needs numpy, scipy and Pillow, plus Blender's FBX parser (pure Python): the newest Blender
install is found automatically, or set BLENDER_FBX_ADDON to its io_scene_fbx folder.
Limits: MetaHuman corrective bones (twistCor, thigh_bck_lwr, ...) are driven by RigLogic in
Unreal; here they follow their parents rigidly, so this is a weights check, not a final look.
Exit code 1 if any garment tears in any pose.
"""
import argparse
import glob
import json
import math
import os
import sys
import types

import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = os.path.join(ROOT, "Resources", "Models")
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
# Layers each garment covers (default: the body's visible skin).
UNDER = {"Protector": ["Jacket"], "Belt": ["Jacket"], "Helmet": ["head"], "Jacket": ["body", "Pants"]}
HFM_PARTS = ["Jacket", "Pants", "Gloves", "FootGuards"]
# An edge counts as torn when it grows by TEAR_CM and to TEAR_RATIO times its rest length. 12 cm is the
# size of a visible gap in the renders: the dobok's crotch gusset legitimately stretches 7-10 cm in
# full splits and head-height kicks (cloth, no gap), while the weight bug this check found made
# 20-38 cm spikes. `max_growth_cm` in the report keeps the actual figure.
TEAR_CM, TEAR_RATIO = 12.0, 2.0
POKE_MM = 5.0            # how far a covered point must come out through the garment to count
COVER_CM = 4.0           # a point counts as covered at rest if it's under the garment within this

ARMS_DOWN = 25           # MetaHuman A-pose: degrees the arms still drop for a guard
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)   # common frame: Z up, character faces -Y, its left is +X


# --- FBX loading ---------------------------------------------------------------------------

def _parser():
    path = os.environ.get("BLENDER_FBX_ADDON")
    if not path:
        roots = glob.glob(r"C:\Program Files\Blender Foundation\Blender*")
        try:   # Microsoft Store install: WindowsApps can't be listed, so ask for the package folder
            import subprocess
            roots += subprocess.run(["powershell", "-NoProfile", "-Command",
                                     "(Get-AppxPackage *Blender*).InstallLocation"],
                                    capture_output=True, text=True, timeout=30).stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            pass
        cands = sorted(c for r in roots if r.strip() for pat in (("*",), ("Blender", "*"))
                       for c in glob.glob(os.path.join(r.strip(), *pat, "scripts", "addons_core", "io_scene_fbx")))
        if not cands:
            sys.exit("Blender's io_scene_fbx not found; set BLENDER_FBX_ADDON")
        path = cands[-1]
    pkg = types.ModuleType("_blender_fbx")
    pkg.__path__ = [path]          # import parse_fbx without the add-on's bpy-dependent __init__
    sys.modules["_blender_fbx"] = pkg
    from _blender_fbx.parse_fbx import parse
    return parse


PARSE = _parser()


def _s(b):
    return b.decode("utf-8", "replace").split("\x00")[0] if isinstance(b, bytes) else b


def _children(e, name):
    return [c for c in e.elems if _s(c.id) == name]


def _props(e):
    out = {}
    for p70 in _children(e, "Properties70"):
        for p in p70.elems:
            out[_s(p.props[0])] = p.props[4:]
    return out


def _euler(deg):
    x, y, z = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def _local(p):
    m = np.eye(4)
    rot = _euler(p.get("Lcl Rotation", [0, 0, 0]))
    if "PreRotation" in p:
        rot = _euler(p["PreRotation"]) @ rot
    if "PostRotation" in p:
        rot = rot @ _euler(p["PostRotation"]).T
    m[:3, :3] = rot @ np.diag(p.get("Lcl Scaling", [1, 1, 1]))
    m[:3, 3] = p.get("Lcl Translation", [0, 0, 0])
    return m


def load_fbx(path):
    """Bones (bind globals), meshes (bind vertices, faces, UVs, skin weights), in the common frame."""
    root, _ = PARSE(path)
    gs = _props(_children(root, "GlobalSettings")[0])
    objs = _children(root, "Objects")[0]
    nodes, kinds = {}, {}
    for o in objs.elems:
        nodes[o.props[0]] = o
        kinds[o.props[0]] = (_s(o.id), _s(o.props[2]))
    parent, kids = {}, {}
    for c in _children(root, "Connections")[0].elems:
        if _s(c.props[0]) == "OO":
            child, par = c.props[1], c.props[2]
            kids.setdefault(par, []).append(child)
            # A bone is also connected to its skin cluster; only Model/Geometry -> Model is hierarchy.
            if kinds.get(par, ("",))[0] == "Model" or par not in kinds:   # par 0 is the scene root
                parent[child] = par
            else:
                parent.setdefault(child, par)

    # File axes -> common frame (Z up, metres -> centimetres already applied by the exporters).
    up, coord = gs["UpAxis"][0], gs["CoordAxis"][0]
    front = 3 - up - coord
    conv = np.zeros((4, 4))
    conv[3, 3] = 1
    conv[0, coord] = gs.get("CoordAxisSign", [1])[0]
    conv[2, up] = gs.get("UpAxisSign", [1])[0]
    conv[1, front] = -gs.get("FrontAxisSign", [1])[0]

    gcache = {}

    def gmat(oid):
        if oid not in gcache:
            m = _local(_props(nodes[oid]))
            p = parent.get(oid)
            gcache[oid] = (gmat(p) @ m) if p in nodes and kinds[p][0] == "Model" else m
        return gcache[oid]

    bones = {}
    for oid, (t, sub) in kinds.items():
        if t == "Model" and sub in ("LimbNode", "Null", "Root") and oid in parent:
            bones[_s(nodes[oid].props[1])] = oid
    bone_parent = {}
    for name, oid in bones.items():
        p = parent.get(oid)
        bone_parent[name] = _s(nodes[p].props[1]) if p in bones.values() else None
    G = {name: conv @ gmat(oid) for name, oid in bones.items()}

    meshes = {}
    for oid, (t, sub) in kinds.items():
        if t != "Geometry" or sub != "Mesh":
            continue
        g = nodes[oid]
        v = np.array(_children(g, "Vertices")[0].props[0], dtype=float).reshape(-1, 3)
        pvi = np.array(_children(g, "PolygonVertexIndex")[0].props[0], dtype=np.int64)
        faces, cur = [], []
        for i in pvi:
            if i < 0:
                cur.append(-i - 1)
                faces.append(cur)
                cur = []
            else:
                cur.append(i)
        uv = None
        for le in _children(g, "LayerElementUV")[:1]:
            uvs = np.array(_children(le, "UV")[0].props[0]).reshape(-1, 2)
            idx = _children(le, "UVIndex")
            if idx:
                uvs = uvs[np.array(idx[0].props[0])]
            if _s(_children(le, "MappingInformationType")[0].props[0]) in ("ByVertice", "ByVertex"):
                uvs = uvs[np.abs(pvi) - (pvi < 0)]          # Unreal's export: one UV per vertex
            uv = uvs                                         # per polygon-vertex, in face order
        model = parent.get(oid)
        name = _s(nodes[model].props[1]) if model in nodes else str(oid)
        bones_used, mats, cols = [], [], []
        for skin in kids.get(oid, []):
            if kinds.get(skin) != ("Deformer", "Skin"):
                continue
            for cl in kids.get(skin, []):
                cn = nodes[cl]
                idx = _children(cn, "Indexes")
                if not idx:
                    continue
                bone_oid = next(k for k in kids.get(cl, []) if k in nodes and kinds[k][0] == "Model")
                col = np.zeros(len(v))
                col[np.array(idx[0].props[0])] = _children(cn, "Weights")[0].props[0]
                cols.append(col)
                bones_used.append(_s(nodes[bone_oid].props[1]))
                # Bind position = TransformLink (bone at bind) @ Transform (mesh in bone space) @ vertex;
                # both Unreal's and Blender's exporters write Transform relative to the bone.
                t = np.array(_children(cn, "Transform")[0].props[0]).reshape(4, 4).T
                tl = np.array(_children(cn, "TransformLink")[0].props[0]).reshape(4, 4).T
                mats.append(conv @ tl @ t)
        vh = np.c_[v, np.ones(len(v))]
        if cols:
            w = np.stack(cols, axis=1)
            tot = w.sum(1)
            tot[tot == 0] = 1
            w /= tot[:, None]
            bind = sum(w[:, j, None] * (vh @ m.T) for j, m in enumerate(mats))
        else:
            w = np.zeros((len(v), 0))
            bind = vh @ (conv @ gmat(model)).T
        meshes[name] = dict(v=bind[:, :3], vh=vh, faces=faces, uv=uv, w=w, bones=bones_used, mats=mats)
    return dict(G=G, parent=bone_parent, meshes=meshes, path=path)


# --- posing ---------------------------------------------------------------------------------

class Pose:
    """World-space bone rotations about each bone's head; children follow (like posetest.rot)."""

    def __init__(self, G, parent):
        self.G, self.parent = G, parent
        self.kids = {}
        for b, p in parent.items():
            self.kids.setdefault(p, []).append(b)
        self.reset()

    def reset(self):
        self.D = {b: np.eye(4) for b in self.G}

    def head(self, b):
        return (self.D[b] @ self.G[b])[:3, 3]

    def rot(self, bone, axis, deg):
        a = np.array(axis, float) / np.linalg.norm(axis)
        t = math.radians(deg)
        k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        r = np.eye(4)
        r[:3, :3] = np.eye(3) + math.sin(t) * k + (1 - math.cos(t)) * k @ k
        h = self.head(bone)
        tr, back = np.eye(4), np.eye(4)
        tr[:3, 3], back[:3, 3] = h, -h
        m = tr @ r @ back
        stack = [bone]
        while stack:
            b = stack.pop()
            self.D[b] = m @ self.D[b]
            stack.extend(self.kids.get(b, []))

    def delta(self, name, other_parent):
        """Delta for a bone of another file's skeleton: its own, or its nearest shared ancestor's."""
        b = name
        while b is not None and b not in self.D:
            b = other_parent.get(b)
        return self.D[b] if b is not None else np.eye(4)


def skin(mesh, pose, other_parent):
    if not mesh["bones"]:
        return mesh["v"].copy()
    vh = mesh["vh"]
    out = np.zeros((len(vh), 4))
    for j, b in enumerate(mesh["bones"]):
        w = mesh["w"][:, j]
        nz = w > 0
        if nz.any():
            out[nz] += w[nz, None] * (vh[nz] @ (pose.delta(b, other_parent) @ mesh["mats"][j]).T)
    unweighted = mesh["w"].sum(1) == 0
    out[unweighted, :3] = mesh["v"][unweighted]
    return out[:, :3]


# --- poses (one per demanding group of shots) -------------------------------------------------

def fist(p, s):
    k = 1 if s == "l" else -1
    for f in ("index", "middle", "ring", "pinky"):
        p.rot(f"{f}_01_{s}", (0, k, 0), 80)
        p.rot(f"{f}_02_{s}", (0, k, 0), 95)
        p.rot(f"{f}_03_{s}", (0, k, 0), 60)
    p.rot(f"thumb_02_{s}", (0, k, 0), 30)
    p.rot(f"thumb_03_{s}", (0, k, 0), 40)


def guard(p):
    for s, k in (("l", 1), ("r", -1)):
        fist(p, s)
        p.rot(f"upperarm_{s}", Y, k * ARMS_DOWN)
        p.rot(f"upperarm_{s}", Z, -k * 30)
        p.rot(f"lowerarm_{s}", X, -115)


def legs_bent(p, hip, knee, sides="lr"):
    for s in sides:
        p.rot(f"thigh_{s}", X, -hip)
        p.rot(f"calf_{s}", X, knee)


def arms_up(p, deg):
    p.rot("upperarm_l", Y, -deg)
    p.rot("upperarm_r", Y, deg)


def p_chamber(p):
    guard(p)
    p.rot("calf_l", X, 125)
    p.rot("foot_l", X, 35)
    p.rot("thigh_l", X, -95)
    p.rot("thigh_l", Y, 40)
    p.rot("spine_03", Z, -15)
    p.rot("spine_01", Y, -10)


def p_spin(p):
    guard(p)
    for b, d in (("spine_01", 20), ("spine_03", 25), ("spine_05", 15), ("neck_01", 15)):
        p.rot(b, Z, d)
    legs_bent(p, 60, 110, "l")


def p_side_high(p):
    guard(p)
    p.rot("thigh_l", Y, -110)
    p.rot("foot_l", X, 20)
    p.rot("spine_01", Y, -25)
    p.rot("spine_03", Y, -10)


def p_axe(p):
    guard(p)
    p.rot("thigh_l", X, -125)
    p.rot("foot_l", X, 30)
    p.rot("spine_01", X, -10)


def p_splits(p):
    p.rot("thigh_l", Y, -80)
    p.rot("thigh_r", Y, 80)
    p.rot("spine_01", X, 25)


def p_squat(p):
    guard(p)
    legs_bent(p, 110, 130)
    p.rot("foot_l", X, -30)
    p.rot("foot_r", X, -30)
    p.rot("spine_01", X, 30)


def p_kneel(p):
    legs_bent(p, 90, 90, "l")
    p.rot("calf_r", X, 100)
    p.rot("foot_r", X, -40)
    p.rot("spine_01", X, 10)


def p_seated(p):
    legs_bent(p, 90, 90)
    p.rot("spine_01", X, 10)


def p_knees_to_chest(p):
    legs_bent(p, 130, 140)
    p.rot("spine_01", X, 25)
    p.rot("spine_03", X, 15)


def p_arms_overhead(p):
    arms_up(p, 130)


def p_hands_on_head(p):
    arms_up(p, 100)
    p.rot("lowerarm_l", Y, -120)
    p.rot("lowerarm_r", Y, 120)


def p_arms_crossed(p):
    for s, k in (("l", 1), ("r", -1)):
        p.rot(f"upperarm_{s}", Y, k * (ARMS_DOWN + 30))
        p.rot(f"upperarm_{s}", Z, -k * 25)
        p.rot(f"lowerarm_{s}", Z, -k * 120)


def p_bent_over(p):
    p.rot("spine_01", X, 35)
    p.rot("spine_03", X, 25)
    legs_bent(p, 20, 30)
    p.rot("upperarm_l", Y, ARMS_DOWN + 30)
    p.rot("upperarm_r", Y, -ARMS_DOWN - 30)


POSES = {
    "IDL-01 guard": guard,
    "CHM-01 chamber": p_chamber,
    "KCK-14 spin wind-up": p_spin,
    "KCK-09 high side extension": p_side_high,
    "KCK-12 axe / CAL-07 max kick": p_axe,
    "TRG-11 splits": p_splits,
    "DEF-11 duck / squat": p_squat,
    "MNU-14 kneel": p_kneel,
    "CER-07 seated": p_seated,
    "FAL-11 get-up, knees to chest": p_knees_to_chest,
    "RES-08 arms overhead / REF-14": p_arms_overhead,
    "COA-04 hands on head": p_hands_on_head,
    "MNU-02 arms crossed": p_arms_crossed,
    "FAT-02 bent over": p_bent_over,
}


# --- measurements ---------------------------------------------------------------------------

def edges_of(faces):
    e = set()
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            e.add((a, b) if a < b else (b, a))
    return np.array(sorted(e), dtype=np.int64)


def vertex_normals(v, faces):
    n = np.zeros_like(v)
    for f in faces:
        for i in range(1, len(f) - 1):
            a, b, c = v[f[0]], v[f[i]], v[f[i + 1]]
            fn = np.cross(b - a, c - a)
            n[[f[0], f[i], f[i + 1]]] += fn
    ln = np.linalg.norm(n, axis=1)
    ln[ln == 0] = 1
    return n / ln[:, None]


def hidden_vertices(body, hfm_dir):
    """Body vertices whose every face is removed by the hidden face maps."""
    faces, uv = body["faces"], body["uv"]
    if uv is None:
        return np.zeros(len(body["v"]), bool)
    from PIL import Image
    maps = []
    for part in HFM_PARTS:
        f = os.path.join(hfm_dir, f"T_HFM_{part}.png")
        if os.path.exists(f):
            maps.append(np.asarray(Image.open(f).convert("L"), dtype=float) / 255.0)
    vis = np.zeros(len(body["v"]), bool)
    li = 0
    for f in faces:
        corners = uv[li:li + len(f)]
        li += len(f)
        u = corners[:, 0] - np.floor(corners[:, 0])     # UDIM 1002 wrapped to 0-1, as Unreal does
        hidden = False
        for m in maps:
            h, w = m.shape
            xs = np.clip((u * w).astype(int), 0, w - 1)
            ys = np.clip(((1 - (corners[:, 1] - np.floor(corners[:, 1]))) * h).astype(int), 0, h - 1)
            if (m[ys, xs] < 0.5).all():
                hidden = True
                break
        if not hidden:
            vis[f] = True
    return ~vis


def _depth(points, surf_v, surf_faces):
    """Signed distance (cm) of points from the nearest surface vertex along its normal; <0 = under."""
    n = vertex_normals(surf_v, surf_faces)
    d, i = cKDTree(surf_v).query(points)
    return np.einsum("ij,ij->i", points - surf_v[i], n[i]), d


def covered_at_rest(inner, outer, outer_faces, skip=None):
    depth, dist = _depth(inner, outer, outer_faces)
    cov = (depth < -0.3) & (dist < COVER_CM)   # clearly under it, not grazing its rim
    return cov if skip is None else cov & ~skip


def show_through(inner, outer, outer_faces, covered):
    """Points covered by the outer surface at rest that end up more than POKE_MM outside it."""
    if not covered.any():
        return 0
    depth, _ = _depth(inner[covered], outer, outer_faces)
    return int((depth > POKE_MM / 10.0).sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", default="MH_FighterBase_Body")
    ap.add_argument("--only", nargs="*", help="pose ID prefixes, e.g. KCK-12 RES-08")
    ap.add_argument("--render", help="folder for one PNG per pose (front and side views)")
    ap.add_argument("--json", default=os.path.join(ROOT, "Saved", "Logs", "check_gear_poses.json"))
    a = ap.parse_args()

    head_name = a.body.replace("_Body", "_Head")
    body_f = load_fbx(os.path.join(MODELS, "MetaHuman", f"{a.body}.fbx"))
    head_f = load_fbx(os.path.join(MODELS, "MetaHuman", f"{head_name}.fbx"))
    fit_dir = os.path.join(MODELS, "Fitted", a.body)
    pose = Pose(body_f["G"], body_f["parent"])

    meshes = {"body": (max(body_f["meshes"].values(), key=lambda m: len(m["v"])), body_f["parent"]),
              "head": (max(head_f["meshes"].values(), key=lambda m: len(m["v"])), head_f["parent"])}
    bind_err = {}
    for part in PARTS:
        f = os.path.join(fit_dir, f"SK_Fighter_{part}.fbx")
        if not os.path.exists(f):
            continue
        g = load_fbx(f)
        meshes[part] = (max(g["meshes"].values(), key=lambda m: len(m["v"])), g["parent"])
        # The garment must be bound to the same rest skeleton as the body.
        common = [b for b in g["G"] if b in body_f["G"]]
        bind_err[part] = round(max(float(np.linalg.norm(g["G"][b][:3, 3] - body_f["G"][b][:3, 3])) for b in common), 3)
        missing = sorted(set(meshes[part][0]["bones"]) - set(body_f["G"]))
        if missing:
            print(f"{part}: weighted to bones missing from the body skeleton: {missing[:8]}")

    hidden = hidden_vertices(meshes["body"][0], fit_dir)
    edges = {k: edges_of(m["faces"]) for k, (m, _) in meshes.items()}

    def skinned():
        return {k: skin(m, pose, par) for k, (m, par) in meshes.items()}

    pose.reset()
    rest_co = skinned()
    # What each garment covers at rest: visible skin (hidden face maps applied) or the layer under it.
    covers = {}
    for k in meshes:
        if k in ("body", "head"):
            continue
        for inner in UNDER.get(k, ["body"]):
            if inner in meshes:
                skip = hidden if inner == "body" else None
                covers[(k, inner)] = covered_at_rest(rest_co[inner], rest_co[k], meshes[k][0]["faces"], skip)

    def measure():
        co = skinned()
        res = {}
        for k in co:
            if k == "head":
                continue
            shown = None
            if k != "body":
                shown = sum(show_through(co[inner], co[k], meshes[k][0]["faces"], cov)
                            for (outer, inner), cov in covers.items() if outer == k)
            res[k] = dict(co=co[k], poke=shown)
        return res

    rest = measure()
    rest_len = {k: np.linalg.norm(r["co"][edges[k][:, 0]] - r["co"][edges[k][:, 1]], axis=1) for k, r in rest.items()}

    report = {"body": a.body, "bind_offset_cm": bind_err, "tear_cm": TEAR_CM, "tear_ratio": TEAR_RATIO,
              "poke_mm": POKE_MM, "poses": {}}
    failed = False
    names = [n for n in POSES if not a.only or any(n.startswith(o) for o in a.only)]
    print(f"{'pose':34s} " + " ".join(f"{k:>12s}" for k in rest))
    for name in names:
        pose.reset()
        POSES[name](pose)
        res = measure()
        row = {}
        for k, r in res.items():
            e = edges[k]
            l1 = np.linalg.norm(r["co"][e[:, 0]] - r["co"][e[:, 1]], axis=1)
            grow = l1 - rest_len[k]
            torn = (grow > TEAR_CM) & (l1 > TEAR_RATIO * np.maximum(rest_len[k], 1e-6))
            new_poke = max(0, r["poke"] - rest[k]["poke"]) if r["poke"] is not None else 0
            bad_v = np.unique(e[torn].ravel())
            top = {}
            if len(bad_v) and k != "body":
                m = meshes[k][0]
                dom = np.argmax(m["w"][bad_v], axis=1)
                for j in dom:
                    top[m["bones"][j]] = top.get(m["bones"][j], 0) + 1
            ok = not torn.any()
            failed |= not ok and k != "body"
            row[k] = dict(torn_edges=int(torn.sum()), max_growth_cm=round(float(grow.max()), 1),
                          new_poke=new_poke, ok=ok,
                          torn_dominant_bones=dict(sorted(top.items(), key=lambda t: -t[1])[:5]))
        report["poses"][name] = row
        cells = " ".join(f"{('ok' if v['ok'] else 'FAIL') + ' ' + str(v['torn_edges']) + '/' + str(v['new_poke']):>12s}"
                         for v in row.values())
        print(f"{name:34s} {cells}")
        if a.render:
            render(a.render, name, res, meshes)
    print("cells: tear status, torn edges / show-through points (advisory); body = bare-skin control; "
          "max stretch per garment is in the report")
    print("bind offset vs body skeleton (cm):", bind_err)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w") as f:
        json.dump(report, f, indent=2)
    print("report:", a.json)
    return 1 if failed else 0


def render(out_dir, name, res, meshes):
    """Flat-shaded front and side views (painter's algorithm) for eyeballing a pose."""
    from PIL import Image, ImageDraw
    os.makedirs(out_dir, exist_ok=True)
    W = 700
    img = Image.new("RGB", (2 * W, W), (45, 45, 48))
    dr = ImageDraw.Draw(img)
    for col, (ax_x, ax_d, sign) in enumerate(((0, 1, 1), (1, 0, -1))):
        tris = []
        for k, r in res.items():
            m = meshes[k][0]
            co = r["co"]
            for f in m["faces"]:
                for i in range(1, len(f) - 1):
                    t = (f[0], f[i], f[i + 1])
                    p = co[list(t)]
                    nrm = np.cross(p[1] - p[0], p[2] - p[0])
                    ln = np.linalg.norm(nrm) or 1
                    shade = abs(nrm[ax_d]) / ln
                    tris.append((sign * p[:, ax_d].mean(), p, shade))
        tris.sort(key=lambda t: -t[0])
        for _, p, shade in tris:
            c = int(70 + 150 * shade)
            pts = [(col * W + W / 2 + sign * q[ax_x] * 2.6, W - 30 - q[2] * 2.6) for q in p]
            dr.polygon(pts, fill=(c, c, c))
    img.save(os.path.join(out_dir, name.split()[0] + ".png"))


if __name__ == "__main__":
    sys.exit(main())
