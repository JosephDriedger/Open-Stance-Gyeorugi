"""Fits a knee's trouser correctives (deep, mid-bend and mid-bend-with-thigh-twist keys) jointly over all frames, with smoothed steps.

The earlier per-frame fit (refine_calf_knee_corrective_v4.py) blew up on the right knee. This collects, for every trouser vertex
that sinks into the calf on any frame, the rest-space offset each active frame needs (zero where it is already clear), solves the
two key offsets by regularised least squares, spreads each step over the neighbouring vertices, and repeats.

    blender.exe -b CalfKneeCorrectiveV4/Candidate.blend -P refine_knee_joint_ls.py -- <out folder> [l|r] [<smoothing weight>] [--twist]

--twist adds a third key driven by mid-bend times thigh twist (tried, little gain).

The animation only bends the left knee, so for the right knee the left leg's pose is copied onto the right bones each frame.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
TWIST = '--twist' in args
args = [a for a in args if a != '--twist']
out = Path(args[0])
SIDE = args[1] if len(args) > 1 else 'r'
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
SINK_MM = 1.0
TARGET_MM = 2.5
MAX_STEP_M = .008 * scale
MAX_ROUNDS = 12
RIDGE = 1e-3
SMOOTH_PASSES = 3
SMOOTH_WEIGHT = float(args[2]) if len(args) > 2 else .5
STRIDE = 2
DEEP_EXPRESSION = 'min(1,max(0,(abs(bend)-.6)/.5))'
MID_EXPRESSION = 'max(0, 1 - abs(abs(bend) - 1.1) / .45)'
# Rising and falling through mid-bend differ in thigh twist (quaternion Y), not hip flexion, so this key separates them.
TWIST_EXPRESSION = 'max(0, 1 - abs(abs(bend) - 1.1) / .45) * max(0, min(1, -twist / .12))'

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
rest = [v.co.copy() for v in pants.data.vertices]
indices = [i for i, p in enumerate(rest) if .16 * scale < (pants.matrix_world @ p).z < .50 * scale]
pants_weights = {i: [(pants.vertex_groups[g.group].name, g.weight) for g in pants.data.vertices[i].groups
                     if pants.vertex_groups[g.group].name in bone_names] for i in indices}
side_for = {i: max('lr', key=lambda side: sum(w for n, w in pants_weights[i] if n.endswith('_' + side))) for i in indices}
region = [i for i in indices if side_for[i] == SIDE]
used_bones = sorted({n for i in region for n, _ in pants_weights[i]})
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
right_rest = {b.name: b.matrix_basis.copy() for b in rig.pose.bones if b.name.endswith('_r')}
left_bones = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name[:-1] + 'r' in rig.pose.bones]
neighbours = {i: [] for i in range(len(rest))}
for edge in pants.data.edges:
    a, b = edge.vertices
    neighbours[a].append(b)
    neighbours[b].append(a)


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


def knee_key(name, expression):
    keys = pants.data.shape_keys.key_blocks
    existing = keys.get(name)
    if existing is not None:
        return existing
    key = pants.shape_key_add(name=name, from_mix=False)
    for dst, src in zip(key.data, keys['Basis'].data):
        dst.co = src.co
    key.value = 1
    driver = key.driver_add('value').driver
    variable = driver.variables.new()
    variable.name = 'bend'
    variable.type = 'TRANSFORMS'
    variable.targets[0].id = rig
    variable.targets[0].bone_target = 'calf_' + SIDE
    variable.targets[0].transform_type = 'ROT_Z'
    variable.targets[0].transform_space = 'LOCAL_SPACE'
    driver.expression = expression
    return key


keys = pants.data.shape_keys.key_blocks
deep_key = knee_key('KneeFlex_Calf_Clearance_' + SIDE, DEEP_EXPRESSION)
mid_key = knee_key('KneeMid_Calf_Clearance_' + SIDE, MID_EXPRESSION)
twist_name = 'KneeTwist_Calf_Clearance_' + SIDE
if TWIST and keys.get(twist_name) is None:
    twist_key = knee_key(twist_name, TWIST_EXPRESSION)
    variable = twist_key.id_data.animation_data.drivers.find('key_blocks["%s"].value' % twist_name).driver.variables.new()
    variable.name = 'twist'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = rig
    variable.targets[0].data_path = 'pose.bones["thigh_%s"].rotation_quaternion[2]' % SIDE
KEYS = (deep_key.name, mid_key.name) + ((twist_name,) if TWIST else ())
pants.update_tag()
bpy.context.view_layer.update()


def diffuse(steps):
    for _ in range(SMOOTH_PASSES):
        steps = [(1 - SMOOTH_WEIGHT) * steps[i] + SMOOTH_WEIGHT * sum((steps[n] for n in neighbours[i]), Vector())
                 / max(1, len(neighbours[i])) for i in range(len(steps))]
    return steps


def check(label, collect, stride):
    rows, frame_data = [], []
    for frame in range(1, scene.frame_end + 1, stride):
        pose_frame(frame)
        body_points, body_triangles = geometry(probe)
        tree = BVHTree.FromPolygons(body_points, [
            t for t in body_triangles
            if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + SIDE) and n.startswith(('calf_', 'foot_', 'ball_')))
                   for i in t) / 3 > .5], all_triangles=True)
        pants_points = geometry(pants)[0]
        depth, normal = {}, {}
        for i in region:
            hit, n, _, _ = tree.find_nearest(pants_points[i])
            depth[i] = (pants_points[i] - hit).dot(n) * 1000
            normal[i] = n.copy()
        rows.append({'frame': frame, 'inside_1mm': sum(d < -SINK_MM for d in depth.values()), 'minimum_mm': round(min(depth.values()), 1)})
        values = tuple(keys[k].value for k in KEYS)
        if collect and max(values) > .02:
            transforms = {n: (rig.matrix_world @ rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted()
                              @ rig.matrix_world.inverted() @ pants.matrix_world).to_3x3() for n in used_bones}
            frame_data.append((depth, normal, values, transforms))
    print('CHECK', label, 'failing frames', [r['frame'] for r in rows if r['inside_1mm']], flush=True)
    needs = {}
    if collect:
        watched = {i for depth, _, _, _ in frame_data for i, d in depth.items() if d < -SINK_MM}
        for i in watched:
            for depth, normal, values, transforms in frame_data:
                blended = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
                for name, w in pants_weights[i]:
                    blended += transforms[name] * w
                if abs(blended.determinant()) < 1e-8:
                    continue
                gap = TARGET_MM - depth[i]
                need = blended.inverted() @ (normal[i] * gap / 1000) if gap > 0 else Vector()
                needs.setdefault(i, []).append((values, need))
    return rows, needs


def refit(needs):
    count = len(KEYS)
    steps = [[Vector() for _ in rest] for _ in KEYS]
    for i, rows in needs.items():
        normal = Matrix.Identity(count) * RIDGE
        for values, _ in rows:
            for p in range(count):
                for q in range(count):
                    normal[p][q] += values[p] * values[q]
        inverse = normal.inverted()
        rhs = [sum((values[k] * n for values, n in rows), Vector()) for k in range(count)]
        for k in range(count):
            step = sum((inverse[k][j] * rhs[j] for j in range(count)), Vector())
            if step.length > MAX_STEP_M:
                step *= MAX_STEP_M / step.length
            steps[k][i] = step
    for k, name in enumerate(KEYS):
        for i, step in enumerate(diffuse(steps[k])):
            keys[name].data[i].co += step
    pants.data.update()


rows, needs = check('before', True, STRIDE)
before = rows
for round_index in range(MAX_ROUNDS):
    if not needs:
        break
    refit(needs)
    rows, needs = check('round %d' % round_index, True, STRIDE)
    if not any(r['inside_1mm'] for r in rows):
        break
rows, _ = check('final all frames', False, 1)

basis = keys['Basis']
offsets = {}
for name in KEYS:
    moved = [(a.co - b.co).length for a, b in zip(keys[name].data, basis.data)]
    offsets[name] = {'moved_vertices': sum(m > 1e-6 for m in moved), 'max_offset_mm': round(max(moved) * 1000, 1)}
print('OFFSETS', json.dumps(offsets), flush=True)
bpy.data.objects.remove(probe, do_unlink=True)
for name, matrix in right_rest.items():
    rig.pose.bones[name].matrix_basis = matrix
(out / 'all_frames.json').write_text(json.dumps({
    'side': SIDE, 'passed': all(r['inside_1mm'] == 0 for r in rows), 'offsets': offsets, 'before': before, 'checks': rows,
    'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance'},
    indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('JOINT LS DONE', flush=True)
