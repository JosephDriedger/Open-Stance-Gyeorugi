"""Back-of-knee trouser correction for one knee, fitted to every frame of the kick, then checked on all frames.

The V3 corrective is fitted at deep bends (90-135 degrees) and ramps in by 63 degrees, so a knee passing through
47-80 degrees on the way into and out of a kick still pushes back-of-knee trouser vertices into the calf. This adds a
second knee-angle-driven shape key that peaks in that range, then refits both keys round by round: each round checks
every frame and moves only the keys' offsets at the failing frames, until none fail.

    blender.exe -b CalfKneeCorrectiveV3/Candidate.blend -P refine_calf_knee_corrective_v4.py -- <out folder> [l|r]

For the right knee the left leg's pose is copied onto the right bones each frame (the animation only bends the left
knee; mirrored rigs bend with the same local values), and a deep-bend key is created as well. Start that run from
the left-knee result.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
SIDE = args[1] if len(args) > 1 else 'l'
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
CLEARANCE_M = .004 * scale
MAX_STEP_M = .006 * scale
MAX_ROUNDS = 12
DEEP_BEND_RAD = 1.55
MIN_KEY_WEIGHT = .25
DEEP_EXPRESSION = 'min(1,max(0,(abs(bend)-.6)/.5))'
MID_EXPRESSION = 'max(0, 1 - abs(abs(bend) - 1.1) / .45)'

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
body_weights = [{probe.vertex_groups[g.group].name: g.weight for g in v.groups} for v in probe.data.vertices]
left_bones = [b.name for b in rig.pose.bones if b.name.endswith('_l') and b.name[:-1] + 'r' in rig.pose.bones]


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


def snapshot(frame):
    pose_frame(frame)
    body_points, body_triangles = geometry(probe)
    pants_points, _ = geometry(pants)
    trees = {side: BVHTree.FromPolygons(body_points, [
        t for t in body_triangles
        if sum(sum(w for n, w in body_weights[i].items() if n.endswith('_' + side) and n.startswith(('calf_', 'foot_', 'ball_')))
               for i in t) / 3 > .5], all_triangles=True) for side in 'lr'}
    return pants_points, trees


def check(label):
    rows = []
    for frame in range(1, scene.frame_end + 1):
        points, trees = snapshot(frame)
        depths = []
        for i in indices:
            hit, normal, _, _ = trees[side_for[i]].find_nearest(points[i])
            depths.append((points[i] - hit).dot(normal))
        rows.append({'frame': frame, 'minimum_m': min(depths), 'inside_1mm': sum(d < -.001 for d in depths)})
    print('CHECK', label, 'failing frames', [r['frame'] for r in rows if r['inside_1mm']], flush=True)
    return rows


def solve(frame, key):
    points, trees = snapshot(frame)
    # The key only shows at its current weight, so ask for proportionally more offset when it is barely active.
    weight = max(key.value, MIN_KEY_WEIGHT)
    transforms = {n: (rig.matrix_world @ rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted()
                      @ rig.matrix_world.inverted() @ pants.matrix_world).to_3x3()
                  for row in pants_weights.values() for n, w in row}
    for i in indices:
        if side_for[i] != SIDE:
            continue
        hit, normal, _, _ = trees[SIDE].find_nearest(points[i])
        distance = (points[i] - hit).dot(normal)
        if distance >= CLEARANCE_M:
            continue
        blended = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        for name, w in pants_weights[i]:
            blended += transforms[name] * w
        if abs(blended.determinant()) < 1e-8:
            continue
        key.data[i].co += blended.inverted() @ (normal * min(MAX_STEP_M, CLEARANCE_M - distance) / weight)
    pants.data.update()


def knee_key(name, expression):
    """The key named `name`, created from Basis with a knee-angle driver if the file does not have it yet."""
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


basis = pants.data.shape_keys.key_blocks['Basis']
deep_key = knee_key('KneeFlex_Calf_Clearance_' + SIDE, DEEP_EXPRESSION)
mid_key = knee_key('KneeMid_Calf_Clearance_' + SIDE, MID_EXPRESSION)
pants.update_tag()
bpy.context.view_layer.update()

before = check('before')
after = before
for round_index in range(MAX_ROUNDS):
    after = check('round %d' % round_index)
    failing = [r['frame'] for r in after if r['inside_1mm']]
    if not failing:
        break
    for frame in failing:
        pose_frame(frame)
        bend = abs(rig.pose.bones['calf_' + SIDE].matrix_basis.to_euler().z)
        for _ in range(3):
            solve(frame, deep_key if bend >= DEEP_BEND_RAD else mid_key)

offsets = {}
for key in (deep_key, mid_key):
    moved = [(a.co - b.co).length for a, b in zip(key.data, basis.data)]
    offsets[key.name] = {'moved_vertices': sum(m > 1e-6 for m in moved), 'max_offset_mm': round(max(moved) * 1000, 1)}
print('OFFSETS', json.dumps(offsets), flush=True)

bpy.data.objects.remove(probe, do_unlink=True)
(out / 'all_frames.json').write_text(json.dumps({
    'side': SIDE, 'passed': all(r['inside_1mm'] == 0 for r in after), 'offsets': offsets,
    'scope': 'Lower-leg-region vertex checks against the matching lower-leg surface; not whole-body or cloth collision acceptance',
    'before': before, 'checks': after}, indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('V4 DONE', flush=True)
