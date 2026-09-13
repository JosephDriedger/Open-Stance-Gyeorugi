"""Add body-type shape keys (UE morph targets) to the combined mesh before the part split.

Offsets are computed once on SK_Fighter, pushing out from the body axes, so every split
part gets identical per-vertex offsets and layered clothing stays aligned. Head, helmet, hands and
feet are excluded (gear there shouldn't change size with body type).

Shape keys: BodyHeavy, BodyMuscular, BodySlim. Drive the same value on every part.
"""
import bpy
from mathutils import Vector
import rig_config as cfg

log = cfg.open_log("body_shapes")

mesh = bpy.data.objects[cfg.MESH_NAME]
me = mesh.data
mw = mesh.matrix_world


def ss(x, a, b):
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    t = (x - a) / (b - a)
    return t * t * (3 - 2 * t)


def body_mask(co):
    """1 on torso/limbs, fading to 0 at the neck, wrists and ankles."""
    x, y, z = co
    ax = abs(x)
    m = 1.0 - ss(z, 1.36, 1.44)          # neck / head / helmet
    m *= 1.0 - ss(ax, 0.58, 0.65)        # hands and gloves
    m *= ss(z, 0.10, 0.20)               # feet and foot guards
    return m


def region(co):
    """Soft region weights used to shape each body type."""
    x, y, z = co
    ax = abs(x)
    arm = ss(ax, 0.17, 0.24) * ss(z, 1.2, 1.28)
    leg = 1.0 - ss(z, 0.80, 0.92)
    torso = max(0.0, 1.0 - arm - leg)
    upper_arm = arm * (1.0 - ss(ax, 0.40, 0.48))
    thigh = leg * ss(z, 0.45, 0.55)
    chest = torso * ss(z, 1.12, 1.25)
    belly = torso * ss(z, 0.92, 1.0) * (1.0 - ss(z, 1.15, 1.25)) * (1.0 - ss(y, -0.02, 0.06))
    shoulders = torso * ss(z, 1.28, 1.36) * ss(ax, 0.08, 0.16)
    return dict(arm=arm, leg=leg, torso=torso, upper_arm=upper_arm, thigh=thigh,
                chest=chest, belly=belly, shoulders=shoulders)


SHAPES = {
    # metres of normal offset per region
    "BodyHeavy": lambda r: 0.010 * r["torso"] + 0.022 * r["belly"] + 0.008 * r["arm"] + 0.010 * r["leg"],
    "BodyMuscular": lambda r: 0.012 * r["chest"] + 0.012 * r["shoulders"] + 0.012 * r["upper_arm"]
                              + 0.004 * r["arm"] + 0.010 * r["thigh"] - 0.004 * r["belly"],
    "BodySlim": lambda r: -0.008 * r["torso"] - 0.010 * r["belly"] - 0.005 * r["arm"] - 0.006 * r["leg"],
}

if me.shape_keys is None:
    mesh.shape_key_add(name="Basis", from_mix=False)
for name in SHAPES:
    if name in me.shape_keys.key_blocks:
        mesh.shape_key_remove(me.shape_keys.key_blocks[name])

def radial(co, a, b):
    """Unit vector from the segment a-b to co, perpendicular to the segment."""
    ab = b - a
    t = max(0.0, min(1.0, (co - a).dot(ab) / ab.length_squared))
    d = co - (a + ab * t)
    return d.normalized() if d.length > 1e-5 else Vector((0, 0, 0))


# Body axes in the T-pose (same joints as build_rig.py)
SPINE = (Vector((0, 0.03, 0.8)), Vector((0, 0.03, 1.45)))
ARMS = {1: (Vector((0.175, 0.025, 1.36)), Vector((0.66, 0.024, 1.363))),
        -1: (Vector((-0.175, 0.025, 1.36)), Vector((-0.66, 0.024, 1.363)))}
LEGS = {1: (Vector((0.103, -0.005, 0.881)), Vector((0.18, 0.05, 0.085))),
        -1: (Vector((-0.103, -0.005, 0.881)), Vector((-0.18, 0.05, 0.085)))}


def direction(co, r):
    """Offset direction from the body axes, not surface normals.

    This mesh has layered clothing with inconsistent normals (shirt modelled under the
    protector); pushing along normals makes layers cross. A spatially smooth direction
    moves overlapping layers together, so they keep their spacing.
    """
    side = 1 if co.x >= 0 else -1
    torso_dir = radial(co, *SPINE)
    torso_dir.z = 0.0
    torso_dir = torso_dir.normalized() if torso_dir.length > 1e-5 else torso_dir
    d = torso_dir * r["torso"] + radial(co, *ARMS[side]) * r["arm"] + radial(co, *LEGS[side]) * r["leg"]
    return d.normalized() if d.length > 1e-5 else d


world = [mw @ v.co for v in me.vertices]
regions = [region(co) for co in world]
dirs = [direction(co, r) for co, r in zip(world, regions)]
masks = [body_mask(co) for co in world]
inv = mw.inverted()
for name, fn in SHAPES.items():
    key = mesh.shape_key_add(name=name, from_mix=False)
    coords = []
    peak = 0.0
    for co, r, dvec, m in zip(world, regions, dirs, masks):
        d = fn(r) * m
        peak = max(peak, abs(d))
        coords.extend(inv @ (co + dvec * d))
    key.data.foreach_set("co", coords)
    log(name, "peak offset m", round(peak, 4))
log.close()
