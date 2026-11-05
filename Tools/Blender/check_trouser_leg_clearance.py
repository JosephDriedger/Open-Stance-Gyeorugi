"""Every-frame count of trouser vertices that sink into the leg surface beyond their rest-pose position.

Run headless on a staged trouser test file, with the result path after `--`:
    blender.exe -b <Trouser_Test.blend> -P check_trouser_leg_clearance.py -- <result.json>

The cloth is stepped from the first frame so the cache is valid. Only the lower body is tested (legs, feet), against
the evaluated body surface, so this is a sampled surface check and not a collision guarantee.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

result_path = Path(sys.argv[sys.argv.index('--') + 1])
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
leg_prefixes = ('thigh_', 'calf_', 'foot_', 'ball_')

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]


def leg_share(vertex_index):
    return sum(w for name, w in body_weights[vertex_index].items() if name.startswith(leg_prefixes))


def evaluated_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


tested = [i for i, v in enumerate(pants.data.vertices) if (pants.matrix_world @ v.co).z < 0.62 * scale]
rows = []
rest_depths = None
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    body_points, body_triangles = evaluated_points(probe)
    pants_points, _ = evaluated_points(pants)
    leg_triangles = [t for t in body_triangles if sum(leg_share(i) for i in t) / 3 > 0.5]
    tree = BVHTree.FromPolygons(body_points, leg_triangles, all_triangles=True)
    depths = []
    for i in tested:
        hit, normal, _, _ = tree.find_nearest(pants_points[i])
        depths.append((pants_points[i] - hit).dot(normal) if hit else 1.0)
    if rest_depths is None:
        rest_depths = depths
    # Depth beyond what the same vertex has at rest, so garment-over-body overlap built into the rest fit is not counted.
    extra = [rest - d for rest, d in zip(rest_depths, depths)]
    rows.append({'frame': frame, 'deepest_mm': round(max(extra) * 1000, 2),
                 'inside_1mm': sum(e > 0.001 for e in extra), 'inside_5mm': sum(e > 0.005 for e in extra)})

worst = max(rows, key=lambda r: r['deepest_mm'])
result_path.write_text(json.dumps({
    'file': bpy.data.filepath,
    'vertices_tested': len(tested),
    'frames_with_any_inside_1mm': sum(r['inside_1mm'] > 0 for r in rows),
    'worst_frame': worst,
    'scope': 'Lower-body pants vertices against the evaluated leg surface; sampled, not a collision guarantee',
    'frames': rows,
}, indent=1))
print('CLEARANCE', len(rows), 'frames, worst', worst, flush=True)
