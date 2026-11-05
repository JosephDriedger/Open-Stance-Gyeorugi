"""Per-frame knee angles and the back-of-knee trouser vertices that sink into the calf (skinned trousers, cloth off).

    blender.exe -b <Candidate.blend> -P diagnose_knee_transition.py -- <result.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

result_path = Path(sys.argv[sys.argv.index('--') + 1])
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False

rest = [v.co.copy() for v in pants.data.vertices]
indices = [i for i, p in enumerate(rest) if .16 * scale < (pants.matrix_world @ p).z < .50 * scale]
bone_names = set(rig.data.bones.keys())
pants_weights = {i: [(pants.vertex_groups[g.group].name, g.weight) for g in pants.data.vertices[i].groups
                     if pants.vertex_groups[g.group].name in bone_names] for i in indices}
side_for = {i: max('lr', key=lambda side: sum(w for n, w in pants_weights[i] if n.endswith('_' + side))) for i in indices}
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def bend(name):
    return round(math.degrees(rig.pose.bones[name].matrix_basis.to_euler().z), 1)


rows = []
for frame in range(1, 145):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    body_points, body_triangles = geometry(probe)
    pants_points, _ = geometry(pants)
    trees = {side: BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + side) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True) for side in 'lr'}
    inside = {}
    for i in indices:
        hit, normal, _, _ = trees[side_for[i]].find_nearest(pants_points[i])
        depth = (pants_points[i] - hit).dot(normal)
        if depth < -.001:
            inside[i] = round(depth * 1000, 1)
    pose = rig.pose.bones
    rows.append({'frame': frame, 'calf_l_z': bend('calf_l'), 'calf_r_z': bend('calf_r'),
                 'thigh_l_x': round(math.degrees(pose['thigh_l'].matrix_basis.to_euler().x), 1),
                 'thigh_l_z': round(math.degrees(pose['thigh_l'].matrix_basis.to_euler().z), 1),
                 'thigh_r_z': round(math.degrees(pose['thigh_r'].matrix_basis.to_euler().z), 1),
                 'inside_mm': inside})

bad_vertices = sorted({i for r in rows for i in r['inside_mm']})
result_path.write_text(json.dumps({
    'bad_vertices': bad_vertices,
    'bad_vertex_weights': {i: pants_weights[i] for i in bad_vertices},
    'bad_vertex_side': {i: side_for[i] for i in bad_vertices},
    'rows': rows}, indent=1))
print('DIAG', len(bad_vertices), 'vertices', flush=True)
