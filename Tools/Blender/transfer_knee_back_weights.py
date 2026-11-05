"""Gives the back-of-knee trouser vertices the body's skin weights, then checks every frame for penetration.

Trouser vertices that follow a different helper-bone mix than the body surface beneath them sink into the calf at
mid-bend. Copying the nearest body vertex's weights makes them deform with the body, so they keep their rest offset.

    blender.exe -b <Candidate.blend> -P transfer_knee_back_weights.py -- <out folder> [<knee-back weight threshold>]
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import kdtree
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
threshold = float(args[1]) if len(args) > 1 else .2
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
bone_names = set(rig.data.bones.keys())

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False


def vertex_weights(obj, index):
    vertex = obj.data.vertices[index]
    return {obj.vertex_groups[g.group].name: g.weight for g in vertex.groups if obj.vertex_groups[g.group].name in bone_names}


# Region: trouser vertices that lean on the knee-back helper bones, on either leg.
region = [v.index for v in pants.data.vertices
          if sum(w for n, w in vertex_weights(pants, v.index).items() if n.startswith('calf_kneeBack_')) > threshold]

tree = kdtree.KDTree(len(body.data.vertices))
for v in body.data.vertices:
    tree.insert(body.matrix_world @ v.co, v.index)
tree.balance()

changed = 0
for index in region:
    _, nearest, _ = tree.find(pants.matrix_world @ pants.data.vertices[index].co)
    source = vertex_weights(body, nearest)
    total = sum(source.values())
    if total <= 0:
        continue
    for name in vertex_weights(pants, index):
        pants.vertex_groups[name].remove([index])
    for name, weight in sorted(source.items(), key=lambda kv: -kv[1])[:4]:
        group = pants.vertex_groups.get(name) or pants.vertex_groups.new(name=name)
        group.add([index], weight / total, 'REPLACE')
    changed += 1
print('TRANSFER region', len(region), 'changed', changed, flush=True)

rest = [v.co.copy() for v in pants.data.vertices]
indices = [i for i, p in enumerate(rest) if .16 * scale < (pants.matrix_world @ p).z < .50 * scale]
pants_weights = {i: list(vertex_weights(pants, i).items()) for i in indices}
side_for = {i: max('lr', key=lambda side: sum(w for n, w in pants_weights[i] if n.endswith('_' + side))) for i in indices}
body_weights = [vertex_weights(probe, v.index) for v in probe.data.vertices]


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


rows = []
for frame in range(1, scene.frame_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    body_points, body_triangles = geometry(probe)
    pants_points, _ = geometry(pants)
    trees = {side: BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + side) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True) for side in 'lr'}
    deepest = 0.0
    count = 0
    for i in indices:
        hit, normal, _, _ = trees[side_for[i]].find_nearest(pants_points[i])
        depth = (pants_points[i] - hit).dot(normal)
        if depth < -.001:
            count += 1
            deepest = min(deepest, depth)
    rows.append({'frame': frame, 'inside_1mm': count, 'deepest_mm': round(deepest * 1000, 1)})
failing = [r['frame'] for r in rows if r['inside_1mm']]
print('WEIGHT CHECK failing frames', failing, flush=True)

bpy.data.objects.remove(probe, do_unlink=True)
(out / 'all_frames.json').write_text(json.dumps({
    'passed': not failing, 'region_vertices': len(region), 'changed_vertices': changed, 'threshold': threshold,
    'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance',
    'checks': rows}, indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('WEIGHTS DONE', flush=True)
