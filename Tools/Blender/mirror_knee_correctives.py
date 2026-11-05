"""Mirrors the left-knee trouser correctives to the right knee and checks both sides over the kick.

The kick animation only bends the left knee, so the right side is tested by copying the left leg's pose onto the
right bones frame by frame (mirrored rigs bend with the same local values).

    blender.exe -b CalfKneeCorrectiveV4/Candidate.blend -P mirror_knee_correctives.py -- <out folder>
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

out = Path(sys.argv[sys.argv.index('--') + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
bone_names = set(rig.data.bones.keys())
keys = pants.data.shape_keys.key_blocks
basis = keys['Basis']
to_world = pants.matrix_world.to_3x3()
to_local = to_world.inverted()


def mirrored(vector):
    return Vector((-vector.x, vector.y, vector.z))


tree = kdtree.KDTree(len(pants.data.vertices))
for v in pants.data.vertices:
    tree.insert(pants.matrix_world @ v.co, v.index)
tree.balance()
partner = {}
worst_gap = 0.0
for v in pants.data.vertices:
    _, index, gap = tree.find(mirrored(pants.matrix_world @ v.co))
    partner[v.index] = index
    worst_gap = max(worst_gap, gap)
print('MIRROR worst vertex gap mm', round(worst_gap * 1000, 2), flush=True)
moved = [v.index for v in pants.data.vertices
         if any((keys[n].data[v.index].co - basis.data[v.index].co).length > 1e-6
                for n in ('KneeFlex_Calf_Clearance_l', 'KneeMid_Calf_Clearance_l'))]
gaps = sorted(round((mirrored(pants.matrix_world @ pants.data.vertices[i].co) - pants.matrix_world @ pants.data.vertices[partner[i]].co).length * 1000, 1) for i in moved)
print('MIRROR corrected vertices', len(moved), 'partner gaps mm (largest 8)', gaps[-8:], 'distinct partners', len({partner[i] for i in moved}), flush=True)

for left_name in ('KneeFlex_Calf_Clearance_l', 'KneeMid_Calf_Clearance_l'):
    left = keys[left_name]
    right = pants.shape_key_add(name=left_name[:-1] + 'r', from_mix=False)
    for dst, src in zip(right.data, basis.data):
        dst.co = src.co
    for v in pants.data.vertices:
        offset = left.data[v.index].co - basis.data[v.index].co
        if offset.length > 1e-6:
            target = partner[v.index]
            right.data[target].co = basis.data[target].co + to_local @ mirrored(to_world @ offset)
    right.value = 0
    curve = right.driver_add('value')
    source = keys[left_name].id_data.animation_data.drivers.find('key_blocks["%s"].value' % left_name)
    curve.driver.expression = source.driver.expression
    variable = curve.driver.variables.new()
    variable.name = 'bend'
    variable.type = 'TRANSFORMS'
    variable.targets[0].id = rig
    variable.targets[0].bone_target = 'calf_r'
    variable.targets[0].transform_type = 'ROT_Z'
    variable.targets[0].transform_space = 'LOCAL_SPACE'
pants.update_tag()

probe = body.copy()
probe.data = body.data.copy()
scene.collection.objects.link(probe)
for modifier in list(probe.modifiers):
    if modifier.type == 'MASK':
        probe.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False


def weights_of(obj, index):
    return {obj.vertex_groups[g.group].name: g.weight for g in obj.data.vertices[index].groups if obj.vertex_groups[g.group].name in bone_names}


rest = [v.co.copy() for v in pants.data.vertices]
indices = [i for i, p in enumerate(rest) if .16 * scale < (pants.matrix_world @ p).z < .50 * scale]
pants_weights = {i: list(weights_of(pants, i).items()) for i in indices}
side_for = {i: max('lr', key=lambda side: sum(w for n, w in pants_weights[i] if n.endswith('_' + side))) for i in indices}
body_weights = [weights_of(probe, v.index) for v in probe.data.vertices]
left_bones = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name[:-1] + 'r' in rig.pose.bones]


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def run(label, mirror_pose):
    failing = []
    worst = 0.0
    for frame in range(1, scene.frame_end + 1):
        scene.frame_set(frame)
        if mirror_pose:
            for name in left_bones:
                rig.pose.bones[name[:-1] + 'r'].matrix_basis = rig.pose.bones[name].matrix_basis.copy()
        bpy.context.view_layer.update()
        body_points, body_triangles = geometry(probe)
        pants_points, _ = geometry(pants)
        trees = {side: BVHTree.FromPolygons(body_points, [
            t for t in body_triangles
            if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + side) and n.startswith(('calf_', 'foot_', 'ball_')))
                   for i in t) / 3 > .5], all_triangles=True) for side in 'lr'}
        side_to_check = 'r' if mirror_pose else 'l'
        count = 0
        for i in indices:
            if side_for[i] != side_to_check:
                continue
            hit, normal, _, _ = trees[side_for[i]].find_nearest(pants_points[i])
            depth = (pants_points[i] - hit).dot(normal)
            if depth < -.001:
                count += 1
                worst = min(worst, depth)
        if count:
            failing.append(frame)
    print('CHECK', label, 'failing frames', failing, 'worst mm', round(worst * 1000, 1), flush=True)
    return {'failing_frames': failing, 'worst_mm': round(worst * 1000, 1)}


left_report = run('left knee, animated pose', False)
# Save before the mirrored-pose test so the copied right-leg pose never reaches the file.
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
for name in ('KneeFlex_Calf_Clearance_r', 'KneeMid_Calf_Clearance_r'):
    keys[name].mute = True
run('right knee, mirrored pose, right corrections muted', True)
for name in ('KneeFlex_Calf_Clearance_r', 'KneeMid_Calf_Clearance_r'):
    keys[name].mute = False
report = {'left': left_report, 'right': run('right knee, mirrored left pose', True),
          'worst_vertex_gap_mm': round(worst_gap * 1000, 2)}
(out / 'report.json').write_text(json.dumps(report, indent=1))
print('MIRROR DONE', flush=True)
