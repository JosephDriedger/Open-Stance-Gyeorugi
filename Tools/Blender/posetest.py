"""Stress-test poses for checking deformation (loaded via run("posetest")).

pose_guard(), pose_chamber(), pose_twist(), reset_pose(), or rot(bone, world_axis, degrees).
use_armature("root") switches to another armature (e.g. the MetaHuman body from fit_to_body);
arms_down sets how far the arms still need to drop for the guard (T-pose 70, MetaHuman A-pose ~25).
"""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector
import rig_config as cfg

_ARMATURE = None
ARMS_DOWN = 70


_FOLLOWERS = []


def use_armature(name, arms_down=None, followers=()):
    """followers: armatures that copy this one's pose for shared bone names (e.g. the MetaHuman
    head skeleton "root.001", whose mesh includes the neck and shoulders)."""
    global _ARMATURE, ARMS_DOWN, _FOLLOWERS
    _ARMATURE = name
    _FOLLOWERS = list(followers)
    if arms_down is not None:
        ARMS_DOWN = arms_down


def _arm():
    return bpy.data.objects[_ARMATURE or cfg.ARMATURE_NAME]


def _sync_followers():
    src = _arm()
    for name in _FOLLOWERS:
        dst = bpy.data.objects.get(name)
        if dst is None:
            continue
        shared = [pb for pb in dst.pose.bones if pb.name in src.pose.bones]
        for pb in sorted(shared, key=lambda pb: len(pb.parent_recursive)):
            pb.matrix = dst.matrix_world.inverted() @ src.matrix_world @ src.pose.bones[pb.name].matrix
            bpy.context.view_layer.update()


def reset_pose():
    for arm in [_arm()] + [bpy.data.objects[n] for n in _FOLLOWERS if n in bpy.data.objects]:
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def rot(bone, axis, deg):
    """Rotate a pose bone about a world-space axis through its head."""
    arm = _arm()
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update()
    m = pb.matrix.copy()   # armature space
    head = m.translation.copy()
    local_axis = arm.matrix_world.to_3x3().inverted() @ Vector(axis)
    r = Quaternion(local_axis.normalized(), math.radians(deg)).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(head) @ r @ Matrix.Translation(-head) @ m
    bpy.context.view_layer.update()
    _sync_followers()


def fist(side, amount=1.0):
    """Curl fingers toward the palm. Call while the hand is still in its T-pose orientation."""
    s = 1 if side == 'l' else -1
    for f in ("index", "middle", "ring", "pinky"):
        rot(f"{f}_01_{side}", (0, s, 0), 80 * amount)
        rot(f"{f}_02_{side}", (0, s, 0), 95 * amount)
        rot(f"{f}_03_{side}", (0, s, 0), 60 * amount)
    rot(f"thumb_02_{side}", (0, s, 0), 30 * amount)
    rot(f"thumb_03_{side}", (0, s, 0), 40 * amount)


def pose_guard():
    reset_pose()
    for side, s in (("l", 1), ("r", -1)):
        fist(side)
        rot(f"upperarm_{side}", (0, 1, 0), s * ARMS_DOWN)    # arm down
        rot(f"upperarm_{side}", (0, 0, 1), -s * 30)   # arm forward
        rot(f"lowerarm_{side}", (1, 0, 0), -115)      # elbow bend


def pose_chamber():
    """Round-kick chamber on the left leg with guard."""
    pose_guard()
    rot("calf_l", (1, 0, 0), 125)      # knee bend
    rot("foot_l", (1, 0, 0), 35)       # point the foot
    rot("thigh_l", (1, 0, 0), -95)     # knee up
    rot("thigh_l", (0, 1, 0), 40)      # open the hip
    rot("spine_03", (0, 0, 1), -15)
    rot("spine_01", (0, 1, 0), -10)


def pose_twist():
    pose_guard()
    rot("spine_01", (0, 0, 1), 15)
    rot("spine_03", (0, 0, 1), 15)
    rot("spine_05", (0, 0, 1), 10)
    rot("neck_01", (0, 0, 1), -20)
    rot("head", (1, 0, 0), 15)
    rot("calf_r", (1, 0, 0), 40)
    rot("thigh_r", (1, 0, 0), -30)
