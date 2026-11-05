"""Scans how moving the knee-back helper bone changes trouser-to-calf clearance at chosen frames.

The rig's `calf_kneeBack_<side>` helper bones are static children of the calf. This offsets one along each of its local axes
(pose-bone location, armature units) and reports the deepest trouser vertex in the lower-leg region and how many sit more than
1 mm inside the calf surface. Run on the V3 knee file, which has no mid-bend key.

    blender.exe -b <Candidate.blend> -P scan_knee_helper_offset.py -- <result.json> <frame> [<frame> ...]
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
frames = [int(a) for a in args[1:]]
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
helper = rig.pose.bones['calf_kneeBack_l']
STEPS = [-3, -2, -1, 0, 1, 2, 3, 4, 6]

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
left = [i for i in indices if side_for[i] == 'l']
print('HELPER weight on trousers', sum(pants_weights[i].get('calf_kneeBack_l', 0) > .05 for i in left),
      'on body', sum(w.get('calf_kneeBack_l', 0) > .05 for w in body_weights), flush=True)


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def measure():
    bpy.context.view_layer.update()
    body_points, body_triangles = geometry(probe)
    tree = BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_l') and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True)
    pants_points = geometry(pants)[0]
    depths = []
    for i in left:
        hit, normal, _, _ = tree.find_nearest(pants_points[i])
        depths.append((pants_points[i] - hit).dot(normal) * 1000)
    return round(min(depths), 1), sum(d < -1 for d in depths)


report = {}
for frame in frames:
    scene.frame_set(frame)
    row = {}
    for axis in range(3):
        for step in STEPS:
            offset = Vector((0, 0, 0))
            offset[axis] = step
            helper.location = offset
            row['xyz'[axis] + str(step)] = measure()
    helper.location = (0, 0, 0)
    report[frame] = row
    best = min(row.items(), key=lambda kv: (kv[1][1], -kv[1][0]))
    print('FRAME', frame, 'none', row['x0'], 'best', best, flush=True)
out.write_text(json.dumps(report, indent=1))
print('SCAN DONE', flush=True)
