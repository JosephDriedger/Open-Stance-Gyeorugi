"""Smooth the dobok and gear skin weights wherever the placeholder technique clips stretch them (match fighters).

    blender.exe -b Resources/Models/FinalRefinement/Match/<Kind>_<Sex>/Candidate.blend -P refine_match_weights.py -- [--save] [--rounds=12]

Linear blend skinning tears a garment where neighbouring vertices follow very different bones: the trousers' crotch
gusset (one side on each thigh), the jacket under the arms, the skirt over a raised thigh. This poses the fighter
through every placeholder clip (mirrors too), finds the vertices on edges that grow more than HOT_CM, and diffuses
their weights over a few rings of neighbours (a Laplacian on the weight vectors, four influences kept), round after
round until the worst growth stops improving. Only the hot regions change; weights elsewhere stay exactly as built.

Garments that layer over each other keep their gap: the jacket skirt is smoothed with the trousers' new weights
blended in at the same ratio its builder used, so the two still deform alike.

--save writes the result back to the open file. Prints REFINE lines with the worst growth before and after.
"""
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / "Resources/Models/Animation/PlaceholderTechniques/PlaceholderTechniques.blend"
SAVE = "--save" in sys.argv
GARMENTS = ["Pants", "Jacket", "Jacket_Skirt", "Jacket_Collar", "Quilted_Lace_Back__Padded_Torso_Shell"]
HOT_CM, RINGS, PASSES, STEP, MAX_INF, FAR_M = 3.0, 3, 6, 3, 4, .22
# Limb-end bones only: a torso point on a short spine bone is legitimately far from it.
DISTAL = ("calf", "foot", "ball", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
ROUNDS = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--rounds=")), 12))

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("RIG_Body_"))
bone_names = {b.name for b in rig.data.bones if b.use_deform}
with bpy.data.libraries.load(str(CLIPS)) as (src, dst):
    dst.actions = [a for a in src.actions if a.startswith("Placeholder_")]
actions = [a for a in bpy.data.actions if a.name.startswith("Placeholder_") and a.library is None]
if not rig.animation_data:
    rig.animation_data_create()
original_action = rig.animation_data.action

objs = [bpy.data.objects[n] for n in GARMENTS if n in bpy.data.objects and not bpy.data.objects[n].hide_render]
# Measure the base topology: masks off (they delete vertices), solidify and cloth off.
saved = []
for o in objs:
    for m in o.modifiers:
        if m.type in ("MASK", "SOLIDIFY", "CLOTH"):
            saved.append((m, m.show_viewport))
            m.show_viewport = False


def coords(o):
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    a = a.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    return a @ mw[:3, :3].T + mw[:3, 3]


def rest_pose():
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.scene.frame_set(1)


def frames():
    """Yield once per sampled frame of every clip, posed."""
    for a in actions:
        rig.animation_data.action = a
        if a.slots:
            rig.animation_data.action_slot = a.slots[0]
        s, e = (int(f) for f in a.frame_range)
        for f in range(s, e + 1, STEP):
            bpy.context.scene.frame_set(f)
            yield a.name, f


class Garment:
    def __init__(self, o):
        self.o = o
        me = o.data
        self.n = len(me.vertices)
        e = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get("vertices", e)
        self.edges = e.reshape(-1, 2)
        self.deg = np.bincount(self.edges.ravel(), minlength=self.n).astype(float)
        self.bones = sorted({g.name for g in o.vertex_groups if g.name in bone_names})
        self.col = {b: i for i, b in enumerate(self.bones)}
        idx = {g.index: g.name for g in o.vertex_groups}
        self.W = np.zeros((self.n, len(self.bones)))
        for v in me.vertices:
            for g in v.groups:
                name = idx[g.group]
                if name in self.col:
                    self.W[v.index, self.col[name]] = g.weight
        self.pruned = self.prune_distant(me)
        s = self.W.sum(1, keepdims=True)
        self.W = np.divide(self.W, s, out=self.W, where=s > 0)

    def prune_distant(self, me):
        """Drop influences of limb-end bones (DISTAL) farther than FAR_M from the vertex at bind (a crotch point on the calf).

        The garments' weights are copied from nearby surfaces, and a copy can land on the wrong limb; such a vertex
        follows a bone it is nowhere near and tears away when that limb moves. Keeps the vertex's nearest bone if
        everything else would go."""
        mw = self.o.matrix_world
        rw = rig.matrix_world
        seg = []
        for b in self.bones:
            bone = rig.data.bones[b]
            seg.append((np.array(rw @ bone.head_local), np.array(rw @ bone.tail_local)))
        heads = np.array([s[0] for s in seg])
        tails = np.array([s[1] for s in seg])
        pts = np.array([mw @ v.co for v in me.vertices])
        d = np.empty((self.n, len(self.bones)))
        for j in range(len(self.bones)):
            ab = tails[j] - heads[j]
            t = np.clip(((pts - heads[j]) @ ab) / max(ab @ ab, 1e-12), 0, 1)
            d[:, j] = np.linalg.norm(pts - (heads[j] + t[:, None] * ab), axis=1)
        distal = np.array([b.startswith(DISTAL) for b in self.bones])
        far = (d > FAR_M) & (self.W > 0) & distal[None, :]
        keep_any = ((self.W > 0) & ~far).any(1)
        rows = np.nonzero(~keep_any & far.any(1))[0]
        for i in rows:                      # nothing near: keep the nearest weighted bone
            cols = np.nonzero(self.W[i] > 0)[0]
            far[i, cols[np.argmin(d[i, cols])]] = False
        n = int(far.any(1).sum())
        self.W[far] = 0.0
        return n

    def neighbour_mean(self, W):
        acc = np.zeros_like(W)
        np.add.at(acc, self.edges[:, 0], W[self.edges[:, 1]])
        np.add.at(acc, self.edges[:, 1], W[self.edges[:, 0]])
        return acc / np.maximum(self.deg, 1)[:, None]

    def grow(self, mask):
        m = mask.copy()
        for _ in range(RINGS):
            hit = m[self.edges[:, 0]] | m[self.edges[:, 1]]
            m[self.edges[hit].ravel()] = True
        return m

    def smooth(self, region):
        W = self.W.copy()
        for _ in range(PASSES):
            W[region] = .5 * W[region] + .5 * self.neighbour_mean(W)[region]
        # Keep the four strongest influences, renormalised (Unreal's default per vertex).
        if W.shape[1] > MAX_INF:
            cut = np.argsort(W, axis=1)[:, :-MAX_INF]
            np.put_along_axis(W, cut, 0.0, axis=1)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        self.W[region] = W[region]

    def write(self):
        o = self.o
        for b in self.bones:
            g = o.vertex_groups.get(b)
            if g is None:
                g = o.vertex_groups.new(name=b)
            col = self.W[:, self.col[b]]
            on = np.nonzero(col > 1e-4)[0]
            off = np.nonzero(col <= 1e-4)[0]
            if len(off):
                g.remove(off.tolist())
            for i in on:
                g.add([int(i)], float(col[i]), "REPLACE")
        o.data.update()


def measure(gs):
    """Per garment: the most any incident edge grows (cm) per vertex, over every sampled frame."""
    rest_pose()
    rest = {g.o.name: coords(g.o) for g in gs}
    rest_len = {g.o.name: np.linalg.norm(rest[g.o.name][g.edges[:, 0]] - rest[g.o.name][g.edges[:, 1]], axis=1) for g in gs}
    worst = {g.o.name: np.zeros(g.n) for g in gs}
    where = {g.o.name: ("", 0, 0.0) for g in gs}
    for clip, f in frames():
        for g in gs:
            p = coords(g.o)
            grow = (np.linalg.norm(p[g.edges[:, 0]] - p[g.edges[:, 1]], axis=1) - rest_len[g.o.name]) * 100
            w = worst[g.o.name]
            np.maximum.at(w, g.edges[:, 0], grow)
            np.maximum.at(w, g.edges[:, 1], grow)
            if grow.max() > where[g.o.name][2]:
                where[g.o.name] = (clip, f, float(grow.max()))
    rest_pose()
    return worst, where


def push_skirt_from_pants(skirt, pants, before_pants):
    """Re-apply the trousers' weight change to the skirt where the skirt copied them (same bones, same ratio)."""
    o = skirt.o
    tree_pts = coords(pants.o)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(tree_pts))
    for i, p in enumerate(tree_pts):
        kd.insert(p, i)
    kd.balance()
    pts = coords(o)
    for i, p in enumerate(pts):
        _, j, d = kd.find(p)
        if d is None or d > .06:
            continue
        delta = pants.W[j] - before_pants[j]
        if not np.any(delta):
            continue
        row = np.zeros(len(skirt.bones))
        for b, c in pants.col.items():
            if b in skirt.col:
                row[skirt.col[b]] = delta[c]
        skirt.W[i] = np.clip(skirt.W[i] + row * (1 - min(1, d / .06)), 0, None)
        skirt.W[i] /= max(skirt.W[i].sum(), 1e-9)


gs = [Garment(o) for o in objs]
print("REFINE pruned", {g.o.name: g.pruned for g in gs}, flush=True)
for g in gs:
    g.write()
by = {g.o.name: g for g in gs}
worst, where = measure(gs)
first = {n: round(float(w.max()), 1) for n, w in worst.items()}
print("REFINE before", {n: (v, where[n][0].replace("Placeholder_", ""), where[n][1]) for n, v in first.items()}, flush=True)
best = {g.o.name: (float(worst[g.o.name].max()), g.W.copy()) for g in gs}
for r in range(ROUNDS):
    changed = False
    pants_before = by["Pants"].W.copy() if "Pants" in by else None
    for g in gs:
        hot = worst[g.o.name] > HOT_CM
        if hot.any():
            g.smooth(g.grow(hot))
            changed = True
    if "Pants" in by and "Jacket_Skirt" in by:
        push_skirt_from_pants(by["Jacket_Skirt"], by["Pants"], pants_before)
    if not changed:
        break
    for g in gs:
        g.write()
    worst, where = measure(gs)
    now = {n: round(float(w.max()), 1) for n, w in worst.items()}
    print(f"REFINE round {r + 1}", {n: (v, where[n][0].replace("Placeholder_", ""), where[n][1]) for n, v in now.items()}, flush=True)
    for g in gs:
        if now[g.o.name] < best[g.o.name][0]:
            best[g.o.name] = (now[g.o.name], g.W.copy())
for g in gs:
    g.W = best[g.o.name][1]
    g.write()
print("REFINE after", {n: round(v[0], 1) for n, v in best.items()}, "was", first, flush=True)
for m, show in saved:
    m.show_viewport = show
rig.animation_data.action = original_action
for a in actions:
    bpy.data.actions.remove(a)
if SAVE:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(compress=True)
    print("REFINE SAVED", bpy.data.filepath, flush=True)
