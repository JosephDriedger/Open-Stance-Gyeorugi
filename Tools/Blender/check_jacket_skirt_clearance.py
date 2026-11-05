"""Measures how the jacket skirt panels sit against the pants on every frame (cloth off, skinned pose plus shape keys).

For each panel vertex the signed distance to the posed pants surface is compared with its value at rest. A vertex that is
deeper than at rest has sunk into the pants; one that is farther out than at rest has flared away from them.

    blender.exe -b <Candidate.blend> -P check_jacket_skirt_clearance.py -- <result.json>
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

out = Path(sys.argv[sys.argv.index('--') + 1])
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
panels = [bpy.data.objects[n] for n in ('Jacket_Back', 'Jacket_Front_Left', 'Jacket_Front_Right')]
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
SINK_MM = 3.0
FLARE_MM = 40.0

for obj in [pants] + panels:
    for modifier in obj.modifiers:
        if modifier.type in {'CLOTH', 'SOLIDIFY'}:
            modifier.show_viewport = False


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def measure(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    points, triangles = geometry(pants)
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    rows = []
    for panel in panels:
        for index, point in enumerate(geometry(panel)[0]):
            hit, normal, _, _ = tree.find_nearest(point)
            rows.append(((panel.name, index), (point - hit).dot(normal) * 1000))
    return dict(rows)


rest = measure(1)
report = []
for frame in range(1, scene.frame_end + 1):
    now = measure(frame)
    change = {key: now[key] - rest[key] for key in now}
    sunk = sorted(((v, k) for k, v in change.items() if v < -SINK_MM))
    flared = sorted(((v, k) for k, v in change.items() if v > FLARE_MM), reverse=True)
    report.append({'frame': frame, 'sunk_vertices': len(sunk), 'deepest_mm': round(min(change.values()), 1),
                   'flared_vertices': len(flared), 'largest_flare_mm': round(max(change.values()), 1)})
    print('FRAME', frame, report[-1]['sunk_vertices'], report[-1]['deepest_mm'], report[-1]['flared_vertices'],
          report[-1]['largest_flare_mm'], flush=True)
worst = max(report, key=lambda r: r['flared_vertices'])
print('WORST FLARE FRAME', worst['frame'], worst['flared_vertices'], flush=True)
out.write_text(json.dumps({
    'sink_threshold_mm': SINK_MM, 'flare_threshold_mm': FLARE_MM, 'frames': report,
    'scope': 'Skirt panel vertices against the posed pants surface, relative to rest; not a cloth collision test'}, indent=1))
print('CHECK DONE', flush=True)
