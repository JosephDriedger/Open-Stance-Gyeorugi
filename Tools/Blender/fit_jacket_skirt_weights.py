"""Tries letting the jacket skirt's left half follow the left thigh more, and scores each variant against the pants.

The new thigh_l weight of a skirt vertex is  w + ALPHA * h^POWER * t * (1 - w),  where h runs from 0 at the skirt's top edge to
1 at its hem and t tapers from 0 at the centre line to 1 by 6 cm to the left, so the change is smooth by construction. Weight
taken from thigh_l comes out of the vertex's other bones in proportion. Each variant is scored with the hip shape keys on and
off: panel vertices that sink more than SINK_MM deeper into the pants than in the original rest pose, and the largest change
in panel edge length against the original weights.

    blender.exe -b <Candidate.blend> -P fit_jacket_skirt_weights.py -- <out folder> [apply <alpha> <power> <keys on|off>]
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
panels = [bpy.data.objects[n] for n in ('Jacket_Back', 'Jacket_Front_Left', 'Jacket_Front_Right')]
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
SINK_MM = 3.0
FRAMES = list(range(11, 66, 2))
bone_names = set(rig.data.bones.keys())

for obj in [pants] + panels:
    for modifier in obj.modifiers:
        if modifier.type in {'CLOTH', 'SOLIDIFY'}:
            modifier.show_viewport = False

original = {p.name: [{p.vertex_groups[g.group].name: g.weight for g in v.groups if p.vertex_groups[g.group].name in bone_names}
                     for v in p.data.vertices] for p in panels}
local = {p.name: [(v.co.x, v.co.z) for v in p.data.vertices] for p in panels}
z_top = max(z for p in panels for _, z in local[p.name])
z_hem = min(z for p in panels for _, z in local[p.name])
edges = {p.name: [tuple(e.vertices) for e in p.data.edges] for p in panels}


def set_weights(alpha, power):
    for p in panels:
        for i, weights in enumerate(original[p.name]):
            x, z = local[p.name][i]
            h = max(0.0, min(1.0, (z_top - z) / (z_top - z_hem))) ** power
            t = max(0.0, min(1.0, (x * 1.0 - 0.0) / 0.06)) if x > 0 else 0.0
            old = weights.get('thigh_l', 0.0)
            new = old + alpha * h * t * (1 - old)
            others = sum(w for n, w in weights.items() if n != 'thigh_l')
            result = {n: (w * (1 - new) / others if others > 0 else 0.0) for n, w in weights.items() if n != 'thigh_l'}
            result['thigh_l'] = new
            for name in set(weights) | {'thigh_l'}:
                group = p.vertex_groups.get(name) or p.vertex_groups.new(name=name)
                group.add([i], result.get(name, 0.0), 'REPLACE')
        p.data.update()


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def measure(frames):
    """{frame: ({(panel, index): depth mm}, {(panel, edge index): length})}"""
    result = {}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        points, triangles = geometry(pants)
        tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
        depth, length = {}, {}
        for p in panels:
            panel_points = geometry(p)[0]
            for i, point in enumerate(panel_points):
                hit, normal, _, _ = tree.find_nearest(point)
                depth[(p.name, i)] = (point - hit).dot(normal) * 1000
            for k, (a, b) in enumerate(edges[p.name]):
                length[(p.name, k)] = (panel_points[a] - panel_points[b]).length
        result[frame] = (depth, length)
    return result


def set_keys(on):
    for p in panels:
        for key in p.data.shape_keys.key_blocks:
            if key.name.startswith(('HipFlex', 'Squat')):
                key.mute = not on


set_keys(True)
set_weights(0.0, 1.0)
rest = measure([1])[1][0]
base_lengths = {}
for on in (True, False):
    set_keys(on)
    base_lengths[on] = measure(FRAMES)


def score(alpha, power, on):
    set_weights(alpha, power)
    set_keys(on)
    data = measure(FRAMES)
    sunk = [sum(d - rest[k] < -SINK_MM for k, d in data[f][0].items()) for f in FRAMES]
    worst = min(d - rest[k] for f in FRAMES for k, d in data[f][0].items())
    strain = max(abs(data[f][1][k] / base_lengths[on][f][1][k] - 1) for f in FRAMES for k in data[f][1]
                 if base_lengths[on][f][1][k] > .002)
    return {'alpha': alpha, 'power': power, 'keys_on': on, 'mean_sunk_vertices': round(sum(sunk) / len(sunk), 1),
            'frames_with_sunk': sum(s > 0 for s in sunk), 'worst_mm': round(worst, 1), 'max_edge_strain': round(strain, 2)}


if args[1:2] == ['apply']:
    alpha, power, on = float(args[2]), float(args[3]), args[4] == 'on'
    set_weights(alpha, power)
    set_keys(True)
    for p in panels:
        for key in p.data.shape_keys.key_blocks:
            if not on and key.name.startswith(('HipFlex_Clearance', 'Squat')):
                key.data.foreach_set('co', [c for v in p.data.shape_keys.key_blocks['Basis'].data for c in v.co])
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
    print('APPLIED', flush=True)
else:
    rows = [score(1e-9, 1.0, True), score(1e-9, 1.0, False)]
    for r in rows:
        print('SCORE', json.dumps(r), flush=True)
    for alpha in (.3, .6, .9):
        for power in (1.0, 2.0):
            for on in (True, False):
                rows.append(score(alpha, power, on))
                print('SCORE', json.dumps(rows[-1]), flush=True)
    (out / 'grid.json').write_text(json.dumps(rows, indent=1))
    print('GRID DONE', flush=True)
