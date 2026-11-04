"""Refits the left-hip shape keys of the jacket skirt panels so the skirt never sinks into the pants during the kick.

The existing HipFlex_Clearance_l key is fully on only from about 80 degrees of hip flexion, so the skirt sinks 30+ mm into the
pants while the thigh rises and lowers. This adds a second key (HipFlex_Ramp_l) that peaks at moderate flexion, then refits
both keys round by round: each round checks every frame and moves the keys' offsets only at the failing frames.

    blender.exe -b <Candidate.blend> -P refine_jacket_skirt_hipflex.py -- <out folder>
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

out = Path(sys.argv[sys.argv.index('--') + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
panels = [bpy.data.objects[n] for n in ('Jacket_Back', 'Jacket_Front_Left', 'Jacket_Front_Right')]
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
SINK_MM = 3.0
TARGET_MM = 2.0
MAX_STEP_M = .008 * scale
MAX_ROUNDS = 14
RIDGE = 1e-3
SMOOTH_PASSES = 4
SMOOTH_WEIGHT = .6
DAMPING = 1.0
MAIN = 'HipFlex_Clearance_l'
RAMP = 'HipFlex_Ramp_l'
HIGH = 'HipFlex_High_l'
KEYS = (MAIN, RAMP, HIGH)
HIGH_EXPRESSION = ('max(0,min(1,(2*acos(min(1,abs(l)))-1.7)/0.8))*max(0,1-max(0,(2*acos(min(1,abs(r)))-0.5)/0.4))')
RAMP_EXPRESSION = ('max(0, 1 - abs(2*acos(min(1,abs(l))) - 0.95)/0.5)*max(0,1-max(0,(2*acos(min(1,abs(r)))-0.5)/0.4))')

for obj in [pants] + panels:
    for modifier in obj.modifiers:
        if modifier.type in {'CLOTH', 'SOLIDIFY'}:
            modifier.show_viewport = False
bone_names = set(rig.data.bones.keys())


def weights_of(obj, index):
    return [(obj.vertex_groups[g.group].name, g.weight) for g in obj.data.vertices[index].groups
            if obj.vertex_groups[g.group].name in bone_names]


panel_weights = {p.name: [weights_of(p, i) for i in range(len(p.data.vertices))] for p in panels}


def geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    evaluated.to_mesh_clear()
    return points, triangles


def pants_tree():
    points, triangles = geometry(pants)
    return BVHTree.FromPolygons(points, triangles, all_triangles=True)


def depths(tree):
    """{(panel name, index): (signed distance mm, outward normal)} for every panel vertex."""
    result = {}
    for panel in panels:
        for index, point in enumerate(geometry(panel)[0]):
            hit, normal, _, _ = tree.find_nearest(point)
            result[(panel.name, index)] = ((point - hit).dot(normal) * 1000, normal)
    return result


def pose_frame(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()


def extra_key(panel, name, expression):
    keys = panel.data.shape_keys.key_blocks
    existing = keys.get(name)
    if existing is not None:
        return existing
    key = panel.shape_key_add(name=name, from_mix=False)
    for dst, src in zip(key.data, keys['Basis'].data):
        dst.co = src.co
    key.value = 0
    driver = key.driver_add('value').driver
    driver.type = 'SCRIPTED'
    for variable_name, bone in (('l', 'thigh_l'), ('r', 'thigh_r')):
        variable = driver.variables.new()
        variable.name = variable_name
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = rig
        variable.targets[0].data_path = 'pose.bones["%s"].rotation_quaternion[0]' % bone
    driver.expression = expression
    return key


for panel in panels:
    extra_key(panel, RAMP, RAMP_EXPRESSION)
    extra_key(panel, HIGH, HIGH_EXPRESSION)
    panel.update_tag()

bpy.context.view_layer.update()
pose_frame(1)
rest = depths(pants_tree())


def check(label, collect=False, stride=2):
    """Checks every frame; with collect=True also returns, per vertex that ever sinks, the rest-space offset each frame needs.

    Frames where the vertex is already clear (and a key is active) are included with a zero need, so a refit that fixes
    one frame is penalised for pushing the vertex into the pants on another.
    """
    rows = []
    frame_data = []
    for frame in range(1, scene.frame_end + 1, stride):
        pose_frame(frame)
        now = depths(pants_tree())
        change = {k: now[k][0] - rest[k][0] for k in now}
        rows.append({'frame': frame, 'sunk_vertices': sum(c < -SINK_MM for c in change.values()),
                     'deepest_mm': round(min(change.values()), 1), 'largest_flare_mm': round(max(change.values()), 1)})
        if not collect:
            continue
        first = panels[0].data.shape_keys.key_blocks
        values = tuple(first[k].value for k in KEYS)
        if max(values) <= .02:
            continue
        transforms = {n: (rig.matrix_world @ rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted()
                          @ rig.matrix_world.inverted() @ panels[0].matrix_world).to_3x3()
                      for n in ('pelvis', 'thigh_l', 'thigh_r')}
        frame_data.append((change, {k: v[1].copy() for k, v in now.items()}, values, transforms))
    print('CHECK', label, 'failing frames', [r['frame'] for r in rows if r['sunk_vertices']], flush=True)
    needs = {}
    if collect:
        watched = {k for change, _, _, _ in frame_data for k, v in change.items() if v < -TARGET_MM}
        for key in watched:
            for change, normals, values, transforms in frame_data:
                blended = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
                for name, w in panel_weights[key[0]][key[1]]:
                    blended += transforms[name] * w
                if abs(blended.determinant()) < 1e-8:
                    needs.setdefault(key, [])
                    continue
                gap = change[key]
                need = normals[key] * (-TARGET_MM - gap) / 1000 if gap < -TARGET_MM else Vector()
                needs.setdefault(key, []).append((values, blended.inverted() @ need))
    return rows, needs


neighbours = {}
for panel in panels:
    table = {i: [] for i in range(len(panel.data.vertices))}
    for edge in panel.data.edges:
        table[edge.vertices[0]].append(edge.vertices[1])
        table[edge.vertices[1]].append(edge.vertices[0])
    neighbours[panel.name] = table


def diffuse(steps, panel):
    """Spreads a per-vertex step over the panel mesh so neighbouring vertices move together."""
    for _ in range(SMOOTH_PASSES):
        steps = [(1 - SMOOTH_WEIGHT) * steps[i] + SMOOTH_WEIGHT * sum((steps[n] for n in neighbours[panel.name][i]), Vector())
                 / max(1, len(neighbours[panel.name][i])) for i in range(len(steps))]
    return steps


def refit(needs):
    """Least-squares step for each sunk vertex, smoothed over the mesh, added to the offsets of every key."""
    steps = {(panel.name, key): [Vector() for _ in panel.data.vertices] for panel in panels for key in KEYS}
    for (name, index), rows in needs.items():
        normal = Matrix(((RIDGE, 0, 0), (0, RIDGE, 0), (0, 0, RIDGE)))
        for values, n in rows:
            for i in range(3):
                for j in range(3):
                    normal[i][j] += values[i] * values[j]
        if abs(normal.determinant()) < 1e-12:
            continue
        inverse = normal.inverted()
        rhs = [sum((values[i] * n for values, n in rows), Vector()) for i in range(3)]
        for i, key in enumerate(KEYS):
            step = sum((inverse[i][j] * rhs[j] for j in range(3)), Vector())
            if step.length > MAX_STEP_M:
                step *= MAX_STEP_M / step.length
            steps[(name, key)][index] = DAMPING * step
    for panel in panels:
        keys = panel.data.shape_keys.key_blocks
        for key in KEYS:
            for index, step in enumerate(diffuse(steps[(panel.name, key)], panel)):
                keys[key].data[index].co += step
        panel.data.update()


def roughness():
    """Mean difference between the offsets of neighbouring vertices, in mm, over vertices with a nonzero offset."""
    total, count = 0.0, 0
    for panel in panels:
        keys = panel.data.shape_keys.key_blocks
        for name in KEYS:
            offsets = [a.co - b.co for a, b in zip(keys[name].data, keys['Basis'].data)]
            for i, offset in enumerate(offsets):
                if offset.length > 1e-6:
                    for n in neighbours[panel.name][i]:
                        total += (offset - offsets[n]).length * 1000
                        count += 1
    return round(total / max(1, count), 2)


bpy.context.view_layer.update()
pose_frame(19)
print('DRIVER CHECK frame 19', [(p.name, round(p.data.shape_keys.key_blocks[MAIN].value, 3), round(p.data.shape_keys.key_blocks[RAMP].value, 3), round(p.data.shape_keys.key_blocks[HIGH].value, 3)) for p in panels], flush=True)
pose_frame(1)
print('DRIVER CHECK frame 1', [(p.name, round(p.data.shape_keys.key_blocks[MAIN].value, 3), round(p.data.shape_keys.key_blocks[RAMP].value, 3), round(p.data.shape_keys.key_blocks[HIGH].value, 3)) for p in panels], flush=True)
after, needs = check('before', collect=True)
before = after
print('ROUGHNESS start mm', roughness(), flush=True)
for round_index in range(MAX_ROUNDS):
    if not needs:
        break
    refit(needs)
    after, needs = check('round %d' % round_index, collect=True)

after, _ = check('final all frames', stride=1)
offsets = {}
for panel in panels:
    keys = panel.data.shape_keys.key_blocks
    basis = keys['Basis']
    for name in KEYS:
        moved = [(a.co - b.co).length for a, b in zip(keys[name].data, basis.data)]
        offsets['%s/%s' % (panel.name, name)] = {'moved_vertices': sum(m > 1e-6 for m in moved),
                                                 'max_offset_mm': round(max(moved) * 1000, 1)}
print('OFFSETS', json.dumps(offsets), flush=True)
print('ROUGHNESS mm', roughness(), flush=True)
(out / 'all_frames.json').write_text(json.dumps({
    'roughness_mm': roughness(), 'passed': all(r['sunk_vertices'] == 0 for r in after), 'offsets': offsets, 'before': before, 'checks': after,
    'scope': 'Skirt panel vertices against the posed pants surface, relative to rest; not a cloth collision test'}, indent=1))
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('HIPFLEX DONE', flush=True)
