"""Settles the jacket skirt panels with cloth at chosen thigh directions and stores the result as rest-space offsets.

The skirt panels are skinned to the pelvis only. For each sample the thigh swings from rest to the sample direction over 30
frames (knee bending with it, as in a chamber), holds for 30 more, and the settled panel shape is read back. Pelvis-only
skinning means the pose's rest-space shape is the settled local shape, so each offset is (settled - settled at rest). These
offsets become thigh-direction-driven shape keys in build_skirt_hip_correctives.py.

    blender.exe -b <Candidate.blend> -P settle_skirt_hip_poses.py -- <out folder> <l|r> <theta deg>:<phi deg> [...]

theta is the swing away from the rest thigh direction; phi is its heading, 0 = straight forward, 90 = straight out to the side.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
SAVE = '--save' in args
args = [a for a in args if a != '--save' and not a.startswith('--goal=')]
out = Path(args[0])
SIDE = args[1]
samples = [tuple(float(v) for v in a.split(':')) for a in args[2:]]
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
PANELS = ('Jacket_Back', 'Jacket_Front_Left', 'Jacket_Front_Right')
panels = [bpy.data.objects[n] for n in PANELS]
SKIRT_MASS_KG = .08
PIN_FULL_Z = .925
PIN_FREE_Z = .905
PIN_GOAL = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--goal=')), .2))
RAMP_END = 30
HOLD_END = 90
DOWN = Vector((0, 0, -1))
FORWARD = Vector((0, -1, 0))
OUT = Vector((1, 0, 0)) if SIDE == 'l' else Vector((-1, 0, 0))

# Static pose only: no action, every bone at rest.
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
thigh = rig.pose.bones['thigh_' + SIDE]
calf = rig.pose.bones['calf_' + SIDE]
for bone in (thigh, calf):
    bone.rotation_mode = 'QUATERNION'

# Only the skirt simulates; it collides with the skinned pants (with their own correctives) and the body.
# The saved cloth modifiers have drivers on their enable switches, so they are removed and the skirt gets a fresh one.
for obj in scene.objects:
    for modifier in list(obj.modifiers):
        if modifier.type == 'COLLISION' and obj.name != 'SIM_Body_Collider':
            obj.modifiers.remove(modifier)
        elif modifier.type == 'CLOTH':
            for prop in ('show_viewport', 'show_render'):
                modifier.driver_remove(prop)
            obj.modifiers.remove(modifier)
for modifier in pants.modifiers:
    if modifier.type == 'SOLIDIFY':
        modifier.show_viewport = False
collision = pants.modifiers.new('SkirtSettleCollision', 'COLLISION')
pants.collision.thickness_outer = .002
pants.collision.thickness_inner = .02

bone_names = set(rig.data.bones.keys())
for panel in panels:
    # Pelvis-only skinning: the correctives carry all thigh-driven motion.
    for group in list(panel.vertex_groups):
        if group.name in bone_names:
            panel.vertex_groups.remove(group)
    pelvis = panel.vertex_groups.new(name='pelvis')
    pelvis.add(range(len(panel.data.vertices)), 1.0, 'REPLACE')
    # The band under the belt is held; below it a soft goal keeps the tailored shape (a free panel buckles chaotically
    # and two identical runs land centimetres apart), so the skirt only changes where the thigh pushes it.
    pin = panel.vertex_groups.new(name='SkirtSettle_Pin')
    for vertex in panel.data.vertices:
        height = (panel.matrix_world @ vertex.co).z
        band = max(0.0, min(1.0, (height - PIN_FREE_Z) / (PIN_FULL_Z - PIN_FREE_Z)))
        pin.add([vertex.index], PIN_GOAL + (1 - PIN_GOAL) * band, 'REPLACE')
    if panel.data.shape_keys:
        for key in panel.data.shape_keys.key_blocks[1:]:
            key.mute = True
    for modifier in panel.modifiers:
        if modifier.type == 'SOLIDIFY':
            modifier.show_viewport = False
    cloth = panel.modifiers.new('SkirtSettle', 'CLOTH')
    settings = cloth.settings
    settings.quality = 10
    settings.mass = SKIRT_MASS_KG / len(panel.data.vertices)
    settings.tension_stiffness = settings.compression_stiffness = 80
    settings.shear_stiffness = 20
    settings.bending_stiffness = 3
    settings.air_damping = 5
    settings.vertex_group_mass = pin.name
    settings.pin_stiffness = 1
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = HOLD_END
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.collection = None
    cloth.collision_settings.distance_min = .003
    cloth.collision_settings.collision_quality = 4
scene.frame_start, scene.frame_end = 1, HOLD_END

world3 = rig.matrix_world.to_3x3().normalized()


def swing_pose(theta, phi):
    """Pose matrices (armature space) for the thigh swung to (theta, phi) and the knee folded as in a kick chamber."""
    t, p = math.radians(theta), math.radians(phi)
    target = DOWN * math.cos(t) + (FORWARD * math.cos(p) + OUT * math.sin(p)) * math.sin(t)
    rotation_world = DOWN.rotation_difference(target).to_matrix()
    rotation = world3.inverted() @ rotation_world @ world3
    rest = rig.data.bones[thigh.name].matrix_local
    head = rest.to_translation()
    thigh_matrix = Matrix.Translation(head) @ rotation.to_4x4() @ Matrix.Translation(-head) @ rest
    knee = -math.radians(min(105.0, theta * .8))
    return thigh_matrix, Matrix.Rotation(knee, 4, 'Z')


def key_pose(frame, thigh_matrix, knee_basis):
    scene.frame_set(frame)
    thigh.matrix = thigh_matrix
    bpy.context.view_layer.update()
    calf.matrix_basis = knee_basis
    for bone in (thigh, calf):
        bone.keyframe_insert('rotation_quaternion', frame=frame)
        bone.keyframe_insert('location', frame=frame)


def settled():
    shapes = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for panel in panels:
        evaluated = panel.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        shapes[panel.name] = [v.co.copy() for v in mesh.vertices]
        evaluated.to_mesh_clear()
    return shapes


def heading_axes():
    """How the thigh's local y and z swing components map onto forward and outward (driver calibration).

    The rig uses UE bone axes: the thigh runs along local -X (hip to knee), so a swing shows up in the local y and z
    components of the rotated x axis, and the knee moves opposite to them."""
    rest = rig.data.bones[thigh.name].matrix_local.to_3x3()
    y_axis, z_axis = (world3 @ rest.col[1]).normalized(), (world3 @ rest.col[2]).normalized()
    return -y_axis.dot(FORWARD), -z_axis.dot(FORWARD), -y_axis.dot(OUT), -z_axis.dot(OUT)


def thigh_angles():
    w, x, y, z = thigh.rotation_quaternion
    b, c = 2 * (x * y + w * z), 2 * (x * z - w * y)
    fy, fz, oy, oz = heading_axes()
    phi = math.degrees(math.atan2(b * oy + c * oz, b * fy + c * fz))
    return math.degrees(math.acos(max(-1, min(1, 1 - 2 * (y * y + z * z))))), phi


def run(theta, phi):
    rig.animation_data_create()
    if rig.animation_data.action:
        bpy.data.actions.remove(rig.animation_data.action)
    rig.animation_data.action = bpy.data.actions.new('SkirtSettle')
    rest_thigh = rig.data.bones[thigh.name].matrix_local.copy()
    key_pose(1, rest_thigh, Matrix.Identity(4))
    thigh_matrix, knee_basis = swing_pose(theta, phi)
    key_pose(RAMP_END, thigh_matrix, knee_basis)
    key_pose(HOLD_END, thigh_matrix, knee_basis)
    for panel in panels:
        # Changing a setting resets the in-memory cloth cache, so each sample starts from rest.
        settings = panel.modifiers['SkirtSettle'].settings
        settings.quality += 1
        settings.quality -= 1
    scene.frame_set(HOLD_END)
    for frame in range(1, HOLD_END + 1):
        scene.frame_set(frame)
        if frame == HOLD_END - 10:
            earlier = settled()
    final = settled()
    still_moving = max((a - b).length for name in PANELS for a, b in zip(final[name], earlier[name])) * 1000
    print('RESIDUAL MOTION mm over last 10 frames', round(still_moving, 2), flush=True)
    return final, thigh_angles()


reference, _ = run(0, 0)
for panel in panels:
    rest = [v.co for v in panel.data.vertices]
    print('REFERENCE SAG mm', panel.name, round(max((r - s).length for r, s in zip(rest, reference[panel.name])) * 1000, 1), flush=True)
for theta, phi in samples:
    shapes, (measured_theta, measured_phi) = run(theta, phi)
    offsets = {name: [list(s - r) for s, r in zip(shapes[name], reference[name])] for name in PANELS}
    peak = max((Vector(o).length for name in PANELS for o in offsets[name]), default=0)
    record = {'side': SIDE, 'theta': theta, 'phi': phi, 'measured_theta': measured_theta, 'measured_phi': measured_phi,
              'heading_axes': heading_axes(), 'max_offset_mm': round(peak * 1000, 1), 'offsets': offsets}
    (out / ('%s_%03d_%03d.json' % (SIDE, theta, phi))).write_text(json.dumps(record))
    print('SAMPLE', SIDE, theta, phi, 'measured', round(measured_theta, 1), round(measured_phi, 1),
          'max offset mm', record['max_offset_mm'], flush=True)
if SAVE:
    # Debug file: the last sample's pose held, its settled shape as a shape key, cloth removed (renders show the result).
    for panel in panels:
        panel.modifiers.remove(panel.modifiers['SkirtSettle'])
        for modifier in panel.modifiers:
            if modifier.type == 'SOLIDIFY':
                modifier.show_viewport = True
        if not panel.data.shape_keys:
            panel.shape_key_add(name='Basis')
        key = panel.shape_key_add(name='Settled', from_mix=False)
        for point, co in zip(key.data, shapes[panel.name]):
            point.co = co
        key.value = 1
        if panel.data.shape_keys.animation_data:
            for fc in list(panel.data.shape_keys.animation_data.drivers):
                panel.data.shape_keys.driver_remove(fc.data_path)
        key.mute = False
    pants.modifiers.remove(collision)
    for modifier in pants.modifiers:
        if modifier.type == 'SOLIDIFY':
            modifier.show_viewport = True
    scene.frame_set(HOLD_END)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Settled_Debug.blend'), compress=True)
print('SETTLE DONE', flush=True)
