"""Fits an offset for the knee-back helper bone as a function of knee bend so the trousers clear the calf on every frame.

The helper bone `calf_kneeBack_l` is static in this rig. Moving it backward as the knee bends carries every trouser (and body)
vertex weighted to it, which is a smooth, low-dimensional correction. For each failing frame a coordinate search finds the
pose-bone location that clears the calf; the offsets are interpolated over knee bend, the whole clip is rechecked, and the
frames that still fail are refitted. The result is written as driver curves on the helper's location (driven by `calf_l`'s
local Z rotation).

    blender.exe -b <V3 Candidate.blend> -P fit_knee_helper_bone.py -- <out folder>
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

out = Path(sys.argv[sys.argv.index('--') + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
SIDE = 'l'
HELPER = 'calf_kneeBack_' + SIDE
helper = rig.pose.bones[HELPER]
calf = rig.pose.bones['calf_' + SIDE]
CLEARANCE_MM = 2.5
SINK_MM = 1.0
STEPS = [4.0, 2.0, 1.0, .5, .25]
MAX_ROUNDS = 4

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False

bone_names = set(rig.data.bones.keys())
indices = [i for i, v in enumerate(pants.data.vertices) if .16 * scale < (pants.matrix_world @ v.co).z < .50 * scale]
pants_weights = {i: {pants.vertex_groups[g.group].name: g.weight for g in pants.data.vertices[i].groups
                     if pants.vertex_groups[g.group].name in bone_names} for i in indices}
side_for = {i: max('lr', key=lambda s: sum(w for n, w in pants_weights[i].items() if n.endswith('_' + s))) for i in indices}
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
region = [i for i in indices if side_for[i] == SIDE]


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def depths():
    bpy.context.view_layer.update()
    body_points, body_triangles = geometry(probe)
    tree = BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + SIDE) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True)
    pants_points = geometry(pants)[0]
    result = []
    for i in region:
        hit, normal, _, _ = tree.find_nearest(pants_points[i])
        result.append((pants_points[i] - hit).dot(normal) * 1000)
    return result


def cost(offset):
    helper.location = offset
    d = depths()
    return sum(max(0.0, CLEARANCE_MM - x) ** 2 for x in d) + .01 * offset.length_squared


def bend_of(frame):
    scene.frame_set(frame)
    return abs(calf.matrix_basis.to_euler().z)


table = {}


def offset_for(bend):
    """Offset interpolated over knee bend from the fitted frames (zero below the smallest fitted bend)."""
    if not table:
        return Vector()
    pairs = sorted(table.values(), key=lambda p: p[0])
    xs = [p[0] for p in pairs]
    return Vector([float(np.interp(bend, xs, [p[1][k] for p in pairs])) for k in range(3)])


def refit(frame):
    bend = bend_of(frame)
    best = offset_for(bend)
    best_cost = cost(best)
    for step in STEPS:
        improved = True
        while improved:
            improved = False
            for axis in range(3):
                for direction in (-1, 1):
                    trial = best.copy()
                    trial[axis] += direction * step
                    c = cost(trial)
                    if c < best_cost - 1e-6:
                        best, best_cost, improved = trial, c, True
    table[frame] = (bend, tuple(best))
    return best, best_cost


def anchor():
    """Zero-offset anchors just below the smallest fitted bend keep the correction off while the knee is nearly straight."""
    if table:
        low = min(p[0] for p in table.values())
        table[-1] = (max(0.0, low - .35), (0.0, 0.0, 0.0))


def check():
    rows = []
    for frame in range(1, scene.frame_end + 1):
        bend = bend_of(frame)
        helper.location = offset_for(bend)
        d = depths()
        rows.append({'frame': frame, 'bend': round(bend, 3), 'inside_1mm': sum(x < -SINK_MM for x in d),
                     'minimum_mm': round(min(d), 1), 'offset': [round(c, 2) for c in helper.location]})
    helper.location = (0, 0, 0)
    print('CHECK failing frames', [r['frame'] for r in rows if r['inside_1mm']], flush=True)
    return rows


rows = check()
before = rows
for round_index in range(MAX_ROUNDS):
    failing = [r['frame'] for r in rows if r['inside_1mm']]
    if not failing:
        break
    for frame in failing:
        offset, c = refit(frame)
        print('FIT frame', frame, [round(x, 2) for x in offset], round(c, 1), flush=True)
    anchor()
    rows = check()

# Driver curves: helper location (x, y, z) as piecewise-linear functions of the calf's local Z rotation.
pairs = sorted(table.values(), key=lambda p: p[0])
merged = {}
for bend, offset in pairs:
    merged.setdefault(round(bend, 2), []).append(offset)
points = [(b, [sum(o[k] for o in offs) / len(offs) for k in range(3)]) for b, offs in sorted(merged.items())]
rig.animation_data_create()
for axis in range(3):
    path = 'pose.bones["%s"].location' % HELPER
    existing = rig.animation_data.drivers.find(path, index=axis)
    if existing:
        rig.animation_data.drivers.remove(existing)
    curve = rig.animation_data.drivers.new(path, index=axis)
    driver = curve.driver
    driver.type = 'AVERAGE'
    variable = driver.variables.new()
    variable.name = 'bend'
    variable.type = 'TRANSFORMS'
    variable.targets[0].id = rig
    variable.targets[0].bone_target = calf.name
    variable.targets[0].transform_type = 'ROT_Z'
    variable.targets[0].transform_space = 'LOCAL_SPACE'
    for bend, offset in points:
        # The variable is signed (the left calf bends toward negative Z), so key the negated bend.
        curve.keyframe_points.insert(-bend, offset[axis], options={'FAST'})
    for keyframe in curve.keyframe_points:
        keyframe.interpolation = 'LINEAR'
    curve.extrapolation = 'CONSTANT'
    curve.update()
helper.location = (0, 0, 0)

(out / 'all_frames.json').write_text(json.dumps({
    'passed': all(r['inside_1mm'] == 0 for r in rows), 'curve_points': [(b, [round(c, 2) for c in o]) for b, o in points],
    'before': before, 'checks': rows,
    'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance'},
    indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('HELPER FIT DONE', flush=True)
