"""Build the fighter's dobok and sparring gear from a MetaHuman body (replaces the Meshy shells).

The Meshy gear was fitted to the body but kept its shards, torn edges and blotchy atlas. These
garments are instead carved from the body's own surface and tailored: each vertex is a body vertex
pushed along its normal by a garment-specific ease, so every piece has clean topology, the body's skin
weights (it deforms exactly like the body underneath) and a designed shape.

    blender --background --factory-startup --python Tools/Blender/build_clean_gear.py -- Base Compact ...

Names are body types (Base = Medium). Per body it imports Resources/Models/MetaHuman/MH_Fighter<Name>_
{Body,Head}.fbx, builds Jacket, Pants, Belt, Protector, Helmet, Gloves and FootGuards, and exports
Resources/Models/Fitted/MH_Fighter<Name>_Body/SK_Fighter_<Part>.fbx (centimetres, body skeleton, same
as fit_to_body.py), then bakes the hidden face maps (hidden_face_maps.py). Textures come from
make_gear_textures.py. Everything is in metres inside Blender.

Parts
  Jacket     torso, skirt to mid-thigh and wide sleeves to the wrist; V neck with a raised collar band
  Pants      loose straight leg from the waist to the ankle
  Belt       band over the jacket, knot, two tails
  Protector  World Taekwondo trunk protector (hogu): a 2 cm contoured shell over the front and sides, V neck
             and white edge binding, white shoulder straps, back open except the straps and a tie
  Helmet     WT head gear: smooth 2.5 cm foam shell over crown, back and ears (ear holes), open face with the
             edge above the brows and cheek pieces to the jaw, chin strap
  Gloves     white fingerless gloves, padded over the knuckles, white cuff
  FootGuards WT electronic sensor socks: thin white sock, toes out, grey sensor pad on the instep, grey sole
"""
import math
import os
import sys
import traceback

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_config as cfg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE)).replace("\\", "/")
MODELS = f"{ROOT}/Resources/Models"
log = cfg.open_log("build_clean_gear")

# --- atlas patches (make_gear_textures.py): role -> UV0 --------------------------------------------
GRID = 4
ROLE_CELL = {"cloth": 0, "belt": 1, "collar": 2, "trim": 3, "team": 4, "vinyl": 5, "binding": 6, "sensor": 7, "liner": 8}
TILE = 0.05      # m of surface per weave-normal repeat (UV1)


def patch_uv(role):
    i = ROLE_CELL[role]
    return ((i % GRID + 0.5) / GRID, 1.0 - (i // GRID + 0.5) / GRID)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --- body access -----------------------------------------------------------------------------------

class Surface:
    """A skinned mesh with welded vertices (the body splits them along UV seams)."""

    def __init__(self, obj):
        bm = bmesh.new()
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
        bm.transform(obj.matrix_world)
        bm.normal_update()
        bm.verts.ensure_lookup_table()
        co = np.array([v.co[:] for v in bm.verts])
        nrm = np.array([v.normal[:] for v in bm.verts])
        keys = np.round(co * 1e5).astype(np.int64)
        canon, first, seen = np.zeros(len(co), np.int64), [], {}
        for i, k in enumerate(map(tuple, keys)):
            if k not in seen:
                seen[k] = len(first)
                first.append(i)
            canon[i] = seen[k]
        m = len(first)
        self.n = m
        self.src = np.array(first)                          # an original vertex per welded vertex
        self.co = co[self.src]
        sums = np.zeros((m, 3))
        np.add.at(sums, canon, nrm)
        ln = np.linalg.norm(sums, axis=1)
        ln[ln == 0] = 1
        self.nrm = sums / ln[:, None]
        names = [g.name for g in obj.vertex_groups]
        W = np.zeros((len(co), len(names)))
        for v in obj.data.vertices:
            for g in v.groups:
                W[v.index, g.group] = g.weight
        # Duplicates along UV seams can carry different weights (at the crotch the left- and right-leg copies
        # sit on the same spot), so a welded vertex takes their average, not just the first copy's.
        total = np.zeros((m, len(names)))
        np.add.at(total, canon, W)
        counts = np.bincount(canon, minlength=m).astype(float)
        self.names, self.W = names, total / counts[:, None]
        faces = []
        for f in bm.faces:
            ids = [int(canon[v.index]) for v in f.verts]
            if len(set(ids)) == len(ids):
                faces.append(ids)
        self.faces = faces
        nb = [set() for _ in range(m)]
        for f in faces:
            for i, a in enumerate(f):
                for b in (f[i - 1], f[(i + 1) % len(f)]):
                    nb[a].add(b)
        self.nbrs = [sorted(s) for s in nb]
        bm.free()
        self.bvh = BVHTree.FromPolygons([tuple(map(float, c)) for c in self.co], [tuple(f) for f in faces])

    def w(self, *prefixes, side=None):
        cols = [i for i, n in enumerate(self.names)
                if n.startswith(prefixes) and (side is None or n.endswith("_" + side))]
        return self.W[:, cols].sum(1) if cols else np.zeros(self.n)

    def smooth(self, field, iters, mask=None):
        if not hasattr(self, "_ea"):
            pairs = [(i, j) for i, ns in enumerate(self.nbrs) for j in ns]
            self._ea = np.array([p[0] for p in pairs], dtype=np.int64)
            self._eb = np.array([p[1] for p in pairs], dtype=np.int64)
            self._deg = np.bincount(self._ea, minlength=self.n).astype(float)
        shape = (slice(None),) + (None,) * (field.ndim - 1)
        has = self._deg > 0
        deg = np.where(has, self._deg, 1.0)[shape]
        for _ in range(iters):
            sums = np.zeros_like(field, dtype=float)
            np.add.at(sums, self._ea, field[self._eb])
            new = np.where(has[shape], 0.5 * field + 0.5 * sums / deg, field)
            field = new if mask is None else np.where(mask[shape], new, field)
        return field

    def maxfilter(self, field, iters):
        """Dilate a scalar field over the mesh graph: each vertex takes the largest value within `iters` steps."""
        self.smooth(np.zeros(self.n), 0)           # builds the edge arrays
        for _ in range(iters):
            out = field.copy()
            np.maximum.at(out, self._ea, field[self._eb])
            field = out
        return field

    def majority(self, mask, passes=2):
        for _ in range(passes):
            nxt = mask.copy()
            for i, ns in enumerate(self.nbrs):
                if ns:
                    nxt[i] = (mask[ns].sum() + mask[i]) * 2 > len(ns) + 1
            mask = nxt
        return mask

    def faces_in(self, mask):
        return [f for f in self.faces if all(mask[v] for v in f)]

    def pieces(self, faces, min_faces=60):
        """Drop small disconnected islands."""
        parent = list(range(len(faces)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        owner = {}
        for fi, f in enumerate(faces):
            for v in f:
                if v in owner:
                    parent[find(fi)] = find(owner[v])
                else:
                    owner[v] = fi
        count = {}
        for fi in range(len(faces)):
            count[find(fi)] = count.get(find(fi), 0) + 1
        return [f for fi, f in enumerate(faces) if count[find(fi)] >= min_faces]

    def boundary_dist(self, faces, steps=8):
        """Edge-steps from each vertex of a face set to its boundary (0 on the boundary)."""
        edge_count = {}
        for f in faces:
            for i, a in enumerate(f):
                b = f[(i + 1) % len(f)]
                key = (a, b) if a < b else (b, a)
                edge_count[key] = edge_count.get(key, 0) + 1
        used = {v for f in faces for v in f}
        dist = {v: steps for v in used}
        frontier = []
        for (a, b), c in edge_count.items():
            if c == 1:
                dist[a] = dist[b] = 0
                frontier += [a, b]
        d = 0
        frontier = sorted(set(frontier))
        while frontier and d < steps:
            d += 1
            nxt = []
            for v in frontier:
                for u in self.nbrs[v]:
                    if u in dist and dist[u] > d:
                        dist[u] = d
                        nxt.append(u)
            frontier = nxt
        out = np.full(self.n, float(steps))
        for v, dd in dist.items():
            out[v] = dd
        return out


def noise(p, seed=1, scale=22.0):
    """Cheap smooth 3-D noise in [-1, 1] (sum of sines): used for fabric undulation."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(p))
    for _ in range(6):
        k = rng.normal(size=3)
        k = k / np.linalg.norm(k) * scale * rng.uniform(0.6, 1.6)
        out += np.sin(p @ k + rng.uniform(0, 6.28))
    return out / 6.0 * 1.6


# --- garment assembly ------------------------------------------------------------------------------

class Part:
    """Geometry for one garment, in plain lists; weights are body weights unless overridden."""

    def __init__(self, name):
        self.name = name
        self.co, self.src, self.faces, self.roles, self.uv1_axis = [], [], [], [], []
        self.override = {}                         # new vertex -> {group name: weight}

    def add_vertex(self, p, src):
        self.co.append(np.asarray(p, float))
        self.src.append(src)
        return len(self.co) - 1

    def add_face(self, ids, role):
        self.faces.append(list(ids))
        self.roles.append(role)

    def clean(self, merge=1e-4, min_area=5e-8):
        """Merge vertices closer than `merge` metres, then drop degenerate, sliver and duplicate faces.

        Clipping can leave zero-area triangles where a cut passes through a vertex; Chaos cloth (and any
        solver) refuses meshes with them."""
        co = np.array(self.co)
        key = np.round(co / merge).astype(np.int64)

        def leg(i):                         # -1 right leg, +1 left leg, 0 neither: coincident vertices of
            w = self.override.get(i) or {}  # different legs (the crotch) must stay separate vertices
            b = sum(v for g, v in w.items() if g.endswith("_l")) - sum(v for g, v in w.items() if g.endswith("_r"))
            return 0 if abs(b) < 0.5 else (1 if b > 0 else -1)

        first, remap = {}, np.zeros(len(co), np.int64)
        for i, k in enumerate(map(tuple, key)):
            k = k + (leg(i),)
            first.setdefault(k, i)
            remap[i] = first[k]
        keep_ids = sorted(set(remap.tolist()))
        new_index = {old: n for n, old in enumerate(keep_ids)}
        seen, faces, roles = set(), [], []
        for fc, role in zip(self.faces, self.roles):
            ids = [remap[v] for v in fc]
            dedup = [v for i, v in enumerate(ids) if v != ids[i - 1]]
            if len(dedup) < 3 or len(set(dedup)) < len(dedup):
                continue
            pts = co[dedup]
            area = 0.0
            for i in range(1, len(dedup) - 1):
                area += np.linalg.norm(np.cross(pts[i] - pts[0], pts[i + 1] - pts[0])) / 2
            if area < min_area:
                continue
            sig = tuple(sorted(dedup))
            if sig in seen:
                continue
            seen.add(sig)
            faces.append([new_index[v] for v in dedup])
            roles.append(role)
        # merged vertices (e.g. left- and right-leg cloth meeting at the crotch) average their weights, so the
        # merged vertex doesn't belong wholly to one leg
        merged = {}
        for i in range(len(co)):
            w = self.override.get(i)
            if w is None:
                continue
            acc = merged.setdefault(new_index[remap[i]], [{}, 0])
            for g, val in w.items():
                acc[0][g] = acc[0].get(g, 0.0) + val
            acc[1] += 1
        self.override = {k: {g: val / n for g, val in w.items()} for k, (w, n) in merged.items()}
        self.co = [co[v] for v in keep_ids]
        self.src = [self.src[v] for v in keep_ids]
        self.faces, self.roles = faces, roles


def shell(surf, faces, out_off, in_off=None, role="cloth", role_of=None, name="shell", wall_role=None,
          pos=None, in_pos=None, nrm=None, roles=None, inner_role=None):
    """Offset body faces outward (a sheet), or between in_off and out_off (a closed padded shell).

    pos / in_pos: base positions for the outer / inner surface (default the body's own), nrm: normals.
    inner_role: role of the inside surface of a padded shell (default: same as the outside)."""
    part = Part(name)
    base = surf.co if pos is None else pos
    ibase = base if in_pos is None else in_pos
    nr = surf.nrm if nrm is None else nrm
    verts = sorted({v for f in faces for v in f})

    def add(p, v):
        i = part.add_vertex(p, v)
        row = surf.W[v]
        top = np.argsort(-row)[:8]
        part.override[i] = {surf.names[j]: float(row[j]) for j in top if row[j] > 0.01} or {"pelvis": 1.0}
        return i

    outer = {v: add(base[v] + nr[v] * out_off[v], v) for v in verts}
    inner = {}
    if in_off is not None:
        inner = {v: add(ibase[v] + nr[v] * in_off[v], v) for v in verts}
    edge_face = {}
    for fi, f in enumerate(faces):
        r = roles[fi] if roles is not None else (role_of(f) if role_of else role)
        part.add_face([outer[v] for v in f], r)
        if in_off is not None:
            part.add_face([inner[v] for v in reversed(f)], inner_role or r)
        for i, a in enumerate(f):
            b = f[(i + 1) % len(f)]
            key = (a, b) if a < b else (b, a)
            edge_face.setdefault(key, []).append((a, b, r))
    if in_off is not None:
        for entries in edge_face.values():
            if len(entries) == 1:                       # boundary edge: close it with a wall
                a, b, r = entries[0]
                part.add_face([outer[a], inner[a], inner[b], outer[b]], wall_role or r)
    return part


def to_object(part, surf, arm, coll, target, uv_scale=TILE, shade_smooth=True):
    part.clean()
    name = f"SK_Fighter_{part.name}_{target}"
    me = bpy.data.meshes.new(name)
    co = [tuple(c) for c in part.co]
    me.from_pydata(co, [], part.faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    cos = np.array(part.co)
    uv0 = me.uv_layers.new(name="UVMap")
    uv1 = me.uv_layers.new(name="UVWeave")
    loops = me.loops
    n = len(loops)
    a0, a1 = np.zeros((n, 2)), np.zeros((n, 2))
    for p in me.polygons:
        pts = cos[[loops[i].vertex_index for i in p.loop_indices]]
        nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        ax = int(np.argmax(np.abs(nrm)))
        dims = [d for d in range(3) if d != ax]
        u0 = patch_uv(part.roles[p.index])
        for li, q in zip(p.loop_indices, pts):
            a0[li] = u0
            a1[li] = (q[dims[0]] / uv_scale, q[dims[1]] / uv_scale)
        p.use_smooth = shade_smooth
    uv0.data.foreach_set("uv", a0.ravel())
    uv1.data.foreach_set("uv", a1.ravel())
    # weights
    groups = {}
    for i, s in enumerate(part.src):
        w = part.override.get(i) or {"pelvis": 1.0}
        total = sum(w.values()) or 1.0
        for g, val in w.items():
            if g not in groups:
                groups[g] = obj.vertex_groups.new(name=g)
            groups[g].add([i], val / total, 'REPLACE')
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    mwld = obj.matrix_world.copy()
    obj.parent = arm
    obj.matrix_world = mwld
    log(part.name, "->", len(part.co), "verts", len(part.faces), "faces", len(groups), "groups")
    return obj


# --- context ---------------------------------------------------------------------------------------

def unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) or 1.0)


class Ctx:
    """Shared measurements: smoothed base surfaces and the jacket's ease, which other pieces sit over."""

    def __init__(self, body_surf, head_surf, joints):
        self.B, self.H, self.J = body_surf, head_surf, joints
        B = self.B
        z = B.co[:, 2]
        pel = joints["pelvis"]
        self.hem_z = pel[2] - 0.17
        # base surfaces: smoothing the body removes anatomy (pecs, abs, calves) that cloth and pads don't follow
        self.base_cloth = B.smooth(B.co, 6)
        self.base_pad = B.smooth(B.co, 28)
        # dobok cloth hangs flat over the chest and belly: over the torso its base is the body's radius from the
        # spine axis, smoothed hard, blended back to the plain smoothed body at the shoulders and arms
        x, y = B.co[:, 0], B.co[:, 1]
        neck = joints["neck_01"]
        ya = pel[1] + (neck[1] - pel[1]) * np.clip((z - pel[2]) / (neck[2] - pel[2]), 0, 1)
        dxy = np.stack([x, y - ya], axis=1)
        rad = np.linalg.norm(dxy, axis=1)
        rad_env = B.smooth(B.maxfilter(rad, 11), 50)          # bridges pecs and belly, then smooths
        self.rad_env = rad_env
        rad_s = rad_env
        d = dxy / np.maximum(rad, 1e-6)[:, None]
        flat = np.stack([d[:, 0] * rad_s, ya + d[:, 1] * rad_s, z], axis=1)
        clav_z = joints["clavicle_l"][2]
        w_t = (1.0 - smoothstep(0.12, 0.19, np.abs(x))) * smoothstep(pel[2] - 0.25, pel[2] - 0.16, z) *             smoothstep(clav_z + 0.07, clav_z - 0.01, z)
        w_t = B.smooth(w_t, 10)
        self.base_torso_cloth = self.base_cloth * (1 - w_t)[:, None] + flat * w_t[:, None]
        nrm = B.smooth(B.nrm, 8)
        self.nrm = nrm / np.linalg.norm(nrm, axis=1)[:, None]
        # jacket ease (m): loose through the torso, flared at the skirt, wide sleeves, tighter under the arm
        ease = 0.026 + 0.010 * smoothstep(pel[2] + 0.10, self.hem_z, z)          # skirt hangs nearly straight
        for side in ("l", "r"):
            up, wr = joints[f"upperarm_{side}"], joints[f"hand_{side}"]
            axis = wr - up
            s = np.clip(((B.co - up) @ axis) / (axis @ axis), 0.0, 1.0)
            arm = B.w("upperarm", "lowerarm", side=side) > 0.5
            sleeve = 0.028 + 0.026 * s
            inward = (-np.sign(B.co[:, 0])) * B.nrm[:, 0] > 0.3
            sleeve = np.where(inward, sleeve * 0.45, sleeve)
            ease = np.where(arm, sleeve, ease)
        # the belt cinches the jacket at the waist; cloth sim then blouses it above and below
        belt_z = pel[2] + 0.058
        cinch = np.exp(-((z - belt_z) / 0.035) ** 2) * (B.w("upperarm", "lowerarm") < 0.3)
        ease = ease * (1 - cinch) + 0.010 * cinch
        ease += 0.004 * noise(B.co, 1)
        self.jacket_ease = B.smooth(ease, 16)
        # Pants base at the crotch: cloth bridges the anatomy instead of copying it. A heavily smoothed surface,
        # lifted by the (smoothed) height of the body's own protrusions so it always clears them.
        flat = B.smooth(B.co, 80)
        nflat = B.smooth(B.nrm, 40)
        nflat = nflat / np.maximum(np.linalg.norm(nflat, axis=1), 1e-9)[:, None]
        protrude = np.einsum("ij,ij->i", B.co - flat, nflat)
        lift = B.smooth(np.maximum(protrude, 0.0), 12) * 1.15 + 0.006
        bridge = flat + nflat * lift[:, None]
        wc = smoothstep(0.11, 0.03, np.abs(B.co[:, 0])) * smoothstep(pel[2] - 0.27, pel[2] - 0.17, z) *             smoothstep(pel[2] + 0.04, pel[2] - 0.04, z)
        self.base_pants = self.base_cloth + wc[:, None] * (bridge - self.base_cloth)

def clear_of(points, bvh, clearance, near=0.08):
    """Push points outside a surface by `clearance` where they are within `near` of it."""
    out = points.copy()
    for i, p in enumerate(points):
        hit = bvh.find_nearest(Vector(p))
        if hit[0] is None or hit[3] > near:
            continue
        loc, nrm = np.array(hit[0][:]), np.array(hit[1][:])
        s = float((p - loc) @ nrm)
        if s < clearance:
            out[i] = p + nrm * (clearance - s)
    return out


def smooth_zone(part, zone, iters, bvh=None, clearance=0.014):
    """Laplacian-smooth the cloth's own surface inside `zone` (a mask over part vertices), then keep it at
    least `clearance` outside the body. Removes anatomy lumps from the finished garment without moving its
    cut edges."""
    co = np.array(part.co)
    nb = [set() for _ in range(len(co))]
    for fc in part.faces:
        for i, a in enumerate(fc):
            nb[a].add(fc[i - 1])
            nb[a].add(fc[(i + 1) % len(fc)])
    idx = np.nonzero(zone)[0]
    for _ in range(iters):
        new = co.copy()
        for i in idx:
            if nb[i]:
                new[i] = 0.5 * co[i] + 0.5 * co[list(nb[i])].mean(0)
        co = new
    if bvh is not None:
        for i in idx:
            hit = bvh.find_nearest(Vector(co[i]))
            if hit[0] is None:
                continue
            loc, nr = np.array(hit[0][:]), np.array(hit[1][:])
            sd = float((co[i] - loc) @ nr)
            if sd < clearance:
                co[i] = co[i] + nr * (clearance - sd)
    part.co = list(co)


def smooth_weights(part, zone, iters):
    """Blend skin weights with neighbouring vertices inside `zone`, so a change of influence (left leg to right
    leg at the crotch) is spread over several centimetres of cloth instead of one edge."""
    nb = [set() for _ in range(len(part.co))]
    for fc in part.faces:
        for i, a in enumerate(fc):
            nb[a].add(fc[i - 1])
            nb[a].add(fc[(i + 1) % len(fc)])
    idx = [i for i in np.nonzero(zone)[0] if nb[i]]
    w = {i: dict(part.override.get(i) or {"pelvis": 1.0}) for i in range(len(part.co))}
    for _ in range(iters):
        nxt = {}
        for i in idx:
            acc = {g: v * 0.5 for g, v in w[i].items()}
            f = 0.5 / len(nb[i])
            for j in nb[i]:
                for g, v in w[j].items():
                    acc[g] = acc.get(g, 0.0) + v * f
            nxt[i] = acc
        w.update(nxt)
    for i in idx:
        top = sorted(w[i].items(), key=lambda t: -t[1])[:8]
        total = sum(v for _, v in top) or 1.0
        part.override[i] = {g: v / total for g, v in top if v / total > 0.01}


def rigidify(part, surf, arm, allowed):
    """Collapse each vertex's body weights onto the nearest allowed ancestor bone (rigid gear)."""
    parent = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}

    def up(b):
        while b is not None and b not in allowed:
            b = parent.get(b)
        return b

    for i, s in enumerate(part.src):
        row = surf.W[s]
        w = {}
        for j in np.argsort(-row)[:10]:
            if row[j] > 0.005:
                a = up(surf.names[j]) or "pelvis"
                w[a] = w.get(a, 0.0) + float(row[j])
        part.override[i] = w


class Cut(Surface):
    """A surface clipped exactly along level sets of fields.

    start(surf, gate) copies the gated faces as triangles; clip(f) then cuts along f = 0: triangles that
    straddle it are split at the crossing, so the cut is a smooth curve (not a stair-step of whole triangles
    or a saw-tooth of snapped vertices). The outside is dropped, or with keep_outside kept and marked in
    `zone` (bit k set = inside the k-th cut) so a colour change can follow the line exactly. New vertices
    carry interpolated attributes; ext(array) extends any per-vertex array of the source surface."""

    @classmethod
    def start(cls, surf, gate):
        self = cls.__new__(cls)
        self.n = surf.n
        self.names = surf.names
        self.co, self.nrm, self.W = surf.co.copy(), surf.nrm.copy(), surf.W.copy()
        self.levels = []                     # per clip: (inside ids, outside ids, t) of the vertices it added
        tris = []
        for fc in surf.faces:
            if all(gate[v] for v in fc):
                for i in range(1, len(fc) - 1):
                    tris.append((fc[0], fc[i], fc[i + 1]))
        self.faces = [list(t) for t in tris]
        self.zone = [0] * len(self.faces)
        self.nclips = 0
        self.n_src = surf.n
        return self

    def clip(self, f, keep_outside=False, min_faces=0):
        f = np.asarray(f, float)
        assert len(f) == self.n, (len(f), self.n)
        bit = 1 << self.nclips
        self.nclips += 1
        new_vertex, spec = {}, []
        n0 = self.n

        def crossing(a, b):
            key = (a, b) if a < b else (b, a)
            if key not in new_vertex:
                vin, vout = (a, b) if f[a] > 0 else (b, a)
                new_vertex[key] = n0 + len(spec)
                spec.append((vin, vout, f[vin] / (f[vin] - f[vout])))
            return new_vertex[key]

        faces, zones = [], []
        for tri, zn in zip(self.faces, self.zone):
            inside = [f[v] > 0 for v in tri]
            if all(inside):
                faces.append(tri)
                zones.append(zn | bit)
                continue
            if not any(inside):
                if keep_outside:
                    faces.append(tri)
                    zones.append(zn)
                continue
            for want in ((True, False) if keep_outside else (True,)):
                poly = []
                for k in range(3):
                    a, b = tri[k], tri[(k + 1) % 3]
                    if (f[a] > 0) == want:
                        poly.append(a)
                    if (f[a] > 0) != (f[b] > 0):
                        poly.append(crossing(a, b))
                for k in range(1, len(poly) - 1):
                    faces.append([poly[0], poly[k], poly[k + 1]])
                    zones.append(zn | (bit if want else 0))
        if spec:
            vin = np.array([q[0] for q in spec])
            vout = np.array([q[1] for q in spec])
            t = np.array([q[2] for q in spec])
            self.co = np.concatenate([self.co, self.co[vin] + (self.co[vout] - self.co[vin]) * t[:, None]])
            nr = np.concatenate([self.nrm, self.nrm[vin] + (self.nrm[vout] - self.nrm[vin]) * t[:, None]])
            self.nrm = nr / np.maximum(np.linalg.norm(nr, axis=1), 1e-9)[:, None]
            self.W = np.concatenate([self.W, self.W[vin] + (self.W[vout] - self.W[vin]) * t[:, None]])
            self.n += len(spec)
        self.levels.append((np.array([q[0] for q in spec], dtype=np.int64), np.array([q[1] for q in spec], dtype=np.int64),
                            np.array([q[2] for q in spec])))
        self.faces, self.zone = faces, zones
        if min_faces:
            keep = set(map(id, self.pieces(self.faces, min_faces)))
            pairs = [(fc, zn) for fc, zn in zip(self.faces, self.zone) if id(fc) in keep]
            self.faces = [p[0] for p in pairs]
            self.zone = [p[1] for p in pairs]
        nb = [set() for _ in range(self.n)]
        for fc in self.faces:
            for i, a in enumerate(fc):
                for b in (fc[i - 1], fc[(i + 1) % len(fc)]):
                    nb[a].add(b)
        self.nbrs = [sorted(q) for q in nb]
        for attr in ("_ea", "_eb", "_deg"):
            if hasattr(self, attr):
                delattr(self, attr)
        return self

    def ext(self, arr):
        """Extend an array defined on the source surface to every vertex added by the clips."""
        out = np.asarray(arr)
        for vin, vout, t in self.levels:
            if len(vin):
                shape = (slice(None),) + (None,) * (out.ndim - 1)
                out = np.concatenate([out, out[vin] + (out[vout] - out[vin]) * t[shape]])
        return out

    def ext_unit(self, arr):
        out = self.ext(arr)
        return out / np.maximum(np.linalg.norm(out, axis=1), 1e-9)[:, None]

    def inside(self, k):
        """Per-face flag: inside the k-th clip (0-based)."""
        return np.array([bool(z & (1 << k)) for z in self.zone])


def region(surf, f, gate, min_faces=60):
    S = Cut.start(surf, gate).clip(f, min_faces=min_faces)
    S.fe = np.maximum(S.ext(f), 0.0)         # metres to the cut, 0 on it
    return S


# --- garments --------------------------------------------------------------------------------------

def make_jacket(ctx):
    B, J = ctx.B, ctx.J
    z, x, y = B.co[:, 2], B.co[:, 0], B.co[:, 1]
    gate = (B.w("spine", "clavicle", "neck", "upperarm", "lowerarm", "pelvis", "thigh") > 0.4)
    # neckline at the base of the neck: an exact cut (a gate would leave a stair-stepped edge)
    neck_f = J["neck_01"][2] + 0.010 + 0.025 * smoothstep(0.0, 0.06, -(y - J["neck_01"][1])) - z
    gate &= neck_f > -0.06
    f = np.minimum(z - ctx.hem_z, neck_f)                    # skirt hem, neckline
    for side in ("l", "r"):
        wrist = J[f"hand_{side}"]
        axis = unit(wrist - J[f"lowerarm_{side}"])
        t = (B.co - wrist) @ (-axis)
        arm = B.w("upperarm", "lowerarm", "hand", side=side) > 0.3
        f = np.where(arm, np.minimum(f, t - 0.012), f)       # sleeves stop at the wrist
    top = float(z[gate & (neck_f > 0)].max())
    yc = J["neck_01"][1]
    apex, half = top - 0.17, 0.052                           # V neck, lapels meeting at the neck base
    g = (z - apex) - (0.17 / half) * np.abs(x)               # > 0 inside the V of the neck opening
    f = np.where(y < yc - 0.01, np.minimum(f, -g), f)
    S = region(B, f, gate, 400)
    # collar: a band along the V and the neck edge, split out so its edge is a clean line
    dist_v = np.where(y < yc - 0.01, -g * 0.29, 1.0)         # metres to the V line (front only)
    dist_top = np.where(z > top - 0.12, np.maximum(neck_f, 0.0), 1.0)    # metres below the neckline
    c_src = B.smooth(0.026 - np.minimum(dist_v, dist_top), 2)
    S.clip(S.ext(c_src), keep_outside=True)
    faces = S.faces
    in_collar = S.inside(1)
    collar_v = S.ext(c_src) > 0
    ease = S.smooth(S.ext(ctx.jacket_ease) + 0.010 * collar_v, 2)
    part = shell(S, faces, ease, roles=["collar" if in_collar[i] else "cloth" for i in range(len(faces))],
                 name="Jacket", pos=S.ext(ctx.base_torso_cloth), nrm=S.ext_unit(ctx.nrm))
    pts = np.array(part.co)
    # MetaHuman's head mesh comes down over the shoulders and upper chest: the jacket must sit outside it there
    head_low = float(ctx.H.co[:, 2].min())
    near_head = pts[:, 2] > head_low - 0.02
    pts[near_head] = clear_of(pts[near_head], ctx.H.bvh, 0.010, near=0.06)
    part.co = list(pts)
    return part


def make_pants(ctx):
    B, J = ctx.B, ctx.J
    z, x = B.co[:, 2], B.co[:, 0]
    pel, foot = J["pelvis"], J["foot_l"]
    hem, waist = foot[2] + 0.055, pel[2] + 0.05
    gate = B.w("pelvis", "thigh", "calf") > 0.4
    S = region(B, np.minimum(z - hem, waist - z), gate, 400)
    zs, xs = S.co[:, 2], S.co[:, 0]
    # loose straight leg: wide through the thigh, slightly tapered to the hem
    ease = np.interp(zs, [hem, 0.30, 0.50, 0.80, waist], [0.044, 0.042, 0.040, 0.038, 0.020])
    sgn = np.clip(xs / 0.04, -1.0, 1.0)                      # a continuous sign: no step at the centre line
    inward = smoothstep(0.15, 0.55, -sgn * S.nrm[:, 0])       # inner-thigh surfaces face the other leg
    ease = ease * (1.0 - 0.70 * inward) + 0.004 * noise(S.co, 2)
    part = shell(S, S.faces, S.smooth(ease, 8), role="cloth", name="Pants",
                 pos=S.ext(ctx.base_pants), nrm=S.ext_unit(ctx.nrm))
    pts = np.array(part.co)
    zone = (np.abs(pts[:, 0]) < 0.11) & (pts[:, 2] > pel[2] - 0.28) & (pts[:, 2] < pel[2] + 0.02)
    smooth_zone(part, zone, 30, B.bvh)                      # crotch: drape over the anatomy, don't copy it
    zw = (np.abs(pts[:, 0]) < 0.10) & (pts[:, 2] > pel[2] - 0.34) & (pts[:, 2] < pel[2] + 0.02)
    return part


def make_belt(ctx, arm):
    B, J = ctx.B, ctx.J
    z, x = B.co[:, 2], B.co[:, 0]
    pel = J["pelvis"]
    z0, z1 = pel[2] + 0.035, pel[2] + 0.080
    gate = (B.w("spine", "pelvis") > 0.4) & (np.abs(x) < 0.30)
    S = region(B, np.minimum(z - z0, z1 - z), gate, 100)
    je = S.ext(ctx.jacket_ease)
    part = shell(S, S.faces, je + 0.014, je + 0.004, role="belt", name="Belt",
                 pos=S.ext(ctx.base_torso_cloth), nrm=S.ext_unit(ctx.nrm))
    rigidify(part, S, arm, {"pelvis", "spine_01", "spine_02"})
    # knot at the front, slightly left of centre
    zk = (z0 + z1) / 2
    near = (np.abs(x) < 0.03) & (np.abs(z - zk) < 0.02)
    front_y = float(ctx.base_cloth[near, 1].min()) - float(ctx.jacket_ease[near].mean()) - 0.014
    kc = np.array([0.012, front_y - 0.012, zk])           # knot sits proud of the jacket
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
    for v in bm.verts:
        v.co = Vector((kc[0] + v.co.x * 0.032, kc[1] + v.co.y * 0.013, kc[2] + v.co.z * 0.026))
    base = len(part.co)
    for v in bm.verts:
        part.add_vertex(v.co[:], int(np.argmin(np.linalg.norm(S.co - np.array(v.co[:]), axis=1))))
    for fc in bm.faces:
        part.add_face([base + v.index for v in fc.verts], "belt")
    bm.free()
    for i in range(base, len(part.co)):
        part.override[i] = {"pelvis": 0.6, "spine_01": 0.4}
    # tails hang over the front of the jacket skirt and pants
    zt0 = kc[2] - 0.020
    for x0, x1, length, width in ((0.010, 0.036, 0.30, 0.044), (-0.012, -0.042, 0.25, 0.044)):
        rows, ids = 14, []
        for i in range(rows + 1):
            s = i / rows
            zz = zt0 - length * s
            xc = x0 + (x1 - x0) * s
            window = (np.abs(x - xc) < 0.05) & (np.abs(z - zz) < 0.03)
            y_body = float(B.co[window, 1].min()) if window.any() else front_y + 0.04   # frontmost body surface here
            j = int(np.argmin(np.abs(z - zz)))
            yy = y_body - max(float(ctx.jacket_ease[j]), 0.05) - 0.022 - 0.010 * s
            hw = width / 2 * (1.0 - 0.15 * s)
            ids.append((part.add_vertex((xc - hw, yy, zz), j), part.add_vertex((xc + hw, yy, zz), j)))
        for a, b in zip(ids[:-1], ids[1:]):
            part.add_face([a[0], b[0], b[1], a[1]], "belt")
        for pair in ids:
            for v in pair:
                part.override[v] = {"pelvis": 1.0}
    for i in range(len(part.co)):
        part.override.setdefault(i, {"pelvis": 0.6, "spine_01": 0.4})
    return part


def make_protector(ctx, arm):
    """World Taekwondo trunk protector (electronic hogu), modelled on Daedo / KP&P competition protectors.

    A contoured shell about 2 cm thick that sits on the dobok over the front and sides of the trunk, from the upper
    chest (V neck) to just over the belt, wrapping round to under the arms. White binding all round the edge, white
    webbing shoulder straps that cross to the back, and a tie across the back; the back itself is open."""
    B, J = ctx.B, ctx.J
    x, y, z = B.co[:, 0], B.co[:, 1], B.co[:, 2]
    pel, neck = J["pelvis"], J["neck_01"]

    def axis_y(zz):
        return pel[1] + (neck[1] - pel[1]) * np.clip((zz - pel[2]) / (neck[2] - pel[2]), 0, 1)

    yc = axis_y(z)
    theta = np.arctan2(x, -(y - yc))                        # 0 front, +-pi back
    a = np.abs(theta)
    ax = np.abs(x)
    z_clav = J["clavicle_l"][2]
    front_top = float(B.co[(ax < 0.03) & (y < yc) & (z > pel[2] + 0.3), 2].max())
    z_sh = z_clav + 0.012                                   # top of the panel where the straps start, at the collarbone
    z_apex = min(z_sh - 0.055, front_top - 0.020)           # bottom of the (small) V neck
    z_arm = z_clav - 0.120                                  # armhole, under the arm
    th_side = math.radians(104)                             # wraps to just behind the side seam
    radius = 0.16
    # top edge: V neck rising to the straps, then the armhole curve down to under the arm
    v_top = z_apex + (z_sh - z_apex) * np.clip(ax / 0.075, 0.0, 1.0)
    top = v_top + (z_arm - v_top) * smoothstep(math.radians(55), math.radians(92), a)
    # bottom edge: just over the belt in front, a little higher at the sides
    bottom = pel[2] + 0.055 + 0.045 * smoothstep(math.radians(25), math.radians(100), a)
    f_panel = np.minimum(np.minimum(z - bottom, top - z), (th_side - a) * radius)
    # shoulder straps (4.4 cm webbing): from the panel's top over the shoulder, down the back to the shoulder blade
    strap_x = 0.105
    f_strap = np.minimum(0.030 - np.abs(ax - strap_x), z - (z_clav - 0.175))        # 6 cm padded shoulder pieces
    f_strap = np.where((y > yc) | (z > v_top - 0.03), f_strap, -1.0)
    # back tie: a 2.4 cm strap across the back between the panel's side edges
    z_tie = pel[2] + 0.235
    f_tie = np.where(a > th_side - 0.15, 0.012 - np.abs(z - z_tie), -1.0)
    f = np.maximum(f_panel, np.maximum(f_strap, f_tie))
    gate = B.w("spine", "clavicle", "neck", "pelvis") > 0.4
    S = region(B, f, gate, 150)
    fp = S.ext(f_panel)
    S.clip(fp - 0.017, keep_outside=True)                    # 1.7 cm white binding round the panel
    faces = S.faces
    team = S.inside(1)
    fp = S.ext(f_panel)
    fe_p = np.maximum(fp, 0.0)
    on_panel = fp > -0.002
    xs, ys, zs = S.co[:, 0], S.co[:, 1], S.co[:, 2]
    ycs = axis_y(zs)
    # outer surface: the body's radius from the spine axis, smoothed hard (a moulded plate, not a cast of muscles)
    # outer plate radius: the body's envelope in (angle round the spine, height) space, blurred wide, so the plate is a
    # smooth moulded surface (no pecs, no abs) that still clears the chest everywhere
    zb = np.clip(((z - (pel[2] - 0.05)) / 0.02).astype(int), 0, 39)
    tb = np.clip(((theta + math.pi) / (2 * math.pi) * 72).astype(int), 0, 71)
    je_s = B.smooth(ctx.jacket_ease, 40)
    over = ctx.base_torso_cloth + ctx.nrm * je_s[:, None]       # the jacket's outer surface
    rad_body = np.linalg.norm(np.stack([over[:, 0], over[:, 1] - yc], axis=1), axis=1)
    grid = np.zeros((40, 72))
    np.maximum.at(grid, (zb[gate], tb[gate]), rad_body[gate])
    for _ in range(3):                                       # fill empty bins from their neighbours
        fill = np.maximum(np.maximum(np.roll(grid, 1, 1), np.roll(grid, -1, 1)), np.maximum(np.roll(grid, 1, 0), np.roll(grid, -1, 0)))
        grid = np.where(grid > 0, grid, fill)
    k_t = np.exp(-0.5 * (np.arange(-9, 10) / 3.0) ** 2)
    k_z = np.exp(-0.5 * (np.arange(-6, 7) / 2.5) ** 2)
    blur = np.zeros_like(grid)
    for i, w_ in zip(range(-9, 10), k_t):
        blur += w_ * np.roll(grid, i, 1)
    grid = blur / k_t.sum()
    pad = np.pad(grid, ((6, 6), (0, 0)), mode="edge")
    grid = sum(w_ * pad[6 + i:46 + i] for i, w_ in zip(range(-6, 7), k_z)) / k_z.sum()
    rad_plate = B.smooth(grid[zb, tb], 6)
    # where the blur dips below the body (pec peaks), lift the plate by a broad, smooth amount instead of copying them
    deficit = np.where(gate, np.maximum(rad_body + 0.003 - rad_plate, 0.0), 0.0)
    lift = B.smooth(B.maxfilter(deficit, 10), 40)
    rad_s = S.ext(rad_plate + lift)
    dxy = np.stack([xs, ys - ycs], axis=1)
    dirxy = dxy / np.maximum(np.linalg.norm(dxy, axis=1), 1e-6)[:, None]
    pos_in = S.ext(ctx.base_torso_cloth)
    pos_plate = np.stack([dirxy[:, 0] * rad_s, ycs + dirxy[:, 1] * rad_s, zs], axis=1)
    nrm_body = S.ext_unit(ctx.nrm)
    nrm_plate = np.stack([dirxy[:, 0], dirxy[:, 1], np.zeros(S.n)], axis=1)
    je = S.ext(je_s)
    inner = je + 0.004                                       # rests on the jacket
    r = smoothstep(0.0, 0.014, fe_p)                         # rounded edge over 1.4 cm
    thetas = np.arctan2(xs, -(ys - ycs))
    out = 0.004 + 0.012 * r                                  # 1.6 cm over the plate base (which already clears the jacket)
    # straps and tie: thin webbing straight on the jacket
    strap_out = np.full(S.n, 0.0045)
    w = smoothstep(-0.004, 0.004, fp)                         # panel weight, blended over a few mm at the junction
    out = w * out + (1 - w) * (je + strap_out)
    inn = w * inner + (1 - w) * (je + 0.0015)
    pos_out = pos_plate * w[:, None] + pos_in * (1 - w)[:, None]
    nrm = nrm_plate * w[:, None] + nrm_body * (1 - w)[:, None]
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1), 1e-9)[:, None]
    # the plate base sits outside the cloth base; express the inner offset against the same base
    shift = np.einsum("ij,ij->i", pos_in - pos_out, nrm)
    part = shell(S, faces, S.smooth(out, 2), inn + shift,
                 roles=["team" if team[i] else "binding" for i in range(len(faces))],
                 name="Protector", wall_role="binding", pos=pos_out, nrm=nrm, inner_role="binding")
    pts = np.array(part.co)
    hi = pts[:, 2] > z_clav - 0.06
    pts[hi] = clear_of(pts[hi], ctx.H.bvh, 0.010)
    part.co = list(pts)
    spine = {"pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05"}
    rigidify(part, S, arm, spine)                            # the plate follows the trunk only
    plate_w = dict(part.override)
    rigidify(part, S, arm, spine | {"clavicle_l", "clavicle_r"})   # straps ride the shoulders
    strap_w = dict(part.override)
    panel_src = on_panel
    for i, s in enumerate(part.src):
        part.override[i] = plate_w[i] if panel_src[s] else strap_w[i]
    return part


def helmet_base_mesh(ctx, centre, radii, n_t=200, n_a=130):
    """A dense, smooth superellipsoid shell round the skull (quads), pushed out wherever the head (ears included)
    would come through it. The helmet is cut from this instead of the head mesh, so seams and vents stay crisp."""
    H = ctx.H
    rx, ry_front, ry_back, rz_up, rz_dn = radii
    e = 2.4
    a = np.linspace(0.012, math.radians(150), n_a)           # polar angle from the top
    t = np.linspace(0, 2 * math.pi, n_t, endpoint=False)      # round the vertical axis, 0 = front (-y)
    A, T = np.meshgrid(a, t, indexing="ij")
    u = np.stack([np.sin(A) * np.sin(T), -np.sin(A) * np.cos(T), np.cos(A)], axis=-1).reshape(-1, 3)
    ry = np.where(u[:, 1] > 0, ry_back, ry_front)
    rz = np.where(u[:, 2] > 0, rz_up, rz_dn)
    s = 1.0 / ((np.abs(u[:, 0]) / rx) ** e + (np.abs(u[:, 1]) / ry) ** e + (np.abs(u[:, 2]) / rz) ** e) ** (1.0 / e)
    need = np.zeros(len(u))
    for i, d in enumerate(u):                                  # outermost head surface along each direction
        hit = H.bvh.ray_cast(Vector(centre + d * 0.5), Vector(-d), 0.5)
        if hit[0] is not None:
            need[i] = float(np.linalg.norm(np.array(hit[0][:]) - centre))
    need = need + 0.005
    grid = np.maximum(s, need).reshape(n_a, n_t)
    for _ in range(6):                                         # relax on the grid (wraps round, clamps top/bottom)
        p = np.pad(grid, ((1, 1), (0, 0)), mode="edge")
        grid = 0.5 * grid + 0.125 * (np.roll(grid, 1, 1) + np.roll(grid, -1, 1) + p[:-2] + p[2:])
    rad = np.maximum(grid.reshape(-1), need)
    co = centre + u * rad[:, None]
    co = np.vstack([co, centre + np.array([0.0, 0.0, float(rad.reshape(n_a, n_t)[0].mean())])])
    pole = len(co) - 1
    faces = []
    for i in range(n_a - 1):
        for j in range(n_t):
            k = (j + 1) % n_t
            faces.append([i * n_t + j, (i + 1) * n_t + j, (i + 1) * n_t + k, i * n_t + k])
    for j in range(n_t):
        faces.append([pole, j, (j + 1) % n_t])
    me = bpy.data.meshes.new("HelmetBase")
    me.from_pydata([tuple(c) for c in co], [], faces)
    me.update()
    obj = bpy.data.objects.new("HelmetBase", me)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name="head").add(list(range(len(co))), 1.0, 'REPLACE')
    surf = Surface(obj)
    bpy.data.objects.remove(obj, do_unlink=True)
    return surf


def make_helmet(ctx):
    """World Taekwondo head gear (Daedo / KP&P / Adidas style), modelled as moulded closed-cell foam: about 3 cm over
    the crown and 2.5 cm at the sides, a thick forehead pad, a rolled edge round the face opening and the bottom, raised
    ear guards with a central hole and vent holes, a solid crown with a moulded centre seam, cheek
    pieces to the jaw line and a chin strap."""
    H, J = ctx.H, ctx.J
    hco = H.co
    hj = J["head"]
    eye_z = 0.5 * (J["FACIAL_L_Eye"][2] + J["FACIAL_R_Eye"][2])
    chin = J["FACIAL_C_Chin"]
    cranium = hco[(hco[:, 2] > hj[2] + 0.10) & (hco[:, 2] < hj[2] + 0.16)]
    cx, cy = cranium[:, 0].mean(), cranium[:, 1].mean()
    front_z = eye_z + 0.046                                 # brow edge
    jaw_z = chin[2] + 0.030                                  # cheek pieces end at the jaw line
    nape_z = hj[2] - 0.015
    centre = np.array([cx, cy, hj[2] + 0.065])
    d = hco - centre
    sel = hco[:, 2] > hj[2] - 0.02
    radii = (float(np.abs(d[sel, 0]).max()) + 0.006, float((-d[sel & (hco[:, 2] > front_z), 1]).max()) + 0.006,
             float(d[sel, 1].max()) + 0.006, float(d[:, 2].max()) + 0.006, float(centre[2] - jaw_z) + 0.025)
    G = helmet_base_mesh(ctx, centre, radii)
    co = G.co
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    phi = np.abs(np.arctan2(x - cx, -(y - cy)))
    rim = front_z + (jaw_z - front_z) * smoothstep(math.radians(52), math.radians(72), phi)
    rim = rim + (nape_z - jaw_z) * smoothstep(math.radians(115), math.radians(160), phi)
    f = z - rim
    w_front = smoothstep(cy - 0.030, cy - 0.060, y)
    f = np.minimum(f, (w_front * (phi - math.radians(70)) + (1 - w_front)) * 0.12)
    ears = [J["FACIAL_L_Ear"] * np.array([sgn, 1, 1]) for sgn in (1.0, -1.0)]
    for ear in ears:                                         # ear guard: central hole and three vent holes round it
        side = (x - cx) * np.sign(ear[0] - cx) > 0
        dd = np.linalg.norm(co - ear, axis=1)
        f = np.where(side, np.minimum(f, dd - 0.014), f)
        for ang in (math.radians(55), math.radians(150), math.radians(245)):
            c = ear + 0.028 * (math.cos(ang) * np.array([0.0, 0.0, 1.0]) + math.sin(ang) * np.array([0.0, -1.0, 0.0])) \
                + np.array([np.sign(ear[0]) * 0.01, 0.0, 0.0])
            f = np.where(side, np.minimum(f, np.linalg.norm(co - c, axis=1) - 0.0045), f)
    S = region(G, f, np.ones(G.n, bool), 300)
    fe = S.fe
    xs, ys, zs = S.co[:, 0], S.co[:, 1], S.co[:, 2]
    phis = np.abs(np.arctan2(xs - cx, -(ys - cy)))
    r = smoothstep(0.0, 0.014, fe)
    crown = smoothstep(hj[2] + 0.05, hj[2] + 0.15, zs)
    out = (0.008 + 0.016 * r) + 0.006 * crown * r            # 2.4 cm sides, 3 cm crown
    out += 0.0035 * np.exp(-((fe - 0.010) / 0.0050) ** 2)     # rolled edge
    wf = smoothstep(math.radians(62), math.radians(40), phis)
    pad = wf * smoothstep(front_z + 0.012, front_z + 0.022, zs) * smoothstep(front_z + 0.085, front_z + 0.072, zs)
    out += 0.008 * pad * r                                   # forehead pad
    out -= 0.004 * wf * np.exp(-((zs - (front_z + 0.081)) / 0.0035) ** 2) * r
    out -= 0.0018 * np.exp(-((xs - cx) / 0.004) ** 2) * crown * (1 - wf) * r           # moulded centre seam
    for ear in ears:
        de = np.linalg.norm(S.co - ear, axis=1)
        guard = smoothstep(0.046, 0.038, de)
        out += 0.006 * guard * smoothstep(0.0, 0.006, fe)    # raised ear guard
        out -= 0.003 * np.exp(-((de - 0.048) / 0.0028) ** 2) * r
    out = S.smooth(out, 1)
    part = shell(S, S.faces, out, np.zeros(S.n), role="team", name="Helmet", wall_role="team",
                 pos=S.co, nrm=S.nrm, inner_role="liner")
    # chin strap: from the bottom of each cheek piece under the chin
    for sgn in (1, -1):
        ear = J["FACIAL_L_Ear"] * np.array([sgn, 1, 1])
        path = [np.array([ear[0] * 0.93, ear[1] - 0.040, jaw_z + 0.010]),
                np.array([0.045 * sgn, chin[1] + 0.020, chin[2] - 0.006]),
                np.array([0.002 * sgn, chin[1] + 0.006, chin[2] - 0.012])]
        pts = []
        for p0, p1 in zip(path[:-1], path[1:]):
            pts += [p0 + (p1 - p0) * tt for tt in np.linspace(0, 1, 8, endpoint=False)]
        pts.append(path[-1])
        proj = []
        for p in pts:
            hit = H.bvh.find_nearest(Vector(p))
            loc, nr = np.array(hit[0][:]), np.array(hit[1][:])
            proj.append((loc + nr * 0.004, nr))
        rows = []
        for i, (p, n) in enumerate(proj):
            tang = unit(proj[min(i + 1, len(proj) - 1)][0] - proj[max(i - 1, 0)][0])
            side = unit(np.cross(tang, n))
            rows.append((part.add_vertex(p - side * 0.010, 0), part.add_vertex(p + side * 0.010, 0)))
        for p0, p1 in zip(rows[:-1], rows[1:]):
            part.add_face([p0[0], p1[0], p1[1], p0[1]], "trim")
    for i in range(len(part.co)):
        part.override[i] = {"head": 1.0}
    return part


def make_footguards(ctx, side):
    """World Taekwondo electronic sensor sock: thin white fabric over the foot from above the ankle bone to the
    ball of the foot (toes out), with a grey sensor pad on the instep and a grey sole."""
    B, J = ctx.B, ctx.J
    z = B.co[:, 2]
    foot, ball = J[f"foot_{side}"], J[f"ball_{side}"]
    fwd = unit(np.array([ball[0] - foot[0], ball[1] - foot[1], 0.0]))
    lat_dir = np.array([-fwd[1], fwd[0], 0.0])
    along = (B.co - foot) @ fwd
    along_ball = (ball - foot) @ fwd
    lat = (B.co - foot) @ lat_dir
    near_foot = (np.abs(B.co[:, 0] - foot[0]) < 0.10) & (np.linalg.norm(B.co - foot, axis=1) < 0.30) & \
                (B.w("thigh", side=side) < 0.3)
    gate = near_foot
    # toes out: the sock ends on a line across the ball of the foot, a little further forward underneath
    f = np.minimum(foot[2] + 0.080 - z, along_ball + 0.006 + 0.012 * smoothstep(foot[2] - 0.035, foot[2] - 0.060, z) - along)
    S = region(B, f, gate, 100)
    nz = S.nrm[:, 2]
    a_s, l_s = S.ext(along), S.ext(lat)
    f_pad = np.minimum(np.minimum(a_s - 0.030, along_ball - 0.020 - a_s), 0.034 - np.abs(l_s))
    f_pad = np.minimum(f_pad, (nz - 0.30) * 0.08)            # top of the foot only, with a smooth edge
    S.clip(f_pad, keep_outside=True)                          # instep sensor pad
    pad = S.inside(1)
    nz = S.nrm[:, 2]
    sole_v = nz < -0.55
    roles = []
    for i, fc in enumerate(S.faces):
        if pad[i]:
            roles.append("sensor")
        elif all(sole_v[v] for v in fc):
            roles.append("sensor")
        else:
            roles.append("binding")
    padv = np.zeros(S.n)
    for i, fc in enumerate(S.faces):
        if pad[i]:
            padv[fc] = 1.0
    padv = S.smooth(padv, 3)
    thick = 0.0030 + 0.0045 * padv
    return shell(S, S.faces, S.smooth(thick, 2), np.full(S.n, 0.0008), roles=roles,
                 name=f"FootGuards_{side}", wall_role="binding", pos=S.ext(B.smooth(B.co, 2)), nrm=S.ext_unit(ctx.nrm))


def make_gloves(ctx):
    """WT fingerless glove: white, padded over the back of the hand and the knuckles, white cuff."""
    B, J = ctx.B, ctx.J
    parts = []
    for side, sign in (("l", 1), ("r", -1)):
        wrist = J[f"hand_{side}"]
        axis = unit(wrist - J[f"lowerarm_{side}"])
        rel = B.co - wrist
        t_up = rel @ (-axis)                                  # + up the forearm from the wrist joint
        radial = np.linalg.norm(rel - np.outer(rel @ axis, axis), axis=1)
        bases = [J[f"{b}_{side}"] for b in ("index_01", "middle_01", "ring_01", "pinky_01")]
        u = unit(np.mean(bases, axis=0) - wrist)
        reach = float(np.linalg.norm(np.mean(bases, axis=0) - wrist))
        along = rel @ u
        across = np.linalg.norm(rel - np.outer(along, u), axis=1)
        on_side = (B.co[:, 0] * sign) > 0
        hand_f = np.minimum(np.minimum(along + 0.010, reach + 0.030 - along), 0.075 - across)
        hand_ok = on_side & (B.w("hand", "thumb_01", "index", "middle", "ring", "pinky", side=side) > 0.12)
        cuff_f = np.minimum(np.minimum(0.085 - t_up, t_up + 0.015), 0.070 - radial)
        cuff_ok = on_side & (B.w("lowerarm", "hand", side=side) > 0.2)
        f = np.where(cuff_ok & ~hand_ok, cuff_f, np.where(hand_ok & ~cuff_ok, hand_f, np.maximum(hand_f, cuff_f)))
        gate = hand_ok | cuff_ok
        S = region(B, f, gate, 200)
        S.clip(S.ext(t_up), keep_outside=True)              # cuff above the wrist joint, hand below it
        cuff = S.inside(1)
        # back of the hand: normals facing away from the palm (in the reference A pose, outward from the body)
        dorsal = smoothstep(0.25, 0.65, S.nrm[:, 0] * sign) * smoothstep(-0.01, 0.02, -S.ext(t_up)) * \
            smoothstep(0.0, 0.025, np.maximum(S.ext(f), 0.0))
        dorsal = S.smooth(dorsal, 3)
        thick = np.where(S.ext(t_up) > 0, 0.0050, 0.0045) + 0.0075 * dorsal
        parts.append(shell(S, S.faces, S.smooth(thick, 2), roles=["binding" if cuff[i] else "vinyl" for i in range(len(S.faces))],
                           name=f"Gloves_{side}", pos=S.co, nrm=S.nrm))
    return merge_parts("Gloves", parts)


def merge_parts(name, parts):
    out = Part(name)
    for p in parts:
        base = len(out.co)
        out.co += p.co
        out.src += p.src
        out.roles += p.roles
        out.faces += [[base + i for i in fc] for fc in p.faces]
        out.override.update({base + k: v for k, v in p.override.items()})
    return out


# --- cloth drape -------------------------------------------------------------------------------------

def drape(obj, colliders, pin, frames=48, bending=1.2, mass=0.25, log_name=""):
    """Settle a garment on the body with Blender cloth: gravity, collisions with the body, head and rigid gear, the
    `pin` vertices (a bool array over the mesh) held where they are. The result is baked into the mesh, so the export
    is plain skinned geometry with real folds. Skin weights stay those of the body vertex each cloth vertex came
    from."""
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.frame_set(1)
    added = []
    for c in colliders:
        if not any(m.type == 'COLLISION' for m in c.modifiers):
            c.modifiers.new("Collision", 'COLLISION')
            added.append(c)
        c.collision.thickness_outer = 0.004
        c.collision.cloth_friction = 8.0
        c.collision.damping = 0.6
    vg = obj.vertex_groups.new(name="DrapePin")
    vg.add([int(i) for i in np.nonzero(pin)[0]], 1.0, 'REPLACE')
    mod = obj.modifiers.new("Cloth", 'CLOTH')
    st = mod.settings
    st.quality = 8
    st.mass = mass
    st.tension_stiffness = st.compression_stiffness = 25.0
    st.shear_stiffness = 10.0
    st.bending_stiffness = bending
    st.air_damping = 2.0
    st.vertex_group_mass = "DrapePin"
    st.pin_stiffness = 1.0
    cs = mod.collision_settings
    cs.distance_min = 0.004
    cs.collision_quality = 4
    cs.use_self_collision = True
    cs.self_distance_min = 0.003
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    for f in range(1, frames + 1):
        scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    inv = obj.matrix_world.inverted()
    co = [inv @ (ev.matrix_world @ v.co) for v in me.vertices]
    before = np.array([v.co[:] for v in obj.data.vertices])
    ev.to_mesh_clear()
    obj.modifiers.remove(mod)
    # a light relax removes the odd spike a collision step leaves, without flattening the folds
    arr = np.array([c[:] for c in co])
    nb = [[] for _ in range(len(arr))]
    for e in obj.data.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    free = ~np.asarray(pin, bool)
    for _ in range(2):
        avg = np.array([arr[n].mean(0) if n else arr[i] for i, n in enumerate(nb)])
        arr = np.where(free[:, None], 0.6 * arr + 0.4 * avg, arr)
    for v, c in zip(obj.data.vertices, arr):
        v.co = c
    obj.data.update()
    obj.vertex_groups.remove(vg)
    for c in added:
        for m in list(c.modifiers):
            if m.type == 'COLLISION':
                c.modifiers.remove(m)
    moved = np.linalg.norm(np.array([v.co[:] for v in obj.data.vertices]) - before, axis=1)
    scene.frame_set(1)
    log("drape", log_name, "verts", len(moved), "moved mean/max (cm)", round(float(moved.mean()) * 100, 2),
        round(float(moved.max()) * 100, 2))


# --- build, export ---------------------------------------------------------------------------------

def add_weave_uv(obj, tile=TILE):
    """Planar-projected UV1 for the weave normal map on a mesh that doesn't have one."""
    me = obj.data
    if "UVWeave" in me.uv_layers:
        return
    layer = me.uv_layers.new(name="UVWeave")
    co = np.array([v.co[:] for v in me.vertices])
    out = np.zeros((len(me.loops), 2))
    for p in me.polygons:
        pts = co[[me.loops[i].vertex_index for i in p.loop_indices]]
        ax = int(np.argmax(np.abs(np.cross(pts[1] - pts[0], pts[2] - pts[0]))))
        dims = [d for d in range(3) if d != ax]
        for li, q in zip(p.loop_indices, pts):
            out[li] = (q[dims[0]] / tile, q[dims[1]] / tile)
    layer.data.foreach_set("uv", out.ravel())


def import_fbx(path, coll):
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
    before = set(bpy.data.objects)
    # keep leaf bones: in a MetaHuman body skeleton "head" is a leaf, and the helmet binds to it
    bpy.ops.import_scene.fbx(filepath=path, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


def cloth_base_surface(body, head, joints, coll):
    """Body + the head mesh's skin below the jaw (neck, shoulders, upper chest), joined and welded at the seam."""
    chin_z = joints["FACIAL_C_Chin"][2]
    cb = body.copy()
    cb.data = body.data.copy()
    cb.name = "ClothBase"
    coll.objects.link(cb)
    hb = head.copy()
    hb.data = head.data.copy()
    coll.objects.link(hb)
    bm = bmesh.new()
    bm.from_mesh(hb.data)
    mw = hb.matrix_world
    doomed = [f for f in bm.faces if f.material_index != 0 or any((mw @ v.co).z > chin_z - 0.02 for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(hb.data)
    bm.free()
    for o in (cb, hb):
        for m in list(o.modifiers):
            o.modifiers.remove(m)
    with bpy.context.temp_override(active_object=cb, selected_editable_objects=[cb, hb], object=cb):
        bpy.ops.object.join()
    bm = bmesh.new()
    bm.from_mesh(cb.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0006)
    bm.to_mesh(cb.data)
    bm.free()
    cb.data.update()
    log("cloth base", len(cb.data.vertices), "verts (body + head neck and shoulders)")
    return cb


def build(name):
    target = f"MH_Fighter{name}_Body"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = bpy.data.collections.new(f"Target_{target}")
    bpy.context.scene.collection.children.link(coll)
    new = import_fbx(f"{MODELS}/MetaHuman/MH_Fighter{name}_Body.fbx", coll)
    tgt_arm = next(o for o in new if o.type == 'ARMATURE')
    tgt_body = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    head_new = import_fbx(f"{MODELS}/MetaHuman/MH_Fighter{name}_Head.fbx", coll)
    head_arm = next(o for o in head_new if o.type == 'ARMATURE')
    head_mesh = max((o for o in head_new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    joints = {}
    for a in (head_arm, tgt_arm):                        # body skeleton wins for shared bones
        for b in a.data.bones:
            joints[b.name] = np.array((a.matrix_world @ b.head_local)[:])
    log(target, "body", len(tgt_body.data.vertices), "head", len(head_mesh.data.vertices))

    # Cloth base surface = the body plus the head mesh's neck and shoulders: a MetaHuman body stops at the upper chest
    # and shoulders, where the head mesh takes over, so a jacket carved from the body alone has no collar or yoke.
    cloth_base = cloth_base_surface(tgt_body, head_mesh, joints, coll)
    B, H = Surface(cloth_base), Surface(head_mesh)
    bpy.data.objects.remove(cloth_base, do_unlink=True)
    ctx = Ctx(B, H, joints)
    built = {
        "Jacket": make_jacket(ctx),
        "Pants": make_pants(ctx),
        "Belt": make_belt(ctx, tgt_arm),
        "Protector": make_protector(ctx, tgt_arm),
        "Helmet": make_helmet(ctx),
        "FootGuards": merge_parts("FootGuards", [make_footguards(ctx, "l"), make_footguards(ctx, "r")]),
        "Gloves": make_gloves(ctx),
    }
    objs = []
    for pname, part in built.items():
        shade = True
        objs.append((pname, to_object(part, None, tgt_arm, coll, target, shade_smooth=shade)))
    by = dict(objs)
    # cloth: pants first (held at the waistband), then the jacket over them (held under the belt), both settling
    # against the body, the head (which covers the shoulders) and the rigid gear on top of them
    pel = joints["pelvis"]
    pz = np.array([(by["Pants"].matrix_world @ v.co).z for v in by["Pants"].data.vertices])
    drape(by["Pants"], [tgt_body, by["FootGuards"]], pz > pel[2] + 0.020, bending=4.0, mass=0.30, log_name="Pants")
    jac = by["Jacket"]
    jz = np.array([(jac.matrix_world @ v.co).z for v in jac.data.vertices])
    gi = [g.index for g in jac.vertex_groups if g.name.startswith(("upperarm", "lowerarm", "hand"))]
    arm_w = np.array([sum(g.weight for g in v.groups if g.group in gi) for v in jac.data.vertices])
    # held under the belt, and at the yoke: the shoulders and collar carry a real jacket; the rest hangs and folds
    yoke = (jz > joints["clavicle_l"][2] - 0.035) & (arm_w < 0.5)
    jxy = np.array([(jac.matrix_world @ v.co)[:2] for v in jac.data.vertices])
    under_knot = (np.abs(jxy[:, 0]) < 0.075) & (jxy[:, 1] < pel[1]) & (jz < pel[2] + 0.07)   # flat under the knot and tails
    drape(jac, [tgt_body, head_mesh, by["Pants"], by["Protector"], by["Gloves"]],
          (np.abs(jz - (pel[2] + 0.058)) < 0.016) | yoke | under_knot, bending=3.0, log_name="Jacket")

    # export (same options as fit_to_body.py: centimetres, body skeleton named root)
    out_dir = os.path.join(cfg.OUTPUT_DIR, "Fitted", target)
    os.makedirs(out_dir, exist_ok=True)
    arms = {a: a.name for a in (tgt_arm, head_arm)}
    for a, n in arms.items():
        a.name = f"tmp_{n}"
    tgt_arm.name = "root"
    for pname, obj in objs:
        for o in bpy.data.objects:
            if o.name in bpy.context.view_layer.objects:
                o.select_set(o in (tgt_arm, obj))
        bpy.context.view_layer.objects.active = tgt_arm
        final = os.path.join(out_dir, f"SK_Fighter_{pname}.fbx")
        tmp = final[:-4] + ".tmp.fbx"                 # write aside, then swap in: scanners/sync tools can hold the file
        bpy.ops.export_scene.fbx(
            filepath=tmp, use_selection=True,
            object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
            axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', use_mesh_modifiers=False,
            add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
            armature_nodetype='NULL', bake_anim=False, path_mode='COPY', embed_textures=False)
        for attempt in range(10):
            try:
                os.replace(tmp, final)
                break
            except OSError:
                if attempt == 9:
                    raise
                import time
                time.sleep(2.0)
        log("exported", pname)
    for a, n in arms.items():
        a.name = f"tmp_restore_{n}"
    for a, n in arms.items():
        a.name = n

    # hidden face maps for the skin the garments cover
    p = f"{HERE}/hidden_face_maps.py"
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"),
         {"__name__": "__main__", "__file__": p, "TARGET_NAME": target})
    if os.environ.get("OPEN_STANCE_SAVE_PREVIEW"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"CleanGear_{name}.blend"), copy=True)


def main():
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = names or ["Base", "Compact", "Stocky", "LeanTall", "Tall"]
    status = f"{ROOT}/Saved/Logs/build_clean_gear_status.txt"
    open(status, "w").close()
    for name in names:
        try:
            build(name)
            msg = f"{name}: done"
        except Exception:
            msg = f"{name}: ERROR\n{traceback.format_exc()}"
        with open(status, "a") as f:
            f.write(msg + "\n")
    with open(status, "a") as f:
        f.write("ALL DONE\n")


if __name__ == "__main__":
    main()
