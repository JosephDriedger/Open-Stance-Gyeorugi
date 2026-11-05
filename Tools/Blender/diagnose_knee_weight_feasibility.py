"""Finds the trouser vertices that sink into the calf during the kick and asks whether any skin-weight mix could keep them out.

For each failing vertex it lists the current weights and the best depth reachable with each single leg bone and with the
current mix, over every frame. The posed positions are rebuilt from the bones' skin matrices, so the same rebuild can
later be used to search weights; the rebuild is checked against Blender's own evaluated mesh first.

    blender.exe -b <Candidate.blend> -P diagnose_knee_weight_feasibility.py -- <result.json> [l|r]
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
SIDE = args[1] if len(args) > 1 else 'l'
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

report = {'rebuild_max_error_mm': round(sample_error * 1000, 3), 'failing_vertex_count': len(failing), 'vertices': {}}
for i, bad in failing.items():
    current_depths = {f: depth(i, f, pants_weights[i]) for f in frames}
    row = {'weights': {n: round(w, 3) for n, w in pants_weights[i].items()},
           'rest_z_m': round((pants.matrix_world @ pants.data.vertices[i].co).z, 3),
           'failing_frames': bad,
           'worst_mm': round(min(current_depths.values()) * 1000, 1),
           'single_bone_worst_mm': {}}
    for name in leg_bones:
        row['single_bone_worst_mm'][name] = round(min(depth(i, f, {name: 1.0}) for f in frames) * 1000, 1)
    report['vertices'][i] = row
bpy.data.objects.remove(probe, do_unlink=True)
out.write_text(json.dumps(report, indent=1))
print('DIAG DONE', flush=True)
