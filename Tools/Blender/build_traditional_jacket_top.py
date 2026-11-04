"""Layer 3 of the traditional dobok: loosen the wrap jacket's torso and sleeves to a boxy, straight cut and drape it.

A traditional wrap-front dobok jacket hangs as a straight box from the armpit down and has straight, wide sleeves; the
fitted jacket follows the chest and tapers the sleeve. This keeps the jacket's topology, wrap overlap, neckline and
weights, and only pushes it outward:
  torso   below the armpit, every angle is pushed out to that angle's widest reach (a straight box) plus BOX_EASE,
          fading out over the shoulders; pushes are per angle and height from the outermost layer, so the inner wrap
          flap moves with the outer one instead of being flattened onto it.
  sleeves round the shoulder-elbow-wrist line, out to a straight sleeve SLEEVE_TOP_GIRTH -> SLEEVE_CUFF_GIRTH round.
Then it drapes with cloth on the bind-pose body over the trousers (shoulders and neck held, self collision on).

Run after build_traditional_trousers.py (the jacket layer goes over the trousers):
    blender.exe -b <Candidate.blend> -P build_traditional_jacket_top.py -- <out folder>
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
jacket = bpy.data.objects['Jacket']
body = bpy.data.objects['Body']
pants = bpy.data.objects['Pants']
W = rig.matrix_world
BOX_EASE = .005
BOX_BLEND = .35     # share of the full box push: a real dobok hangs a few cm off the body, not as a rigid box
SLEEVE_TOP_GIRTH, SLEEVE_CUFF_GIRTH = .40, .32   # m round: loose, not ballooned (sparring photos)
ANGLE_BINS, HEIGHT_STEP = 72, .02
DRAPE_FRAMES = 0      # set > 0 to drape the loosened jacket (see the note at the drape)
GOAL = .35          # soft hold toward the loosened shape everywhere


def head(name):
    return W @ rig.data.bones[name].head_local


bones = set(rig.data.bones.keys())
names = {g.index: g.name for g in jacket.vertex_groups}
mesh = jacket.data
points = [jacket.matrix_world @ v.co for v in mesh.vertices]
role = []
for v in mesh.vertices:
    ws = [(names[g.group], g.weight) for g in v.groups if names[g.group] in bones]
    top = max(ws, key=lambda w: w[1])[0] if ws else 'pelvis'
    role.append(('arm_' + top[-1]) if top.startswith(('upperarm', 'lowerarm', 'hand')) else 'torso')
# The wrap's overlap edge (the open boundary loop running from the hem up to the neck), found before anything moves and
# kept by vertex index for the skirt and collar layers (after the drape a sagging cuff can hang lower than the hem).
import bmesh
from collections import defaultdict as _dd
_bm = bmesh.new()
_bm.from_mesh(mesh)
_links = _dd(list)
for e in _bm.edges:
    if e.is_boundary:
        a, b = (v.index for v in e.verts)
        _links[a].append(b)
        _links[b].append(a)
_bm.free()
_loops, _seen = [], set()
for start in _links:
    if start in _seen:
        continue
    stack, members = [start], []
    while stack:
        i = stack.pop()
        if i not in _seen:
            _seen.add(i)
            members.append(i)
            stack += _links[i]
    _loops.append(members)
_hem = min(p.z for p in points)
_edge = max((l for l in _loops if min(points[i].z for i in l) < _hem + .02),
            key=lambda l: max(points[i].z for i in l) - min(points[i].z for i in l))
jacket['OverlapEdgeVerts'] = _edge
armpit_z = head('upperarm_l').z - .10
shoulder_z = head('upperarm_l').z + .02
hem_z = min(p.z for p in points)
centre = Vector((0, sum(p.y for p, r in zip(points, role) if r == 'torso') / max(1, role.count('torso')), 0))
moves = [Vector() for _ in points]

# --- torso: a straight box below the armpit ----------------------------------------------------------------------------
def polar(p):
    return math.atan2(p.y - centre.y, p.x - centre.x), math.hypot(p.x - centre.x, p.y - centre.y)


def abin(angle):
    return int((angle + math.pi) / (2 * math.pi) * ANGLE_BINS) % ANGLE_BINS


outer = defaultdict(float)          # (angle bin, height bin) -> outermost radius
box = [0.0] * ANGLE_BINS            # angle bin -> widest radius between hem and armpit
for p, r in zip(points, role):
    if r != 'torso':
        continue
    a, rad = polar(p)
    k = abin(a)
    outer[(k, int(p.z / HEIGHT_STEP))] = max(outer[(k, int(p.z / HEIGHT_STEP))], rad)
    if p.z <= armpit_z:
        box[k] = max(box[k], rad)
for _ in range(3):
    box = [max(box[i], (box[i - 1] + 2 * box[i] + box[(i + 1) % ANGLE_BINS]) / 4) for i in range(ANGLE_BINS)]
for i, (p, r) in enumerate(zip(points, role)):
    if r != 'torso' or p.z > shoulder_z:
        continue
    a, rad = polar(p)
    k = abin(a)
    w = 1.0 if p.z <= armpit_z else 1 - (p.z - armpit_z) / (shoulder_z - armpit_z)
    w = w * w * (3 - 2 * w)
    push = max(0.0, box[k] + BOX_EASE - outer[(k, int(p.z / HEIGHT_STEP))]) * w * BOX_BLEND
    moves[i] = Vector((math.cos(a), math.sin(a), 0)) * push

# --- sleeves: straight and wide round the arm line ---------------------------------------------------------------------
for side in 'lr':
    line = [head('upperarm_' + side), head('lowerarm_' + side), head('hand_' + side)]
    lengths = [(line[1] - line[0]).length, (line[2] - line[1]).length]
    total = sum(lengths)

    def project(p):
        best = None
        for s, (a, b) in enumerate(zip(line, line[1:])):
            d = b - a
            t = max(0.0, min(1.0, (p - a).dot(d) / d.length_squared))
            foot = a + d * t
            dist = (p - foot).length
            if best is None or dist < best[0]:
                best = (dist, foot, (sum(lengths[:s]) + t * lengths[s]) / total, d.normalized())
        return best
    sleeve = [i for i, r in enumerate(role) if r == 'arm_' + side]
    outer_arm = defaultdict(float)
    info = {}
    for i in sleeve:
        dist, foot, t, axis = project(points[i])
        radial = points[i] - foot
        radial -= axis * radial.dot(axis)
        ref = axis.orthogonal().normalized()
        angle = math.atan2(radial.dot(axis.cross(ref)), radial.dot(ref))
        key = (int(t * 30), int((angle + math.pi) / (2 * math.pi) * 24) % 24)
        outer_arm[key] = max(outer_arm[key], radial.length)
        info[i] = (radial, t, key)
    for i, (radial, t, key) in info.items():
        target = (SLEEVE_TOP_GIRTH + (SLEEVE_CUFF_GIRTH - SLEEVE_TOP_GIRTH) * t) / (2 * math.pi)
        fade = min(1.0, t / .12)               # blend into the shoulder
        push = max(0.0, target - outer_arm[key]) * fade
        if radial.length > 1e-6:
            moves[i] = radial.normalized() * push

inverse = jacket.matrix_world.inverted().to_3x3()
for v, move in zip(mesh.vertices, moves):
    v.co += inverse @ move
mesh.update()
report = {'armpit_z': round(armpit_z, 3), 'hem_z': round(hem_z, 3),
          'box_girth_cm': round(sum(2 * math.pi / ANGLE_BINS * (r + BOX_EASE) for r in box) * 100, 1),
          'max_push_cm': round(max(m.length for m in moves) * 100, 1)}

# --- drape on the bind-pose body over the trousers ---------------------------------------------------------------------
# Off by default: this jacket is several unjoined panels, and even with a soft goal the drape lifts the hem over the
# trousers, crumples the shoulders and pulls the sleeves off the wrists. The push alone gives the boxy cut.
if DRAPE_FRAMES > 0:
    pose_position = rig.data.pose_position
    rig.data.pose_position = 'REST'
    drape = jacket.copy()
    drape.data = mesh.copy()
    drape.name = 'Jacket_Drape'
    scene.collection.objects.link(drape)
    for modifier in list(drape.modifiers):
        if modifier.type == 'CLOTH':
            for prop in ('show_viewport', 'show_render'):
                modifier.driver_remove(prop)
        if modifier.type != 'ARMATURE':
            drape.modifiers.remove(modifier)
    if drape.animation_data:
        drape.animation_data_clear()
    contacts = []
    for source, thickness in ((body, .006), (pants, .004)):
        proxy = source.copy()
        proxy.data = source.data.copy()
        proxy.name = source.name + '_JacketContact'
        scene.collection.objects.link(proxy)
        if proxy.animation_data:
            proxy.animation_data_clear()
        for modifier in list(proxy.modifiers):
            if modifier.type != 'ARMATURE':
                proxy.modifiers.remove(modifier)
        proxy.modifiers.new('Contact', 'COLLISION')
        proxy.collision.thickness_outer = thickness
        contacts.append(proxy)
    muted = []
    for obj in scene.objects:
        if obj in contacts:
            continue
        for modifier in obj.modifiers:
            if modifier.type == 'COLLISION' and modifier.show_viewport:
                modifier.show_viewport = False
                muted.append(modifier)
    pin = drape.vertex_groups.new(name='Drape_Shoulders')
    for v, p, r in zip(drape.data.vertices, points, role):
        hold = max(0.0, min(1.0, (p.z - (shoulder_z - .06)) / .05)) if r == 'torso' else max(0.0, min(1.0, (p.z - (shoulder_z - .02)) / .04))
        # The jacket is several unjoined panels (body pieces, sleeves, collar layers): a soft goal everywhere keeps the loose
        # ones from dropping off, so the drape only adds folds.
        pin.add([v.index], max(hold, GOAL), 'REPLACE')
    cloth = drape.modifiers.new('Drape', 'CLOTH')
    s = cloth.settings
    s.quality = 12
    s.mass = .5 / len(mesh.vertices)
    s.tension_stiffness = s.compression_stiffness = 400
    s.shear_stiffness = 60
    s.bending_stiffness = 8
    s.air_damping = 2
    s.vertex_group_mass = pin.name
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.collection = None
    cloth.collision_settings.distance_min = .004
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.self_distance_min = .003
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = DRAPE_FRAMES
    frame = scene.frame_current
    for f in range(1, DRAPE_FRAMES + 1):
        scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    draped = bpy.data.meshes.new_from_object(drape.evaluated_get(depsgraph), depsgraph=depsgraph)
    report['drape_max_move_cm'] = round(max((a.co - b.co).length for a, b in zip(draped.vertices, mesh.vertices)) * 100, 1)
    for v, d in zip(mesh.vertices, draped.vertices):
        v.co = d.co
    mesh.update()
    bpy.data.meshes.remove(draped)
    data = drape.data
    bpy.data.objects.remove(drape, do_unlink=True)
    bpy.data.meshes.remove(data)
    for proxy in contacts:
        data = proxy.data
        bpy.data.objects.remove(proxy, do_unlink=True)
        bpy.data.meshes.remove(data)
    for modifier in muted:
        modifier.show_viewport = True
    rig.data.pose_position = pose_position
    scene.frame_set(frame)
print('JACKET TOP DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'jacket_top_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
