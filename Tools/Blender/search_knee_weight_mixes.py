"""Searches random skin-weight mixes of the leg bones for each trouser vertex that sinks into the calf, to show whether
any mix keeps the vertex outside the calf surface on every frame.

    blender.exe -b <Candidate.blend> -P search_knee_weight_mixes.py -- <result.json> [l|r] [<samples per vertex>]
"""
import json
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
SIDE = args[1] if len(args) > 1 else 'l'
SAMPLES = int(args[2]) if len(args) > 2 else 4000
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
bone_names = set(rig.data.bones.keys())
armature = next(m for m in pants.modifiers if m.type == 'ARMATURE')
print('ARMATURE preserve volume', armature.use_deform_preserve_volume, 'vertex groups only', armature.use_vertex_groups, flush=True)

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False

pants_weights = [{pants.vertex_groups[g.group].name: g.weight for g in v.groups if pants.vertex_groups[g.group].name in bone_names}
                 for v in pants.data.vertices]
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
indices = [i for i, v in enumerate(pants.data.vertices) if .16 * scale < (pants.matrix_world @ v.co).z < .50 * scale]
side_for = {i: max('lr', key=lambda s: sum(w for n, w in pants_weights[i].items() if n.endswith('_' + s))) for i in indices}
leg_bones = sorted(n for n in bone_names if n.endswith('_' + SIDE) and any(k in n for k in ('thigh', 'calf')))
print('LEG BONES', leg_bones, flush=True)


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def skin_matrices():
    return {n: rig.matrix_world @ rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted() @ rig.matrix_world.inverted()
            for n in bone_names}


frames = range(1, scene.frame_end + 1)
armature.show_viewport = False
shape_keyed = {}
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    shape_keyed[frame] = geometry(pants)[0]
armature.show_viewport = True

trees, skins, final = {}, {}, {}
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    body_points, body_triangles = geometry(probe)
    trees[frame] = BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + SIDE) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True)
    skins[frame] = skin_matrices()
    final[frame] = geometry(pants)[0]


def posed(index, frame, weights):
    rest = shape_keyed[frame][index]
    total = Vector((0, 0, 0))
    for name, weight in weights.items():
        total += weight * (skins[frame][name] @ rest)
    return total


def depth(index, frame, weights):
    point = posed(index, frame, weights)
    hit, normal, _, _ = trees[frame].find_nearest(point)
    return (point - hit).dot(normal)


sample_error = max((posed(i, f, pants_weights[i]) - final[f][i]).length for i in indices[::7] for f in frames[::9])
print('REBUILD max error mm', round(sample_error * 1000, 3), flush=True)


failing = {}
for i in indices:
    if side_for[i] != SIDE:
        continue
    bad = [f for f in frames if depth(i, f, pants_weights[i]) < -.001]
    if bad:
        failing[i] = bad
print('FAILING vertices', len(failing), flush=True)

rng = random.Random(7)
mix_bones = ['thigh_l', 'calf_l', 'thigh_bck_l', 'thigh_twistCor_02_l', 'calf_knee_l', 'calf_twist_02_l', 'thigh_fwd_l', 'thigh_twist_02_l']
report = {}
for i, bad in failing.items():
    current = min(depth(i, f, pants_weights[i]) for f in frames)
    best_mix, best_depth = dict(pants_weights[i]), current
    for _ in range(SAMPLES):
        picked = rng.sample(mix_bones, rng.choice((2, 3, 4)))
        raw = [rng.random() ** 2 for _ in picked]
        mix = {n: r / sum(raw) for n, r in zip(picked, raw)}
        worst = min(depth(i, f, mix) for f in bad)
        if worst > best_depth:
            if min(depth(i, f, mix) for f in frames) > best_depth:
                best_mix, best_depth = mix, min(depth(i, f, mix) for f in frames)
    report[i] = {'current_worst_mm': round(current * 1000, 1), 'best_worst_mm': round(best_depth * 1000, 1),
                 'best_mix': {n: round(w, 3) for n, w in best_mix.items()}}
    print('VERTEX', i, report[i]['current_worst_mm'], '->', report[i]['best_worst_mm'], flush=True)
out.write_text(json.dumps(report, indent=1))
print('SEARCH DONE', flush=True)
