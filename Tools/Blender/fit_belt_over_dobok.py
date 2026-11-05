"""Layer 6 of the traditional dobok: tie the belt over the finished jacket, cinching the loose jacket in at the waist.

A dobok belt is tied tight: it sits on the trouser waistband with only the jacket fabric between, and the loose, boxy
jacket is gathered in under it (blousing above and below). So:
  1. the waistband moves, per angle, to sit on the trousers plus CINCH_FABRIC for the jacket layers under it;
  2. the jacket, its skirt and the collar band are drawn in under the band, fading out over FALLOFF above and below;
  3. the knot and each tail move as rigid pieces to rest on the cinched jacket front (and at least with the band).
Rest-pose positions; the belt pieces are skinned to the pelvis, so the fit holds in every pose.

    blender.exe -b <Candidate.blend> -P fit_belt_over_dobok.py -- <out folder>
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
UNDER = 'Pants'
CINCHED = ('Jacket', 'Jacket_Skirt', 'Jacket_Collar')
BAND, KNOT, TAILS = 'Belt_Waistband', 'Belt', ('Belt_Tail_Left', 'Belt_Tail_Right')
CINCH_FABRIC = .012  # m of jacket (two layers at the front overlap) between trousers and belt
CLEARANCE = .003
FALLOFF = .07        # m above and below the band over which the gathered jacket eases back out
TORSO_REACH = .27    # m from the waist centre: anything further out at belt height is an arm
BINS = 180

pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()


def world_points(name):
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


band_points = world_points(BAND)
band_low, band_high = min(p.z for p in band_points), max(p.z for p in band_points)
centre = Vector((sum(p.x for p in band_points) / len(band_points), sum(p.y for p in band_points) / len(band_points), 0))


def polar(p):
    return math.atan2(p.y - centre.y, p.x - centre.x), math.hypot(p.x - centre.x, p.y - centre.y)


def bin_of(angle):
    return int((angle + math.pi) / (2 * math.pi) * BINS) % BINS


def ring_fill(values, smooth=6):
    for _ in range(BINS):
        if all(v is not None for v in values):
            break
        values = [v if v is not None else (values[i - 1] if values[i - 1] is not None else values[(i + 1) % BINS])
                  for i, v in enumerate(values)]
    values = [v or 0.0 for v in values]
    for _ in range(smooth):
        values = [(values[i - 1] + 2 * values[i] + values[(i + 1) % BINS]) / 4 for i in range(BINS)]
    return values


def move(name, offset_of):
    obj = bpy.data.objects[name]
    inverse = obj.matrix_world.inverted().to_3x3()
    keys = obj.data.shape_keys.key_blocks if obj.data.shape_keys else []
    moved = 0.0
    for i, v in enumerate(obj.data.vertices):
        offset = offset_of(obj.matrix_world @ v.co)
        local = inverse @ offset
        v.co += local
        for key in keys:
            key.data[i].co += local
        moved = max(moved, offset.length)
    obj.data.update()
    return moved


def radial(p, amount):
    d = Vector((p.x - centre.x, p.y - centre.y, 0))
    return d.normalized() * amount if d.length > 1e-6 else Vector()


# 1. Waistband on the trousers plus the jacket fabric.
trousers = [None] * BINS
for p in world_points(UNDER):
    if band_low - .005 <= p.z <= band_high + .005:
        a, r = polar(p)
        k = bin_of(a)
        trousers[k] = r if trousers[k] is None else max(trousers[k], r)
trousers = ring_fill(trousers, 3)
inner = [None] * BINS
for p in band_points:
    a, r = polar(p)
    k = bin_of(a)
    inner[k] = r if inner[k] is None else min(inner[k], r)
inner = ring_fill(inner, 0)
push = ring_fill([trousers[k] + CINCH_FABRIC + CLEARANCE - inner[k] for k in range(BINS)])
report = {'band_offset_mm': [round(min(push) * 1000, 1), round(max(push) * 1000, 1)]}
move(BAND, lambda p: radial(p, push[bin_of(polar(p)[0])]))
band_inner = [inner[k] + push[k] for k in range(BINS)]

# 2. Gather the jacket layers in under the band.
def outward_thickness(obj):
    """How far a Solidify adds material outside the mesh surface (Blender offset +1 is fully outside, -1 fully inside)."""
    return sum(m.thickness * (1 + m.offset) / 2 for m in obj.modifiers if m.type == 'SOLIDIFY' and m.show_render)


def gather(p, extra=0.0):
    a, r = polar(p)
    if r > TORSO_REACH:
        return Vector()
    if band_low <= p.z <= band_high:
        w = 1.0
    else:
        gap = band_low - p.z if p.z < band_low else p.z - band_high
        w = max(0.0, 1 - gap / FALLOFF)
        w = w * w * (3 - 2 * w)
    excess = r - (band_inner[bin_of(a)] - CLEARANCE - extra)
    return radial(p, -excess * w) if excess > 0 and w > 0 else Vector()


for name in CINCHED:
    if bpy.data.objects.get(name):
        # a garment's outer thickness must stay under the band too (the collar band's showed through it as a tab)
        extra = outward_thickness(bpy.data.objects[name])
        report[name + '_gathered_mm'] = round(move(name, lambda p, e=extra: gather(p, e)) * 1000, 1)

# 3. Knot and tails rest on the gathered jacket front.
reach = {}
for name in CINCHED + (UNDER,):
    if not bpy.data.objects.get(name):
        continue
    for p in world_points(name):
        a, r = polar(p)
        if r <= TORSO_REACH:
            key = (bin_of(a), int(p.z * 100))
            reach[key] = max(reach.get(key, 0.0), r)


def needed(p):
    a, r = polar(p)
    k, z = bin_of(a), int(p.z * 100)
    best = max((reach.get(((k + dk) % BINS, z + dz), 0.0) for dk in (-1, 0, 1) for dz in (-1, 0, 1)), default=0.0)
    return best + CLEARANCE - r


def add_reach(name):
    for p in world_points(name):
        a, r = polar(p)
        if r <= TORSO_REACH:
            key = (bin_of(a), int(p.z * 100))
            reach[key] = max(reach.get(key, 0.0), r)


# The knot sits on the band's outer face, and the tails come out over the knot: each piece clears the ones placed before
# it (left inside the band, the knot was hidden and the tails started behind it).
add_reach(BAND)
for name in (KNOT,) + TAILS:
    if name in TAILS and name == TAILS[0]:
        add_reach(KNOT)
    pts = world_points(name)
    middle = sum(pts, Vector()) / len(pts)
    amount = max(needed(p) for p in pts)          # signed: in or out, so it rests on the jacket
    amount = max(amount, push[bin_of(polar(middle)[0])] if amount < 0 else amount)
    offset = radial(middle, amount)
    report[name + '_moved_mm'] = round(move(name, lambda p, o=offset: o) * 1000 * (1 if amount >= 0 else -1), 1)


# 4. The tails hang straight down from the knot. Modelled sloping forward (to clear the old flared skirt), they stood
#    8 cm out from the body, which a turned stance shows as a sideways splay. Each tail keeps its width and twist (every
#    point's offset from the tail's own centreline at its height) but its centreline drops plumb from the top, and only
#    where that would touch the jacket is it eased out to rest on it.
def hang_plumb(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        return 0.0
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]  # raw mesh: the evaluated one carries Solidify
    by_height = defaultdict(list)
    for p in pts:
        by_height[int(p.z * 100)].append(p)
    line = {k: sum(v, Vector()) / len(v) for k, v in by_height.items()}
    top = line[max(line)]
    inverse = obj.matrix_world.inverted()
    worst = 0.0
    for v, p in zip(obj.data.vertices, pts):
        c = line[int(p.z * 100)]
        q = Vector((top.x + p.x - c.x, top.y + p.y - c.y, p.z))
        out = needed(q)
        if out > 0:
            q = q + radial(q, out)
        worst = max(worst, (q - p).length)
        v.co = inverse @ q
    obj.data.update()
    return worst


for name in TAILS:
    report[name + '_plumbed_mm'] = round(hang_plumb(name) * 1000, 1)
rig.data.pose_position = pose_position
print('BELT DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'belt_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
