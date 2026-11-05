"""Sweeps a smooth rest-pose bulge at the back of the trouser knee and checks it clears the calf over the kick.

The bulge moves vertices outward along their normals by AMOUNT * band(height) * back-facing^2, where the band is a cosine-squared
taper around the knee. The same displacement is added to the Basis and every shape key (they store absolute positions), so
the existing correctives still add on top of the new rest shape. For each amount in the sweep, every second frame of the kick is
checked: trouser vertices in the lower-leg region that sit more than 1 mm inside the matching calf surface.

    blender.exe -b <Candidate.blend> -P inflate_trouser_knee_back.py -- <out folder> <side l|r> <amount mm> [<amount mm> ...]

With a single amount the result is saved as <out folder>/Candidate.blend after a check of every frame. For the right knee the
left leg's pose is copied onto the right bones (the animation only bends the left knee).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
SIDE = args[1]
amounts = [float(a) for a in args[2:]]
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
CENTRE = .47
HALF_WIDTH = .10
SINK_MM = 1.0

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
keys = pants.data.shape_keys.key_blocks
original = {k.name: [v.co.copy() for v in k.data] for k in keys}
mesh_original = [v.co.copy() for v in pants.data.vertices]
normals = [v.normal.copy() for v in pants.data.vertices]
heights = [v.co.z for v in pants.data.vertices]
indices = [i for i, z in enumerate(heights) if .16 * scale < z < .50 * scale]
pants_weights = {i: {pants.vertex_groups[g.group].name: g.weight for g in pants.data.vertices[i].groups
                     if pants.vertex_groups[g.group].name in bone_names} for i in indices}
side_for = {i: max('lr', key=lambda s: sum(w for n, w in pants_weights[i].items() if n.endswith('_' + s))) for i in indices}
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
region = [i for i in indices if side_for[i] == SIDE]
right_rest = {b.name: b.matrix_basis.copy() for b in rig.pose.bones if b.name.endswith('_r')}
left_bones = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name[:-1] + 'r' in rig.pose.bones]


def displacement(index, amount_m):
    offset = (heights[index] - CENTRE) / HALF_WIDTH
    if abs(offset) >= 1:
        return Vector()
    band = math.cos(math.pi / 2 * offset) ** 2
    back = max(0.0, normals[index].y) ** 2
    return normals[index] * (amount_m * band * back)


def apply(amount_mm):
    moves = [displacement(i, amount_mm / 1000) for i in range(len(heights))]
    for key in keys:
        for i, v in enumerate(key.data):
            v.co = original[key.name][i] + moves[i]
    for i, v in enumerate(pants.data.vertices):
        v.co = mesh_original[i] + moves[i]
    pants.data.update()
    return max(m.length for m in moves) * 1000


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def pose_frame(frame):
    scene.frame_set(frame)
    if SIDE == 'r':
        for name in left_bones:
            rig.pose.bones[name[:-1] + 'r'].matrix_basis = rig.pose.bones[name].matrix_basis.copy()
    bpy.context.view_layer.update()


def check(stride):
    rows = []
    for frame in range(1, scene.frame_end + 1, stride):
        pose_frame(frame)
        body_points, body_triangles = geometry(probe)
        tree = BVHTree.FromPolygons(body_points, [
            t for t in body_triangles
            if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + SIDE) and n.startswith(('calf_', 'foot_', 'ball_')))
                   for i in t) / 3 > .5], all_triangles=True)
        pants_points = geometry(pants)[0]
        depths = []
        for i in region:
            hit, normal, _, _ = tree.find_nearest(pants_points[i])
            depths.append((pants_points[i] - hit).dot(normal) * 1000)
        rows.append({'frame': frame, 'inside_1mm': sum(d < -SINK_MM for d in depths), 'minimum_mm': round(min(depths), 1)})
    return rows


summary = {}
for amount in amounts:
    peak = apply(amount)
    rows = check(2 if len(amounts) > 1 else 1)
    failing = [r['frame'] for r in rows if r['inside_1mm']]
    summary[amount] = {'peak_displacement_mm': round(peak, 1), 'failing_frames': failing,
                       'worst_mm': min(r['minimum_mm'] for r in rows)}
    print('AMOUNT', amount, json.dumps(summary[amount]), flush=True)
    if len(amounts) == 1:
        (out / 'all_frames.json').write_text(json.dumps({
            'side': SIDE, 'amount_mm': amount, 'passed': not failing, 'checks': rows,
            'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance'},
            indent=1))
        for name, matrix in right_rest.items():
            rig.pose.bones[name].matrix_basis = matrix
        scene.frame_set(1)
        bpy.data.objects.remove(probe, do_unlink=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
(out / 'sweep.json').write_text(json.dumps(summary, indent=1))
print('INFLATE DONE', flush=True)
