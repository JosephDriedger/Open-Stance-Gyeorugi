"""Refits the skin weights of the trouser vertices that sink into the calf, and checks every frame of the kick.

The back-of-knee trouser vertices follow a fixed mix of thigh and calf helper bones. No single bone keeps them clear of
the calf, but some mixes do. For each failing vertex (plus the ring around it, so the surface stays smooth) a hill climb
looks for the mix, limited to four bones, that keeps the vertex outside the calf by CLEARANCE_M on every sampled frame
while staying close to its current weights and to its neighbours' weights. The result is written to the vertex groups.

    blender.exe -b <Candidate.blend> -P optimize_knee_weights.py -- <out folder> [l|r]

For the right knee the left leg's pose is copied onto the right bones each frame (the animation only bends the left knee).
"""
import json
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
SIDE = args[1] if len(args) > 1 else 'l'
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
CLEARANCE_MM = 2.0
MAX_INFLUENCES = 4
SWEEPS = 3
ITERATIONS = 500
DEVIATION_COST = 20.0
SMOOTH_COST = 6.0
STRIDE = 2
EXTRA_BONES = ['thigh_l', 'calf_l', 'thigh_bck_l', 'thigh_twistCor_02_l', 'calf_knee_l', 'calf_twist_02_l', 'thigh_fwd_l',
               'thigh_twist_02_l', 'calf_kneeBack_l', 'calf_correctiveRoot_l', 'thigh_correctiveRoot_l']
rng = random.Random(11)

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False
armature = next(m for m in pants.modifiers if m.type == 'ARMATURE')

bone_names = set(rig.data.bones.keys())
mix_bones = [n[:-1] + SIDE if n.endswith(('_l', '_r')) else n for n in EXTRA_BONES]
pants_weights = [{pants.vertex_groups[g.group].name: g.weight for g in v.groups if pants.vertex_groups[g.group].name in bone_names}
                 for v in pants.data.vertices]
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
indices = [i for i, v in enumerate(pants.data.vertices) if .16 * scale < (pants.matrix_world @ v.co).z < .50 * scale]
side_for = {i: max('lr', key=lambda s: sum(w for n, w in pants_weights[i].items() if n.endswith('_' + s))) for i in indices}
left_bones = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name[:-1] + 'r' in rig.pose.bones]
neighbours = {v.index: set() for v in pants.data.vertices}
for e in pants.data.edges:
    a, b = e.vertices
    neighbours[a].add(b)
    neighbours[b].add(a)


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


frames = list(range(1, scene.frame_end + 1))
right_rest = {b.name: b.matrix_basis.copy() for b in rig.pose.bones if b.name.endswith('_r')}
armature.show_viewport = False
shape_keyed = {}
for frame in frames:
    pose_frame(frame)
    shape_keyed[frame] = geometry(pants)[0]
armature.show_viewport = True

trees, skins = {}, {}
for frame in frames:
    pose_frame(frame)
    body_points, body_triangles = geometry(probe)
    trees[frame] = BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + SIDE) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True)
    skins[frame] = {n: rig.matrix_world @ rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted() @ rig.matrix_world.inverted()
                    for n in bone_names}


def bone_positions(index, names):
    """Array [bone, frame, xyz] of where each bone alone would carry the vertex."""
    return np.array([[tuple(skins[f][n] @ shape_keyed[f][index]) for f in frames] for n in names])


def depths_mm(index, weights, positions, names, frame_ids):
    vector = np.array([weights.get(n, 0.0) for n in names])
    points = np.einsum('b,bfk->fk', vector, positions)
    result = []
    for f in frame_ids:
        point = Vector(points[f - 1])
        hit, normal, _, _ = trees[f].find_nearest(point)
        result.append((point - hit).dot(normal) * 1000)
    return result


def cost(index, weights, positions, names, frame_ids, original, around):
    shortfall = sum(max(0.0, CLEARANCE_MM - d) ** 2 for d in depths_mm(index, weights, positions, names, frame_ids))
    deviation = sum((weights.get(n, 0.0) - original.get(n, 0.0)) ** 2 for n in set(weights) | set(original))
    spread = 0.0
    for other in around:
        spread += sum((weights.get(n, 0.0) - other.get(n, 0.0)) ** 2 for n in set(weights) | set(other))
    spread /= max(1, len(around))
    return shortfall + DEVIATION_COST * deviation + SMOOTH_COST * spread


def normalised(weights):
    kept = dict(sorted(((n, max(0.0, w)) for n, w in weights.items()), key=lambda kv: -kv[1])[:MAX_INFLUENCES])
    total = sum(kept.values())
    return {n: w / total for n, w in kept.items() if w / total > 1e-4} if total > 0 else None


def failing_vertices(weight_table):
    found = {}
    for i in indices:
        if side_for[i] != SIDE:
            continue
        names = sorted(set(weight_table[i]))
        positions = bone_positions(i, names)
        worst = min(depths_mm(i, weight_table[i], positions, names, frames))
        if worst < -1.0:
            found[i] = worst
    return found


original_weights = [dict(w) for w in pants_weights]
before = failing_vertices(original_weights)
print('FAILING before', len(before), flush=True)

region = sorted(set(before) | {n for i in before for n in neighbours[i] if n in side_for})
print('REGION', len(region), flush=True)

sample_frames = frames[::STRIDE]
current = [dict(w) for w in original_weights]
for sweep in range(SWEEPS):
    for i in region:
        names = sorted(set(mix_bones) | set(current[i]))
        positions = bone_positions(i, names)
        around = [current[n] for n in neighbours[i] if n in region]
        best = dict(current[i])
        best_cost = cost(i, best, positions, names, sample_frames, original_weights[i], around)
        step = .25
        for iteration in range(ITERATIONS):
            trial = dict(best)
            for name in rng.sample(names, rng.choice((1, 2, 3))):
                trial[name] = trial.get(name, 0.0) + rng.gauss(0, step)
            trial = normalised(trial)
            if trial is None:
                continue
            c = cost(i, trial, positions, names, sample_frames, original_weights[i], around)
            if c < best_cost:
                best, best_cost = trial, c
            if iteration % 100 == 99:
                step = max(.02, step * .6)
        current[i] = best
    print('SWEEP', sweep, 'done', flush=True)

for i in region:
    for name in list(original_weights[i]):
        pants.vertex_groups[name].remove([i])
    for name, weight in current[i].items():
        group = pants.vertex_groups.get(name) or pants.vertex_groups.new(name=name)
        group.add([i], weight, 'REPLACE')
pants.data.update()

after = failing_vertices(current)
print('FAILING after', len(after), flush=True)

# Edge strain: how much the edges around refitted vertices stretch relative to the original weighting, over every frame.
region_set = set(region)
edges = [e.vertices[:] for e in pants.data.edges if e.vertices[0] in region_set or e.vertices[1] in region_set]
strain = 0.0
for frame in frames:
    def point(index, table):
        total = Vector((0, 0, 0))
        for name, weight in table[index].items():
            total += weight * (skins[frame][name] @ shape_keyed[frame][index])
        return total
    for a, b in edges:
        new = (point(a, current) - point(b, current)).length
        old = (point(a, original_weights) - point(b, original_weights)).length
        if old > 1e-6:
            strain = max(strain, abs(new / old - 1))
print('EDGE STRAIN max relative change', round(strain, 3), flush=True)

bpy.data.objects.remove(probe, do_unlink=True)
for name, matrix in right_rest.items():
    rig.pose.bones[name].matrix_basis = matrix
(out / 'all_frames.json').write_text(json.dumps({
    'side': SIDE, 'passed': not after, 'failing_before': {str(k): round(v, 1) for k, v in before.items()},
    'failing_after': {str(k): round(v, 1) for k, v in after.items()}, 'region_vertices': len(region),
    'max_edge_strain': round(strain, 3),
    'weights': {str(i): {n: round(w, 3) for n, w in current[i].items()} for i in region},
    'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance'},
    indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('WEIGHTS DONE', flush=True)
