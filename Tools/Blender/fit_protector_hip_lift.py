"""Layer 8 of the traditional dobok: a raised thigh pushes the chest protector's lowered hem up out of the way.

The protector hangs over the belt (layer 7) and moves rigidly with the spine, so in a front kick the raised thigh passed
straight through its hem and the blue showed under the thigh. On a fighter the rising thigh pushes the hem back and up
against the belly, where it disappears behind the thigh. Each side gets a shape key (HipRetract_Protector_l/_r, weighted
to that side of the centre line) that folds the panel below a hinge just above the belt up toward the hinge (RETRACT of
its length) and in to the hinge's outline, driven by how far that thigh has swung from rest:
clamp((swing - RAMP_FROM) / (RAMP_TO - RAMP_FROM)). RAMP_FROM sits just above a fighting stance's swing, so the hem hangs
over the belt in stance and steps.

    blender.exe -b <Candidate.blend> -P fit_protector_hip_lift.py -- <out folder>
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
PROTECTORS = ('Quilted_Lace_Back__', 'Smooth_Buckle_Back__')
SHELL_HINT = 'Padded_Torso_Shell'
RETRACT = .85         # share of the panel's length below the hinge folded away at full key
HINGE_ABOVE_BELT = .05
HINGE_SOFT = .03      # m below the hinge over which the fold fades in
SIDE_SOFT = .06       # m either side of the centre line over which left and right blend
RAMP_FROM, RAMP_TO = math.radians(24), math.radians(65)   # thigh swing: stance is about 20 degrees
SWING = 'acos(min(1, max(-1, 1 - 2 * (y * y + z * z))))'   # thigh swing from rest (the UE thigh runs along local -X)
BINS = 72

worn = [o for o in scene.objects if o.type == 'MESH' and o.name.startswith(PROTECTORS) and not o.hide_get() and not o.hide_render]
shell = next(o for o in worn if SHELL_HINT in o.name)
belt = bpy.data.objects['Belt_Waistband']
hinge_z = max((belt.matrix_world @ v.co).z for v in belt.data.vertices) + HINGE_ABOVE_BELT
shell_points = [shell.matrix_world @ v.co for v in shell.data.vertices]
centre = Vector((0, sum(p.y for p in shell_points) / len(shell_points), 0))


def polar(p):
    return math.atan2(p.y - centre.y, p.x - centre.x), math.hypot(p.x - centre.x, p.y - centre.y)


def bin_of(angle):
    return int((angle + math.pi) / (2 * math.pi) * BINS) % BINS


# The shell's outer reach per angle and 1 cm height, and at the hinge: the folded panel tucks in to the hinge's outline.
outer = defaultdict(float)
for p in shell_points:
    a, r = polar(p)
    outer[(bin_of(a), int(p.z * 100))] = max(outer[(bin_of(a), int(p.z * 100))], r)
at_hinge = [outer.get((k, int(hinge_z * 100)), 0.0) for k in range(BINS)]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def retracted(p, side):
    """Rest-space position of p with the side's full retraction."""
    if p.z >= hinge_z:
        return p
    toward = smooth((p.x + SIDE_SOFT) / (2 * SIDE_SOFT))
    share = toward if side == 'l' else 1 - toward
    if share <= 0:
        return p
    depth = hinge_z - p.z
    fold = RETRACT * share * smooth(depth / HINGE_SOFT)
    a, r = polar(p)
    k = bin_of(a)
    tuck = (at_hinge[k] - outer.get((k, int(p.z * 100)), r)) * fold if at_hinge[k] else 0.0
    radial = Vector((p.x - centre.x, p.y - centre.y, 0))
    radial = radial.normalized() if radial.length > 1e-6 else Vector()
    return Vector((p.x, p.y, hinge_z - depth * (1 - fold))) + radial * tuck


def swing_driver(key, side):
    fc = key.driver_add('value')
    d = fc.driver
    for name, index in (('y', 2), ('z', 3)):
        var = d.variables.new()
        var.name = name
        var.type = 'SINGLE_PROP'
        var.targets[0].id = rig
        var.targets[0].data_path = 'pose.bones["thigh_%s"].rotation_quaternion[%d]' % (side, index)
    d.expression = 'max(0, min(1, (%s - %.4f) / %.4f))' % (SWING, RAMP_FROM, RAMP_TO - RAMP_FROM)


for obj in worn:
    if not obj.data.shape_keys:
        obj.shape_key_add(name='Basis', from_mix=False)
    blocks = obj.data.shape_keys.key_blocks
    for old in [k for k in blocks if k.name.startswith(('HipLift_Protector_', 'HipRetract_Protector_'))]:
        obj.shape_key_remove(old)
    basis = obj.data.shape_keys.key_blocks['Basis']
    world, inverse = obj.matrix_world, obj.matrix_world.inverted()
    for side in 'lr':
        key = obj.shape_key_add(name='HipRetract_Protector_' + side, from_mix=False)
        for kp, bp in zip(key.data, basis.data):
            kp.co = inverse @ retracted(world @ bp.co, side)
        key.value = 0
        swing_driver(key, side)
report = {'hinge_z': round(hinge_z, 3), 'retract': RETRACT, 'ramp_deg': [round(math.degrees(RAMP_FROM), 1), round(math.degrees(RAMP_TO), 1)],
          'parts': len(worn)}
print('HIP LIFT DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'hip_lift_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
