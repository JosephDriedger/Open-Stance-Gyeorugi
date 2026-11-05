"""Layer 7 of the traditional dobok: strap the chest protector (hogu) on over the jacket and belt, and press the jacket in under it.

A sparring fighter wears the hogu over the dobok, strapped tight, so the jacket lies flat beneath it. The loosened, boxy
jacket would otherwise poke through the protector's sides and cover its shoulder yoke. This switches the protector and
headgear on, then for every jacket and collar-band vertex casts a ray inward (against the garment's outward normal): if
it meets the protector within REACH, the vertex sits outside the protector there and is pulled to CLEARANCE (plus the
garment's own outer thickness) inside the protector's surface. The pull is smoothed over the neighbouring vertices so the
jacket eases out from under the protector's edges instead of creasing there.

    blender.exe -b <Candidate.blend> -P fit_protector_over_dobok.py -- <out folder>
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
PROTECTORS = ('Quilted_Lace_Back__', 'Smooth_Buckle_Back__')
PRESSED = ('Jacket', 'Jacket_Collar')
CLEARANCE = .005
REACH = .05          # m: a protector this far inside a jacket point means the jacket is lying outside it
SMOOTH = 12
HEM_BELOW_BELT = .045  # m: the protector's front hem hangs this far below the belt's lower edge (WT sparring kit)
PIVOT_Z = 1.20         # m: the chest above this stays put; the panel below it stretches down
BELT_CLEARANCE = .006  # m: the overhang clears the band and knot by this much
FLARE_RISE = .12       # m above the belt over which the overhang tilts back in to the chest

rig['Wear_Protector'] = True
rig['Wear_Helmet'] = True
rig.update_tag()
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
scene.frame_set(scene.frame_current)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()

worn = [obj for obj in scene.objects
        if obj.type == 'MESH' and obj.name.startswith(PROTECTORS) and not obj.hide_get() and not obj.hide_render]


def world_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def shift(obj, offset_of):
    inverse = obj.matrix_world.inverted().to_3x3()
    keys = obj.data.shape_keys.key_blocks if obj.data.shape_keys else []
    for i, v in enumerate(obj.data.vertices):
        local = inverse @ offset_of(obj.matrix_world @ v.co)
        v.co += local
        for key in keys:
            key.data[i].co += local
    obj.data.update()


# WT protectors hang their lower panel down over the belt (the knot and tails come out from under it). Lengthen the
# panel below mid-chest so the hem ends HEM_BELOW_BELT under the belt, then flare the overhang out over the band and
# knot, tilting in gradually above them.
belt_parts = [bpy.data.objects[n] for n in ('Belt_Waistband', 'Belt') if bpy.data.objects.get(n)]
if belt_parts:
    belt_points = [p for obj in belt_parts for p in world_points(obj)]
    belt_low, belt_high = min(p.z for p in belt_points), max(p.z for p in belt_points)
    front_hem = min(p.z for obj in worn for p in world_points(obj) if p.y < -.05)
    drop = max(0.0, front_hem - (belt_low - HEM_BELOW_BELT))
    centre = sum(belt_points, Vector()) / len(belt_points)
    centre.z = 0

    def polar(p):
        return math.atan2(p.y - centre.y, p.x - centre.x), math.hypot(p.x - centre.x, p.y - centre.y)

    for obj in worn:
        shift(obj, lambda p: Vector((0, 0, -drop * max(0.0, min(1.0, (PIVOT_Z - p.z) / (PIVOT_Z - front_hem))))))
    reach = [0.0] * 72
    for p in belt_points:
        a, r = polar(p)
        k = int((a + math.pi) / (2 * math.pi) * 72) % 72
        reach[k] = max(reach[k], r)
    reach = [max(reach[i - 1], reach[i], reach[(i + 1) % 72]) for i in range(72)]
    need = [0.0] * 72
    for obj in worn:
        for p in world_points(obj):
            if p.z <= belt_high + .005:
                a, r = polar(p)
                k = int((a + math.pi) / (2 * math.pi) * 72) % 72
                need[k] = max(need[k], reach[k] + BELT_CLEARANCE - r)
    for _ in range(3):
        need = [max(need[i], (need[i - 1] + 2 * need[i] + need[(i + 1) % 72]) / 4) for i in range(72)]

    def flare(p):
        a, r = polar(p)
        w = max(0.0, min(1.0, 1 - (p.z - belt_high) / FLARE_RISE))
        w = w * w * (3 - 2 * w)
        k = int((a + math.pi) / (2 * math.pi) * 72) % 72
        d = Vector((p.x - centre.x, p.y - centre.y, 0))
        return d.normalized() * need[k] * w if need[k] > 0 and d.length > 1e-6 else Vector()
    for obj in worn:
        shift(obj, flare)
    report_lower = {'drop_mm': round(drop * 1000, 1), 'flare_mm': round(max(need) * 1000, 1)}
else:
    report_lower = {}

vertices, triangles, parts = [], [], []
for obj in worn:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    base = len(vertices)
    vertices += [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles += [tuple(base + i for i in t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    parts.append(obj.name)
if not triangles:
    raise RuntimeError('no protector is switched on')
protector = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
axis = Vector((0, sum(v.y for v in vertices) / len(vertices), 0))
report = {'protector_parts': len(parts), **report_lower}


def outward_thickness(obj):
    return sum(m.thickness * (1 + m.offset) / 2 for m in obj.modifiers if m.type == 'SOLIDIFY' and m.show_render)


for name in PRESSED:
    obj = bpy.data.objects.get(name)
    if obj is None:
        continue
    mesh = obj.data
    mesh.calc_normals_split() if hasattr(mesh, 'calc_normals_split') else None
    world = obj.matrix_world
    normal_matrix = world.to_3x3().inverted().transposed()
    extra = CLEARANCE + outward_thickness(obj)
    moves = [Vector() for _ in mesh.vertices]
    # Sleeves stay out: their tops sit beside the protector's shoulder yoke, and pulling them under it frays the armhole.
    names = {g.index: g.name for g in obj.vertex_groups}
    for v in mesh.vertices:
        dominant = max(((names[g.group], g.weight) for g in v.groups), key=lambda w: w[1], default=('', 0))[0]
        if dominant.startswith(('upperarm', 'lowerarm', 'hand')):
            continue
        p = world @ v.co
        n = (normal_matrix @ v.normal).normalized()
        outward = Vector((p.x - axis.x, p.y - axis.y, 0))
        if n.dot(outward) < 0:
            n = -n
        hit, face_normal, _, dist = protector.ray_cast(p, -n, REACH)
        if hit is not None and face_normal.dot(n) > 0:  # only the protector's outer face: the jacket is outside it
            moves[v.index] = (hit - n * extra) - p
    # Spread the pull so the jacket eases out from under the protector's edges; keep at least each vertex's own pull.
    links = defaultdict(list)
    for e in mesh.edges:
        a, b = e.vertices
        links[a].append(b)
        links[b].append(a)
    own = [m.copy() for m in moves]
    for _ in range(SMOOTH):
        moves = [(sum((moves[j] for j in links[i]), Vector()) + moves[i] * 2) / (len(links[i]) + 2) for i in range(len(moves))]
        moves = [own[i] if own[i].length > moves[i].length else moves[i] for i in range(len(moves))]
    inverse = world.inverted().to_3x3()
    for v, move in zip(mesh.vertices, moves):
        v.co += inverse @ move
    mesh.update()
    report[name] = {'pressed': sum(1 for m in own if m.length > 0), 'max_pull_mm': round(max(m.length for m in own) * 1000, 1)}
rig.data.pose_position = pose_position
print('PROTECTOR DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'protector_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
