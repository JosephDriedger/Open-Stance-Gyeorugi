"""Measure the T-posed mesh to place joints: torso depth, limb cross-sections, finger
clusters, feet and head profiles, plus a skin-weight spread report.

Run after import_source.py (or on the rigged scene). Output: logs/analyze_mesh.txt.
Blender space: Z up, front is -Y, character's left is +X.
"""
import bmesh
import bpy
from mathutils import Vector
import rig_config as cfg

log = cfg.open_log("analyze_mesh")
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
mw = mesh.matrix_world
V = [mw @ v.co for v in mesh.data.vertices]


def r3(v):
    return tuple(round(c, 3) for c in v)


def rng(vals):
    return round(min(vals), 3), round(max(vals), 3)


log("=== TORSO depth (|x|<0.08): z -> ymin ymax")
for z100 in range(80, 172, 3):
    z = z100 / 100
    s = [v for v in V if abs(v.z - z) < 0.008 and abs(v.x) < 0.08]
    if s:
        log(z, *rng([v.y for v in s]))

log("=== LEFT LEG (x>0.02): z -> centroid, y range, x range")
for z100 in range(2, 95, 3):
    z = z100 / 100
    s = [v for v in V if abs(v.z - z) < 0.006 and 0.02 < v.x < 0.4]
    if s:
        log(z, r3(sum(s, Vector()) / len(s)), rng([v.y for v in s]), rng([v.x for v in s]))

for side, sgn in (("LEFT", 1), ("RIGHT", -1)):
    log(f"=== {side} ARM: x -> centroid, y range, z range")
    for x100 in range(12, 88, 2):
        x = sgn * x100 / 100
        s = [v for v in V if abs(v.x - x) < 0.004 and v.z > 1.2]
        if s:
            log(x, r3(sum(s, Vector()) / len(s)), rng([v.y for v in s]), rng([v.z for v in s]))


def clusters(vals, gap):
    vals = sorted(vals)
    out, cur = [], [vals[0]]
    for a in vals[1:]:
        if a - cur[-1] > gap:
            out.append(cur)
            cur = [a]
        else:
            cur.append(a)
    out.append(cur)
    return out


for side, sgn in (("LEFT", 1), ("RIGHT", -1)):
    log(f"=== {side} HAND: x -> clusters along Y [ymin..ymax z-range n]  (gaps between clusters = fingers)")
    for x1000 in range(600, 900, 8):
        x = sgn * x1000 / 1000
        s = [v for v in V if abs(v.x - x) < 0.002 and v.z > 1.2]
        if not s:
            continue
        desc = []
        for c in clusters([v.y for v in s], 0.004):
            zz = [v.z for v in s if c[0] - 1e-6 <= v.y <= c[-1] + 1e-6]
            desc.append(f"[{c[0]:.3f}..{c[-1]:.3f} z{min(zz):.3f}..{max(zz):.3f} n{len(c)}]")
        log(round(x, 3), " ".join(desc))

for side, sgn in (("LEFT", 1), ("RIGHT", -1)):
    log(f"=== {side} FOOT (z<0.2): y -> z range, x range")
    for y100 in range(-20, 20):
        y = y100 / 100
        s = [v for v in V if abs(v.y - y) < 0.004 and v.z < 0.2 and sgn * v.x > 0.02]
        if s:
            log(y, rng([v.z for v in s]), rng([v.x for v in s]))

log("=== HEAD (|x|<0.14, z>1.35): z -> y range, x range")
for z100 in range(135, 172, 2):
    z = z100 / 100
    s = [v for v in V if abs(v.z - z) < 0.005 and abs(v.x) < 0.14]
    if s:
        log(z, rng([v.y for v in s]), rng([v.x for v in s]))

if mesh.vertex_groups:
    log("=== WEIGHT SPREAD: group -> verts with w>0, w>0.1, w>0.5")
    names = {g.index: g.name for g in mesh.vertex_groups}
    stat = {i: [0, 0, 0] for i in names}
    maxinf = 0
    for v in mesh.data.vertices:
        maxinf = max(maxinf, len(v.groups))
        for g in v.groups:
            st = stat[g.group]
            st[0] += g.weight > 0
            st[1] += g.weight > 0.1
            st[2] += g.weight > 0.5
    for i, n in names.items():
        log(n, stat[i])
    log("max influences", maxinf)

bm = bmesh.new()
bm.from_mesh(mesh.data)
seen, islands = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, cnt, acc = [v], 0, Vector()
    seen.add(v.index)
    while stack:
        a = stack.pop()
        cnt += 1
        acc += mw @ a.co
        for e in a.link_edges:
            b = e.other_vert(a)
            if b.index not in seen:
                seen.add(b.index)
                stack.append(b)
    islands.append((cnt, r3(acc / cnt)))
bm.free()
islands.sort(reverse=True)
log("mesh islands:", len(islands), islands[:25])
log.close()
