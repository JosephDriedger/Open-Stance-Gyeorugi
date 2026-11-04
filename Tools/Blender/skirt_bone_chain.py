"""Rig the jacket skirt panels to bone chains hinged under the belt and bake a verlet simulation of them.

Why: the skirt hangs over a hip that flexes up to 138 degrees in a kick. Skinned between pelvis and thigh it collapses into
the trousers (linear blend skinning shrinks a 50/50 blend of a 138-degree turn to a third of its radius), and neither weight
fits, hip-angle shape keys nor Blender cloth settles fixed it (REMAINING_WORK.md). A chain of bones per strip of skirt
swings about the belt like a real hem, collides with the trousers, exports as ordinary skeleton data and maps onto the same
Unreal AnimDynamics / physics-asset path as the belt tails (belt_bone_chain.py). The bake here is the Blender preview.

    blender.exe -b <Candidate.blend> -P skirt_bone_chain.py -- <out folder>

Saves <out folder>/Candidate.blend with skirt_<panel>_<chain>_<segment> bones under pelvis, the panels skinned to them (old
skirt shape keys and cloth removed) and the chains baked into the rig's action, plus chain_report.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

out = Path(sys.argv[sys.argv.index('--') + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
W = rig.matrix_world
Wi = W.inverted()
PANELS = (('Jacket_Front_Left', 'fl', 4), ('Jacket_Front_Right', 'fr', 4), ('Jacket_Back', 'b', 7))
COLLIDERS = ('Pants',)
SEGMENTS = 3
HINGE_Z = .915          # m: just under the belt band (.922); the skirt above this stays on the pelvis
CLEARANCE = .012        # m: particle offset from the trouser surface (covers the span between chains)
SUBSTEPS = 4
ITERATIONS = 8
DAMPING = .97
SHAPE_MEMORY = .03      # pull toward the hanging rest shape (stiff cotton), strongest at the hinge
MAX_PUSH = .03
SPREAD_MAX = 1.05       # neighbouring chains may bunch up (folds) but not pull more than 5 percent apart
SPREAD_MIN = .45
GROUP = 'SkirtChain'
centre = W @ rig.data.bones['pelvis'].head_local


def angle_of(point):
    return math.atan2(point.y - centre.y, point.x - centre.x)


def unwrap(values):
    # The back panel runs round the back through +/-180 degrees; keep each panel's angles continuous.
    if max(values) - min(values) > math.pi:
        return [v + 2 * math.pi if v < 0 else v for v in values]
    return values


def build_chains():
    chains = {}
    for name, tag, count in PANELS:
        panel = bpy.data.objects[name]
        points = [panel.matrix_world @ v.co for v in panel.data.vertices]
        angles = unwrap([angle_of(p) for p in points])
        low, high = min(angles), max(angles)
        spacing = (high - low) / count
        lanes = [low + spacing * (c + .5) for c in range(count)]
        panel_chains = []
        for lane in lanes:
            near = [p for p, a in zip(points, angles) if abs(a - lane) <= spacing * .5] or points
            hem = min(p.z for p in near)
            joints = []
            for k in range(SEGMENTS + 1):
                z = HINGE_Z - (HINGE_Z - hem) * k / SEGMENTS
                window = (HINGE_Z - hem) / SEGMENTS * .6
                band = [p for p in near if abs(p.z - z) <= window] or near
                joint = sum(band, Vector()) / len(band)
                joint.z = z
                joints.append(joint)
            panel_chains.append({'lane': lane, 'hem': hem, 'joints': joints})
        chains[name] = {'tag': tag, 'spacing': spacing, 'chains': panel_chains, 'angles': angles}
    return chains


def bone_name(tag, chain, segment):
    return 'skirt_%s_%d_%d' % (tag, chain + 1, segment + 1)


def convert(chains):
    rig.hide_viewport = False
    rig.hide_set(False)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    with bpy.context.temp_override(active_object=rig, object=rig):
        bpy.ops.object.mode_set(mode='EDIT')
    edit = rig.data.edit_bones
    for name, data in chains.items():
        for c, chain in enumerate(data['chains']):
            parent = edit['pelvis']
            outward = Wi.to_3x3() @ Vector((math.cos(chain['lane']), math.sin(chain['lane']), 0))
            for k in range(SEGMENTS):
                bone = edit.new(bone_name(data['tag'], c, k))
                bone.head = Wi @ chain['joints'][k]
                bone.tail = Wi @ chain['joints'][k + 1]
                bone.align_roll(outward)  # straight-down bones need an explicit roll
                bone.parent = parent
                bone.use_connect = k > 0
                parent = bone
    with bpy.context.temp_override(active_object=rig, object=rig):
        bpy.ops.object.mode_set(mode='OBJECT')

    bone_names = set(rig.data.bones.keys())
    for name, data in chains.items():
        panel = bpy.data.objects[name]
        for modifier in list(panel.modifiers):
            if modifier.type == 'CLOTH':
                for prop in ('show_viewport', 'show_render'):
                    modifier.driver_remove(prop)
                panel.modifiers.remove(modifier)
        # The hip-flex correctives were written for the old pelvis/thigh weights; the chains replace them.
        if panel.data.shape_keys:
            panel.shape_key_clear()
        for group in list(panel.vertex_groups):
            if group.name in bone_names:
                panel.vertex_groups.remove(group)
        pelvis = panel.vertex_groups.new(name='pelvis')
        lanes = [chain['lane'] for chain in data['chains']]
        groups = [[panel.vertex_groups.new(name=bone_name(data['tag'], c, k)) for k in range(SEGMENTS)]
                  for c in range(len(lanes))]
        for vertex, angle in zip(panel.data.vertices, data['angles']):
            point = panel.matrix_world @ vertex.co
            if point.z >= HINGE_Z:
                pelvis.add([vertex.index], 1.0, 'REPLACE')
                continue
            t = max(0.0, min(len(lanes) - 1.0, (angle - lanes[0]) / data['spacing']))
            c0 = min(int(t), len(lanes) - 2) if len(lanes) > 1 else 0
            lateral = ((c0, 1 - (t - c0)), (c0 + 1, t - c0)) if len(lanes) > 1 else ((0, 1.0),)
            hem = sum(data['chains'][c]['hem'] * w for c, w in lateral)
            s = max(0.0, min(SEGMENTS - 1.0, (HINGE_Z - point.z) / max(1e-4, HINGE_Z - hem) * SEGMENTS - .5))
            k0 = min(int(s), SEGMENTS - 2)
            vertical = ((k0, 1 - (s - k0)), (k0 + 1, s - k0))
            for c, wc in lateral:
                for k, wk in vertical:
                    if wc * wk > 1e-4:
                        groups[c][k].add([vertex.index], wc * wk, 'ADD')


def collider_tree():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertices, triangles = [], []
    for name in COLLIDERS:
        obj = bpy.data.objects[name].evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        mesh.calc_loop_triangles()
        base = len(vertices)
        vertices += [obj.matrix_world @ v.co for v in mesh.vertices]
        triangles += [tuple(base + i for i in t.vertices) for t in mesh.loop_triangles]
        obj.to_mesh_clear()
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True)


def pelvis_matrix():
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return W @ evaluated.pose.bones['pelvis'].matrix


def simulate(chains):
    for obj in scene.objects:
        for modifier in obj.modifiers:
            if modifier.type in {'CLOTH', 'SOLIDIFY'} and obj.name in COLLIDERS:
                modifier.show_viewport = False
    scene.frame_set(1)
    keys = [(name, c) for name, data in chains.items() for c in range(len(data['chains']))]
    rest_world = {key: [p.copy() for p in chains[key[0]]['chains'][key[1]]['joints']] for key in keys}
    seg = {key: [(pts[i + 1] - pts[i]).length for i in range(SEGMENTS)] for key, pts in rest_world.items()}
    pm0 = pelvis_matrix()
    rest = {key: [pm0.inverted() @ p for p in pts] for key, pts in rest_world.items()}
    neighbours = [((name, c), (name, c + 1)) for name, data in chains.items() for c in range(len(data['chains']) - 1)]
    spread = {pair: [(rest_world[pair[0]][k] - rest_world[pair[1]][k]).length for k in range(SEGMENTS + 1)] for pair in neighbours}
    pos = {key: [p.copy() for p in pts] for key, pts in rest_world.items()}
    prev = {key: [p.copy() for p in pts] for key, pts in rest_world.items()}
    gravity = Vector((0, 0, -9.81))
    dt = 1 / (scene.render.fps * SUBSTEPS)
    stats = {'contacts': 0, 'deepest_mm': 0.0}
    # The trousers are single-sided: take the outward direction from where the skirt hangs at rest, not the winding.
    bind_tree = collider_tree()
    rest_depths = sorted((p - bind_tree.find_nearest(p)[0]).dot(bind_tree.find_nearest(p)[1])
                         for pts in rest_world.values() for p in pts[1:])
    sign = 1.0 if rest_depths[len(rest_depths) // 2] > 0 else -1.0
    stats['normal_sign'] = sign
    stats['rest_median_gap_mm'] = round(abs(rest_depths[len(rest_depths) // 2]) * 1000, 1)

    def push_out(point, tree):
        hit, normal, _, _ = tree.find_nearest(point)
        if hit is None:
            return Vector()
        normal = normal * sign
        depth = (point - hit).dot(normal)
        if depth >= CLEARANCE:
            return Vector()
        stats['deepest_mm'] = min(stats['deepest_mm'], depth * 1000)
        move = normal * (CLEARANCE - depth)
        if move.length > MAX_PUSH:
            move *= MAX_PUSH / move.length
        return move

    def step(tree, pm):
        new = {}
        for key in keys:
            P, Q = pos[key], prev[key]
            new[key] = [pm @ rest[key][0] if i == 0 else p + (p - Q[i]) * DAMPING + gravity * dt * dt for i, p in enumerate(P)]
        for _ in range(ITERATIONS):
            for key in keys:
                N = new[key]
                N[0] = pm @ rest[key][0]
                for i in range(1, SEGMENTS + 1):
                    N[i] += (pm @ rest[key][i] - N[i]) * SHAPE_MEMORY * (1 - i / (SEGMENTS + 1))
                for i in range(1, SEGMENTS + 1):
                    move = push_out(N[i], tree)
                    if move.length:
                        N[i] += move
                        stats['contacts'] += 1
            # Midpoints between neighbouring chains: the skirt surface spans them, so the trousers must not poke through.
            for a, b in neighbours:
                for i in range(1, SEGMENTS + 1):
                    move = push_out((new[a][i] + new[b][i]) * .5, tree)
                    if move.length:
                        new[a][i] += move
                        new[b][i] += move
                    d = new[b][i] - new[a][i]
                    length = d.length or 1e-9
                    target = max(spread[(a, b)][i] * SPREAD_MIN, min(spread[(a, b)][i] * SPREAD_MAX, length))
                    fix = d * (.5 * (length - target) / length)
                    new[a][i] += fix
                    new[b][i] -= fix
            for key in keys:  # lengths last, so a collision never stretches a strip
                N = new[key]
                N[0] = pm @ rest[key][0]
                for i in range(SEGMENTS):
                    a, b = N[i], N[i + 1]
                    d = b - a
                    length = d.length or 1e-9
                    err = (length - seg[key][i]) / length
                    if i == 0:
                        N[1] = b - d * err
                    else:
                        N[i] = a + d * err * .5
                        N[i + 1] = b - d * err * .5
        for key in keys:
            prev[key] = pos[key]
            pos[key] = new[key]

    tree = collider_tree()
    pm = pelvis_matrix()
    for _ in range(120):
        step(tree, pm)
    frames = {}
    for frame in range(scene.frame_start, scene.frame_end + 1):
        for sub in range(SUBSTEPS):
            if frame > scene.frame_start:
                scene.frame_set(frame - 1, subframe=(sub + 1) / SUBSTEPS)
            step(collider_tree(), pelvis_matrix())
        frames[frame] = {key: [p.copy() for p in pos[key]] for key in keys}
        if frame % 12 == 0:
            print('SIM frame', frame, 'contacts', stats['contacts'], 'deepest mm', round(stats['deepest_mm'], 1), flush=True)
    scene.frame_set(1)
    return frames, stats


def bake(chains, frames):
    bones = rig.data.bones
    for frame in sorted(frames):
        scene.frame_set(frame)
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for name, data in chains.items():
            for c in range(len(data['chains'])):
                points = [Wi @ p for p in frames[frame][(name, c)]]
                parent_arm = evaluated.pose.bones['pelvis'].matrix.copy()
                parent_rest = bones['pelvis'].matrix_local.copy()
                for k in range(SEGMENTS):
                    bname = bone_name(data['tag'], c, k)
                    pb = rig.pose.bones[bname]
                    rest_matrix = bones[bname].matrix_local
                    expected = parent_arm @ parent_rest.inverted() @ rest_matrix
                    turn = (expected.to_3x3() @ Vector((0, 1, 0))).normalized().rotation_difference((points[k + 1] - points[k]).normalized())
                    desired = Matrix.Translation(points[k]) @ (turn.to_matrix() @ expected.to_3x3()).to_4x4()
                    basis = expected.inverted() @ desired
                    pb.rotation_mode = 'QUATERNION'
                    pb.rotation_quaternion = basis.to_quaternion()
                    pb.location = basis.translation if k == 0 else Vector()
                    pb.keyframe_insert('rotation_quaternion', frame=frame, group=GROUP)
                    if k == 0:
                        pb.keyframe_insert('location', frame=frame, group=GROUP)
                    parent_arm = desired
                    parent_rest = rest_matrix
    scene.frame_set(1)


chains = build_chains()
convert(chains)
frames, stats = simulate(chains)
bake(chains, frames)
for obj in scene.objects:
    for modifier in obj.modifiers:
        if modifier.type == 'SOLIDIFY' and obj.name in COLLIDERS:
            modifier.show_viewport = True
report = {'panels': {name: {'chains': len(d['chains']), 'segments': SEGMENTS,
                            'hem_z': [round(c['hem'], 3) for c in d['chains']]} for name, d in chains.items()},
          'hinge_z': HINGE_Z, 'clearance_m': CLEARANCE, 'contacts': stats['contacts'],
          'normal_sign': stats['normal_sign'], 'rest_median_gap_mm': stats['rest_median_gap_mm'],
          'deepest_particle_mm': round(stats['deepest_mm'], 1), 'frames': len(frames)}
(out / 'chain_report.json').write_text(json.dumps(report, indent=1))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Candidate.blend'), compress=True)
print('SKIRT CHAIN DONE', json.dumps(report), flush=True)
