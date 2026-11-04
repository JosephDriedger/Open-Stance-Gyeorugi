"""Keyframe rough placeholder animations for every Skill Stick technique, until the mocap versions exist.

Each technique is authored once, thrown with the RIGHT (rear) leg or hand from a LEFT-lead fighting stance, facing -Y,
in place: the greybox turns the whole fighter for spinning kicks and lifts it for jump kicks, and mirrors it for left-leg
techniques and right-lead stances. Poses are written as targets (where the feet and fists go, which way the knees and
elbows point, how the hips and chest turn) and solved with two-bone IK, then keyed on the fighter rig.
Timing comes from Data/Combat/DT_MoveData.csv: the clip lasts the technique's longest startup + active + recovery, the
strike is fully out at the end of startup and held through active, so the greybox can scrub the clip by combat phase.

    blender.exe -b Resources/Models/CharacterSuite/Medium/Gameplay_High.blend -P build_placeholder_techniques.py -- <out folder>

Saves <out folder>/PlaceholderTechniques.blend (one action per technique plus Stance) and one FBX per action
(armature only, named `root`, centimetres) for import onto the production fighter skeleton.
"""
import csv
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else ROOT / 'Resources/Models/Animation/PlaceholderTechniques'
FPS = 30
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
W = rig.matrix_world
Wi = W.inverted()
bones = rig.data.bones
REST = {b.name: W @ b.matrix_local for b in bones}           # world-space rest matrices (metres)


def head(name):
    return REST[name].translation.copy()


HIP_Z = head('pelvis').z
LEG = (head('calf_l') - head('thigh_l')).length, (head('foot_l') - head('calf_l')).length
ARM = (head('lowerarm_l') - head('upperarm_l')).length, (head('hand_l') - head('lowerarm_l')).length
FOOT_Z = head('foot_l').z


def yaw(deg):
    return Quaternion((0, 0, 1), math.radians(deg))


def V(x, y, z):
    return Vector((x, y, z))


# ---- pose model -------------------------------------------------------------------------------------------------------
# A pose: pelvis (drop m, yaw/pitch/roll deg), chest (yaw/pitch/roll deg spread over the spine), head look (yaw deg from
# the opponent line), and per limb a target point (world, metres, fighter at origin facing -Y), a pole (which way the
# knee or elbow points) and for feet a toe direction. Distances scale with the body: written for a 0.92 m hip height.
S = HIP_Z / .915


def stance():
    # Sparring stance (gyeorugi junbi): side-on with the left foot leading, feet a long step apart on the opponent line,
    # knees soft and weight on the balls of the feet; fists closed, lead fist forward at shoulder height, rear fist by
    # the chin, elbows down guarding the trunk. Between the user's two reference photos (WT upright, and a lower base).
    return {
        'pelvis': dict(drop=.085, yaw=-52, pitch=0, roll=0, shift=V(0, 0, 0)),
        'chest': dict(yaw=14, pitch=5, roll=0),
        'look': 0,
        'foot_l': dict(at=V(.10, -.33, FOOT_Z), pole=V(.5, -1, .2), toe=V(-.25, -1, 0)),
        'foot_r': dict(at=V(-.13, .30, FOOT_Z), pole=V(-.4, -1, .1), toe=V(-1, -.35, 0)),
        'hand_l': dict(at=V(.07, -.40, 1.30), pole=V(.5, .1, -1)),
        'hand_r': dict(at=V(-.05, -.26, 1.35), pole=V(-.5, .2, -1)),
    }


def pose(**changes):
    """A stance with some parts changed: pass pelvis=dict(...), foot_r=dict(...), etc. (merged into the stance's)."""
    p = stance()
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(p.get(key), dict):
            p[key] = {**p[key], **value}
        else:
            p[key] = value
    return p


def two_bone(root, target, lengths, pole):
    """Middle-joint position for a two-bone chain from root reaching target, bending toward pole."""
    a, b = lengths
    to = target - root
    d = min(max(to.length, 1e-4), a + b - 1e-4)
    to.normalize()
    cos_a = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    side = (pole - to * pole.dot(to))
    side = side.normalized() if side.length > 1e-6 else to.orthogonal().normalized()
    return root + to * (a * cos_a) + side * (a * math.sqrt(max(0.0, 1 - cos_a * cos_a)))


def aim_rotation(current, desired):
    return current.normalized().rotation_difference(desired.normalized())


def solve(p):
    """World-space posed matrices for the bones a pose drives (others follow their parents)."""
    posed = {}

    def baseline(name):
        bone = bones[name]
        if bone.parent is None:
            return REST[name].copy()
        parent = bone.parent.name
        delta = posed.get(parent, None)
        if delta is None:
            delta = baseline(parent)
            posed[parent] = delta
        return delta @ REST[parent].inverted() @ REST[name]

    def rotate(name, rotation, about=None):
        m = baseline(name)
        h = m.translation.copy() if about is None else about
        posed[name] = Matrix.Translation(h) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-h) @ m

    def child_head(name, child):
        return posed[name] @ (REST[name].inverted() @ head(child))

    # pelvis: drop, shift, turn
    pv = p['pelvis']
    turn = yaw(pv['yaw']) @ Quaternion((1, 0, 0), math.radians(pv['pitch'])) @ Quaternion((0, 1, 0), math.radians(pv['roll']))
    m = REST['pelvis']
    h = m.translation.copy()
    posed['pelvis'] = Matrix.Translation(h + V(0, 0, -pv['drop'] * S) + pv['shift'] * S) @ turn.to_matrix().to_4x4() @ Matrix.Translation(-h) @ m

    # chest: spread over the spine
    ch = p['chest']
    spine = ['spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05']
    part = Quaternion((0, 0, 1), math.radians(ch['yaw'] / 5)) @ Quaternion((1, 0, 0), math.radians(ch['pitch'] / 5)) @ \
        Quaternion((0, 1, 0), math.radians(ch['roll'] / 5))
    for name in spine:
        rotate(name, part)

    # head: face the opponent line (-Y), turned by `look`
    for name, share in (('neck_01', .5), ('head', 1.0)):
        m = baseline(name)
        forward = m.to_3x3() @ (REST[name].to_3x3().inverted() @ V(0, -1, 0))
        forward.z = 0
        want = yaw(p['look']) @ V(0, -1, 0)
        r = Quaternion().slerp(aim_rotation(forward, want), share) if forward.length > 1e-6 else Quaternion()
        rotate(name, r)

    # legs and arms: two-bone IK onto targets
    for side in 'lr':
        foot = p['foot_' + side]
        posed_thigh = baseline('thigh_' + side)
        hip = posed_thigh.translation.copy()
        target = foot['at'] * 1.0
        target = V(target.x * S, target.y * S, target.z if foot['at'].z == FOOT_Z else target.z * S)
        knee = two_bone(hip, target, LEG, foot['pole'])
        posed['thigh_' + side] = posed_thigh
        rotate('thigh_' + side, aim_rotation(child_head('thigh_' + side, 'calf_' + side) - hip, knee - hip))
        calf = baseline('calf_' + side)
        posed['calf_' + side] = calf
        ankle = calf.translation.copy()
        rotate('calf_' + side, aim_rotation(child_head('calf_' + side, 'foot_' + side) - ankle, target - ankle))
        ft = baseline('foot_' + side)
        posed['foot_' + side] = ft
        f0 = ft.translation.copy()
        toe = foot['toe'].normalized()
        # A level toe direction keeps the rest pose's ankle-to-ball slope, so a planted foot lands flat instead of
        # pointing down; a toe direction with its own height (a chambered or extended kick) is used as given.
        if abs(toe.z) < 1e-6:
            rest = head('ball_' + side) - head('foot_' + side)
            toe = (toe * math.hypot(rest.x, rest.y) + V(0, 0, rest.z)).normalized()
        rotate('foot_' + side, aim_rotation(child_head('foot_' + side, 'ball_' + side) - f0, toe))

        hand = p['hand_' + side]
        upper = baseline('upperarm_' + side)
        shoulder = upper.translation.copy()
        target = V(hand['at'].x * S, hand['at'].y * S, hand['at'].z * S)
        elbow = two_bone(shoulder, target, ARM, hand['pole'])
        posed['upperarm_' + side] = upper
        rotate('upperarm_' + side, aim_rotation(child_head('upperarm_' + side, 'lowerarm_' + side) - shoulder, elbow - shoulder))
        lower = baseline('lowerarm_' + side)
        posed['lowerarm_' + side] = lower
        e0 = lower.translation.copy()
        rotate('lowerarm_' + side, aim_rotation(child_head('lowerarm_' + side, 'hand_' + side) - e0, target - e0))
    return posed


KEYED = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'head'] + \
    [f'{b}_{s}' for s in 'lr' for b in ('thigh', 'calf', 'foot', 'upperarm', 'lowerarm')]


# Closed fists on every key: each finger joint curls toward the palm about the axis across the finger (from the rest
# pose, so it works on any body built on this rig), the thumb wraps across. Left unkeyed, the fingers stay in the rest
# pose's open hand, which reads as a claw.
FINGER_CURL = {'01': 82, '02': 98, '03': 72}
THUMB_CURL = {'01': 22, '02': 38, '03': 42}


def _fist_rotations():
    rotations = {}
    for side in 'lr':
        hand = head('hand_' + side)
        across = head('pinky_01_' + side) - head('index_01_' + side)
        along = head('middle_01_' + side) - hand
        palm = along.cross(across).normalized()
        # the thumb sits on the palm side of the hand plane (tested on the left hand; the right is its mirror, since on
        # the right the thumb test picked the back of the hand)
        if side == 'l':
            if (head('thumb_02_l') - hand).dot(palm) < 0:
                palm = -palm
            left_palm = palm
        else:
            palm = Vector((-left_palm.x, left_palm.y, left_palm.z))
        for finger in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            curls = THUMB_CURL if finger == 'thumb' else FINGER_CURL
            for joint, degrees in curls.items():
                name = f'{finger}_{joint}_{side}'
                if name not in bones:
                    continue
                # This rig's finger bones (UE/MetaHuman convention) run along their local X and hinge about their local
                # Z, the same axis for every joint of a finger; Blender's bone Y (head to tail) does not follow the
                # finger, so the hinge is taken from the bone frame and only its sign from the hand: the one that turns
                # the finger toward the palm (the thumb toward the palm and the little finger).
                frame = REST[name].to_3x3()
                direction = frame.col[0].normalized()
                hinge = frame.col[2].normalized()
                toward = ((across.normalized() + palm) if finger == 'thumb' else palm).normalized()
                turned = Quaternion(hinge, math.radians(degrees)) @ direction
                sign = 1.0 if (turned - direction).dot(toward) >= 0 else -1.0
                # The right side's bone axes mirror the left's (UE convention), so it takes the left joint's rotation as is.
                left = f'{finger}_{joint}_l'
                rotations[name] = rotations[left] if side == 'r' and left in rotations else \
                    Quaternion((0.0, 0.0, 1.0), sign * math.radians(degrees))
    return rotations


FIST = _fist_rotations()


def key_fists(frame):
    for name, rotation in FIST.items():
        pb = rig.pose.bones[name]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = rotation
        pb.keyframe_insert('rotation_quaternion', frame=frame)


def key_pose(p, frame):
    key_fists(frame)
    posed = solve(p)
    for name in KEYED:
        bone = bones[name]
        pb = rig.pose.bones[name]
        world = posed.get(name)
        if world is None:
            continue
        arm = Wi @ world
        if bone.parent is None:
            basis = bone.matrix_local.inverted() @ arm
        else:
            parent_world = posed.get(bone.parent.name)
            parent_arm = Wi @ parent_world if parent_world is not None else bone.parent.matrix_local
            basis = bone.matrix_local.inverted() @ bone.parent.matrix_local @ parent_arm.inverted() @ arm
        loc, rot, _ = basis.decompose()
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = rot
        pb.location = loc if name == 'pelvis' else Vector()
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if name == 'pelvis':
            pb.keyframe_insert('location', frame=frame)


# ---- techniques -------------------------------------------------------------------------------------------------------
# Each: list of (phase, pose). Phases: 0 start, 'S' end of startup (strike fully out), 'A' end of active, 1 end of
# recovery; numbers in between are fractions of the whole clip.
STANCE = stance()
CHAMBER_R = dict(at=V(-.04, -.12, .62), pole=V(0, -1, .6), toe=V(0, .3, -1))


def roundhouse(height):
    return [
        (0, STANCE),
        ('S/2', pose(pelvis=dict(yaw=-90, roll=-8), chest=dict(yaw=40), foot_r=CHAMBER_R,
                     foot_l=dict(toe=V(.6, -.8, 0)))),
        ('S', pose(pelvis=dict(yaw=-115, roll=-22, drop=.04), chest=dict(yaw=60, roll=8), look=0,
                   foot_r=dict(at=V(.05, -.78, height), pole=V(0, 0, 1), toe=V(.9, -.2, -.2)),
                   foot_l=dict(toe=V(.9, -.4, 0)), hand_r=dict(at=V(-.25, .05, 1.0), pole=V(-.4, .6, -1)))),
        ('A', pose(pelvis=dict(yaw=-115, roll=-22, drop=.04), chest=dict(yaw=60, roll=8),
                   foot_r=dict(at=V(.02, -.75, height), pole=V(0, 0, 1), toe=V(.9, -.2, -.2)),
                   foot_l=dict(toe=V(.9, -.4, 0)), hand_r=dict(at=V(-.25, .05, 1.0), pole=V(-.4, .6, -1)))),
        ('A+R/2', pose(pelvis=dict(yaw=-90, roll=-8), chest=dict(yaw=40), foot_r=CHAMBER_R)),
        (1, STANCE),
    ]


def side_kick(height):
    out = dict(pelvis=dict(yaw=-125, pitch=0, roll=-25, drop=.03), chest=dict(yaw=40, roll=10), look=-10,
               foot_l=dict(toe=V(1, .3, 0)), hand_r=dict(at=V(-.30, .15, 1.0), pole=V(-.2, .6, -1)))
    return [
        (0, STANCE),
        ('S/2', pose(pelvis=dict(yaw=-100, roll=-6), chest=dict(yaw=30), foot_r=dict(at=V(.0, -.05, .66), pole=V(0, -1, 1), toe=V(1, 0, -.4)),
                     foot_l=dict(toe=V(.9, .1, 0)))),
        ('S', pose(**out, foot_r=dict(at=V(.04, -.82, height), pole=V(0, 0, 1), toe=V(1, 0, .3)))),
        ('A', pose(**out, foot_r=dict(at=V(.04, -.80, height), pole=V(0, 0, 1), toe=V(1, 0, .3)))),
        ('A+R/2', pose(pelvis=dict(yaw=-100, roll=-6), chest=dict(yaw=30), foot_r=dict(at=V(.0, -.05, .66), pole=V(0, -1, 1), toe=V(1, 0, -.4)))),
        (1, STANCE),
    ]


def hook(height):
    out = dict(pelvis=dict(yaw=-125, roll=-25, drop=.03), chest=dict(yaw=40, roll=10), foot_l=dict(toe=V(1, .3, 0)),
               hand_r=dict(at=V(-.30, .15, 1.0), pole=V(-.2, .6, -1)))
    return [
        (0, STANCE),
        ('S/2', pose(pelvis=dict(yaw=-100, roll=-6), chest=dict(yaw=30), foot_r=dict(at=V(.0, -.05, .7), pole=V(0, -1, 1), toe=V(1, 0, -.4)),
                     foot_l=dict(toe=V(.9, .1, 0)))),
        ('S', pose(**out, foot_r=dict(at=V(.40, -.70, height), pole=V(0, 0, 1), toe=V(1, 0, .2)))),
        ('A', pose(**out, foot_r=dict(at=V(-.10, -.62, height + .05), pole=V(.3, 1, .4), toe=V(0, 1, .2)))),
        ('A+R/2', pose(pelvis=dict(yaw=-100, roll=-6), chest=dict(yaw=30), foot_r=dict(at=V(.0, -.1, .65), pole=V(0, -1, 1), toe=V(1, 0, -.4)))),
        (1, STANCE),
    ]


def axe():
    return [
        (0, STANCE),
        ('S/2', pose(pelvis=dict(yaw=-30, pitch=-6), foot_r=dict(at=V(-.02, -.55, 1.15), pole=V(0, -.3, 1), toe=V(0, -1, .5)))),
        ('S', pose(pelvis=dict(yaw=-25, pitch=-12), chest=dict(pitch=-8), foot_r=dict(at=V(.0, -.40, 1.72), pole=V(0, -1, 0), toe=V(0, -.3, 1)))),
        ('A', pose(pelvis=dict(yaw=-25, pitch=4), chest=dict(pitch=10), foot_r=dict(at=V(.0, -.62, .95), pole=V(0, -1, 0), toe=V(0, -1, -.3)))),
        ('A+R/2', pose(pelvis=dict(yaw=-30), foot_r=dict(at=V(.0, -.45, .35), pole=V(0, -1, .3), toe=V(0, -1, -.2)))),
        (1, STANCE),
    ]


def punch():
    out = dict(pelvis=dict(yaw=-10), chest=dict(yaw=-25, pitch=8), foot_r=dict(toe=V(-.8, -.6, 0)),
               hand_r=dict(at=V(.02, -.62, 1.30), pole=V(-1, 0, -.5)), hand_l=dict(at=V(.08, -.22, 1.28), pole=V(1, 0, -1)))
    return [(0, STANCE), ('S', pose(**out)), ('A', pose(**out)), (1, STANCE)]


def back_kick(height):
    # in place: the greybox has turned the fighter half round by the end of startup, so the kick goes out the back (+Y)
    out = dict(pelvis=dict(yaw=-40, pitch=-14, drop=.02), chest=dict(pitch=-12), look=180,
               foot_r=dict(at=V(-.02, .82, height), pole=V(0, 0, 1), toe=V(0, .3, -1)))
    return [
        (0, STANCE),
        ('S/2', pose(look=150, foot_r=dict(at=V(-.04, .10, .62), pole=V(0, -1, .3), toe=V(0, .2, -1)))),
        ('S', pose(**out)), ('A', pose(**out)),
        ('A+R/2', pose(look=60, foot_r=dict(at=V(-.04, .10, .60), pole=V(0, -1, .3), toe=V(0, .2, -1)))),
        (1, STANCE),
    ]


def spin_hook(height):
    # straight leg out behind, sweeping round with the turn the greybox applies
    sweep = lambda x, y: pose(pelvis=dict(yaw=-40, roll=18, drop=.02), chest=dict(roll=-10), look=170,
                              foot_r=dict(at=V(x, y, height), pole=V(0, 0, 1), toe=V(0, 1, .2)))
    return [
        (0, STANCE),
        ('S/2', pose(look=150, foot_r=dict(at=V(-.20, .25, .75), pole=V(-1, 0, .3), toe=V(-.5, 1, 0)))),
        ('S', sweep(-.55, .60)), ('A', sweep(.30, .75)),
        ('A+R/2', pose(look=40, foot_r=dict(at=V(-.05, .1, .55), pole=V(0, -1, .3), toe=V(0, .2, -1)))),
        (1, STANCE),
    ]


def tornado(height):
    # the greybox spins and lifts the fighter; the leg chambers through the turn and snaps a roundhouse at the end
    tuck = pose(pelvis=dict(drop=-.02), foot_l=dict(at=V(.08, .05, .45), pole=V(0, -1, .5), toe=V(0, -1, -.4)), foot_r=CHAMBER_R)
    return [
        (0, STANCE),
        ('S/2', tuck),
        ('S', pose(pelvis=dict(yaw=-115, roll=-22), chest=dict(yaw=60, roll=8),
                   foot_r=dict(at=V(.05, -.78, height), pole=V(0, 0, 1), toe=V(.9, -.2, -.2)),
                   foot_l=dict(at=V(.10, .05, .40), pole=V(0, -1, .5), toe=V(0, -1, -.4)))),
        ('A', pose(pelvis=dict(yaw=-115, roll=-22), chest=dict(yaw=60, roll=8),
                   foot_r=dict(at=V(.03, -.75, height), pole=V(0, 0, 1), toe=V(.9, -.2, -.2)),
                   foot_l=dict(at=V(.10, .05, .40), pole=V(0, -1, .5), toe=V(0, -1, -.4)))),
        ('A+R/2', pose(foot_r=CHAMBER_R)),
        (1, STANCE),
    ]


TECHNIQUES = {
    'SideKick': lambda: side_kick(1.05), 'Roundhouse': lambda: roundhouse(1.05), 'Hook': lambda: hook(1.35),
    'Axe': axe, 'Punch': punch, 'SpinSide': lambda: back_kick(1.0), 'SpinHook': lambda: spin_hook(1.30),
    'Tornado': lambda: tornado(1.15),
}


def timings():
    rows = list(csv.DictReader(open(ROOT / 'Data/Combat/DT_MoveData.csv', encoding='utf-8')))
    out = {}
    for r in rows:
        s, a, rec = float(r['StartupSeconds']), float(r['ActiveSeconds']), float(r['RecoverySeconds'])
        t = r['Technique']
        if t not in out or s + a + rec > sum(out[t]):
            out[t] = (s, a, rec)
    return out


def phase_frame(phase, s, a, rec):
    total = s + a + rec
    named = {'S': s, 'A': s + a, 'S/2': s / 2, 'A+R/2': s + a + rec / 2}
    seconds = named[phase] if isinstance(phase, str) else phase * total
    return 1 + round(seconds * FPS)


def build():
    scene.render.fps = FPS
    rig.animation_data_create()
    times = timings()
    made = {}
    stance_action = bpy.data.actions.new('Placeholder_Stance')
    stance_action.use_fake_user = True
    rig.animation_data.action = stance_action
    key_pose(STANCE, 1)
    key_pose(STANCE, 31)
    made['Stance'] = {'action': stance_action.name, 'frames': 31}
    for name, keys in TECHNIQUES.items():
        s, a, rec = times[name]
        action = bpy.data.actions.new('Placeholder_' + name)
        action.use_fake_user = True
        rig.animation_data.action = action
        last = 1
        for phase, p in keys():
            frame = max(last, phase_frame(phase, s, a, rec))
            key_pose(p, frame)
            last = frame + 1
        made[name] = {'action': action.name, 'frames': last - 1, 'startup_s': s, 'active_s': a, 'recovery_s': rec}
    return made


def export(made):
    OUT.mkdir(parents=True, exist_ok=True)
    rig.name = 'root'
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    for name, info in made.items():
        action = bpy.data.actions[info['action']]
        rig.animation_data.action = action
        scene.frame_start, scene.frame_end = 1, info['frames']
        with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[rig]):
            bpy.ops.export_scene.fbx(filepath=str(OUT / f'Placeholder_{name}.fbx'), use_selection=True, object_types={'ARMATURE'},
                                     add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                                     bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                                     apply_scale_options='FBX_SCALE_NONE', use_armature_deform_only=False)


if __name__ == '__main__' or 'NOEXPORT' not in globals():
    made = build()
    for o in scene.objects:
        for m in o.modifiers:
            if m.type == 'CLOTH':
                for prop in ('show_viewport', 'show_render'):
                    m.driver_remove(prop)
                m.show_viewport = m.show_render = False
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'techniques.json').write_text(json.dumps(made, indent=1))
    if '--' in sys.argv:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PlaceholderTechniques.blend'), compress=True)
        export(made)
    print('PLACEHOLDER TECHNIQUES DONE', json.dumps({k: v['frames'] for k, v in made.items()}), flush=True)
