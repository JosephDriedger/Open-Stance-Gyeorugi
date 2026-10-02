"""Prop meshes for the Career venues (GDD 6.2): club dojang, school gym, provincial hall, national arena,
continental arena and world-final stage.

    run("build_venue_meshes")

Same conventions and export path as build_environment_meshes.py (see env_builder.py): metres, origin at the
bottom centre (hanging fixtures: at the mounting point, geometry below), front faces -Y. Material slot names
(MI_*) are matched to material instances by Tools/Unreal/build_venues.py.

Crowds are low-poly stand-in spectators baked into seat blocks so a full bowl stays a few hundred actors.
Each figure takes one of several shirt, trouser, skin and hair slots (natural skin and hair colours only,
Docs/Character_Customization.md), so Unreal varies a crowd by material, not by mesh.
"""
import importlib
import math
import random

import bpy
from mathutils import Matrix, Vector
import rig_config as cfg
import env_builder

importlib.reload(env_builder)
from env_builder import Builder

log = cfg.open_log("build_venue_meshes")
Builder.log = log
previous_scene = env_builder.environment_scene()

SHIRTS = [f"MI_CrowdShirt{i}" for i in range(8)]
PANTS = [f"MI_CrowdPants{i}" for i in range(3)]
SKINS = [f"MI_CrowdSkin{i}" for i in range(5)]
HAIRS = [f"MI_CrowdHair{i}" for i in range(4)]
BELTS = ["MI_BeltYellow", "MI_BeltGreen", "MI_BeltBlue", "MI_BeltRed", "MI_BeltBlack", "MI_BeltBlack"]


# ---------------------------------------------------------------- people
class Figure:
    """Draws one person into a Builder through a local frame (x right, -y forward, z up). Body parts are
    smooth-shaded capsules and tapered ellipsoids, so silhouettes read as people rather than blocks."""

    def __init__(self, b, origin, yaw=0.0):
        self.b = b
        self.T = Matrix.Translation(origin) @ Matrix.Rotation(yaw, 4, 'Z')
        self.R = Matrix.Rotation(yaw, 4, 'Z')

    def p(self, v):
        return self.T @ Vector(v)

    @staticmethod
    def _smooth(faces):
        for f in faces:
            f.smooth = True

    def limb(self, a, c, r0, mat, r1=None):
        """Tapered limb from a (radius r0) to c (radius r1); joints are rounded off by joint()."""
        r1 = r0 if r1 is None else r1
        a, c = self.p(a), self.p(c)
        d = c - a
        rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        self._smooth(self.b.cyl(r0, d.length, a, mat, seg=6, r2=r1, rot=rot))

    def joint(self, r, loc, mat, scale=(1, 1, 1)):
        self._smooth(self.b.sphere(r, self.p(loc), mat, scale=scale, seg=6))

    def trunk(self, base, up, length, r_bottom, r_top, depth, mat):
        """Elliptical tapered torso from `base` along unit vector `up` (local frame)."""
        a = self.p(base)
        d = (self.R @ Vector(up).to_4d()).to_3d().normalized()
        rot = self.R @ Vector((0, 0, 1)).rotation_difference(Vector(up).normalized()).to_matrix().to_4x4() \
            @ Matrix.Diagonal((1.0, depth, 1.0, 1.0))
        self._smooth(self.b.cyl(r_bottom, length, a, mat, seg=8, r2=r_top, rot=rot))
        top = a + d * length
        self._smooth(self.b.sphere(r_top, top, mat, scale=(1.0, depth, 0.45), seg=8))
        self._smooth(self.b.sphere(r_bottom, a, mat, scale=(1.0, depth, 0.5), seg=8))

    def ball(self, r, loc, mat, scale=(1, 1, 1), seg=8):
        self._smooth(self.b.sphere(r, self.p(loc), mat, scale=scale, seg=seg))

    def box(self, size, loc, mat, rot=None):
        self.b.box(size, self.p(loc), mat, rot=self.R @ (rot or Matrix.Identity(4)))


def outfit(rng, kind):
    skin, hair = rng.choice(SKINS), rng.choice(HAIRS)
    style = rng.choices(["short", "long", "bald", "cap"], [5, 3, 1, 1])[0]
    if kind == "dobok":
        return dict(top="MI_DobokWhite", legs="MI_DobokWhite", skin=skin, hair=hair, belt=rng.choice(BELTS),
                    long_sleeves=True, style="short" if style == "cap" else style, shoes=None, bulk=0.0)
    if kind == "coach":
        return dict(top=rng.choice(["MI_CrowdShirt0", "MI_CrowdShirt1", "MI_CrowdShirt6"]), legs="MI_CrowdPants0",
                    skin=skin, hair=hair, belt=None, long_sleeves=True, style=style, shoes="MI_BlackFabric", bulk=0.01)
    return dict(top=rng.choice(SHIRTS), legs=rng.choice(PANTS), skin=skin, hair=hair, belt=None,
                long_sleeves=rng.random() < 0.45, style=style, shoes=rng.choice(["MI_BlackFabric", "MI_TowelWhite"]),
                bulk=rng.uniform(-0.01, 0.03))


def head(f, o, neck, up, rng, k, helmet=None):
    """Neck, skull and hair. neck = base of the neck, up = head axis (unit, local frame)."""
    up = Vector(up).normalized()
    n0 = Vector(neck)
    f.limb(tuple(n0 - up * 0.03), tuple(n0 + up * 0.12 * k), 0.05 * k, o["skin"], 0.045 * k)
    hc = n0 + up * 0.19 * k + Vector((0, -0.015, 0))
    f.ball(0.098 * k, tuple(hc), o["skin"], scale=(0.8, 0.95, 1.12))
    f.joint(0.042 * k, tuple(hc + Vector((0, -0.03, -0.065)) * k), o["skin"], scale=(1.4, 1.0, 0.8))   # jaw
    if helmet:
        f.ball(0.118 * k, tuple(hc + Vector((0, 0.01, 0.025))), helmet, scale=(0.92, 1.05, 1.0))
        return
    style = o["style"]
    if style == "bald":
        return
    if style == "cap":
        f.ball(0.104 * k, tuple(hc + Vector((0, 0.005, 0.045 * k))), o["top"], scale=(0.85, 1.0, 0.7))
        f.box((0.15 * k, 0.1 * k, 0.015), tuple(hc + Vector((0, -0.11 * k, 0.06 * k))), o["top"])
        return
    f.ball(0.103 * k, tuple(hc + Vector((0, 0.018, 0.03 * k))), o["hair"], scale=(0.85, 1.0, 0.92))
    if style == "long":
        f.trunk(tuple(hc + Vector((0, 0.05, -0.02))), (0, 0.15, -1), 0.2 * k, 0.07 * k, 0.085 * k, 0.6, o["hair"])


def arms(f, o, shoulders, elbows, hands, k):
    for s, e, h in zip(shoulders, elbows, hands):
        f.joint(0.065 * k, s, o["top"])
        f.limb(s, e, 0.05 * k, o["top"], 0.042 * k)
        f.joint(0.042 * k, e, o["top"] if o["long_sleeves"] else o["skin"])
        f.limb(e, h, 0.04 * k, o["top"] if o["long_sleeves"] else o["skin"], 0.032 * k)
        f.joint(0.042 * k, h, o["skin"], scale=(0.8, 1.1, 1.25))


def shoe(f, o, ankle, k, barefoot_mat=None):
    mat = barefoot_mat or o["shoes"]
    f.joint(0.055 * k, (ankle[0], ankle[1] - 0.06 * k, ankle[2] - 0.035), mat, scale=(0.85, 2.0, 0.6))


def seated(b, origin, rng, kind="crowd", pose=None, yaw=0.0):
    """A seated figure; origin = centre of the seat surface."""
    f = Figure(b, origin, yaw)
    o = outfit(rng, kind)
    k = rng.uniform(0.92, 1.06)
    w = 1.0 + o["bulk"] * 6
    pose = pose or rng.choices(["rest", "rest", "lean", "clap", "cheer", "point"], [5, 2, 2, 1, 1, 1])[0]
    lean = {"rest": rng.uniform(-0.12, 0.06), "lean": rng.uniform(0.35, 0.5), "clap": 0.05, "cheer": -0.08,
            "point": 0.1}[pose]
    spread = rng.uniform(0.0, 0.08)
    for side in (-1, 1):
        x = side * 0.1 * k * w
        knee = (x + side * spread, -0.43 * k, 0.07 + rng.uniform(-0.02, 0.02))
        ankle = (x + side * spread * 0.6, -0.47 * k, -0.36)
        f.limb((x, 0.0, 0.08), knee, 0.08 * k * w, o["legs"], 0.06 * k)
        f.joint(0.06 * k, knee, o["legs"])
        f.limb(knee, ankle, 0.055 * k, o["legs"], 0.04 * k)
        shoe(f, o, ankle, k, barefoot_mat=o["skin"] if kind == "dobok" else None)
    lean_m = Matrix.Rotation(lean, 4, 'X') @ Matrix.Rotation(rng.uniform(-0.1, 0.1), 4, 'Z')
    up = (lean_m @ Vector((0, 0, 1)).to_4d()).to_3d()
    hip = Vector((0, 0.04, 0.1))
    f.trunk(tuple(hip), tuple(up), 0.44 * k, 0.15 * k * w, 0.185 * k * w, 0.62, o["top"])
    if o["belt"]:
        f.trunk(tuple(hip + up * 0.05), tuple(up), 0.045, 0.172 * k, 0.172 * k, 0.68, o["belt"])
    neck = hip + up * 0.5 * k
    head(f, o, tuple(neck), tuple(up + Vector((0, -0.1, 0))), rng, k)
    shoulders = [tuple(neck + (lean_m @ Vector((sd * 0.19 * k * w, 0, -0.07)).to_4d()).to_3d()) for sd in (-1, 1)]
    sz = shoulders[0][2]
    if pose == "cheer":
        elbows = [(sd * 0.3 * k, shoulders[0][1] - 0.04, sz + 0.22) for sd in (-1, 1)]
        hands = [(sd * 0.25 * k, shoulders[0][1] - 0.1, sz + 0.5) for sd in (-1, 1)]
    elif pose == "clap":
        elbows = [(sd * 0.22 * k, -0.08, sz - 0.26) for sd in (-1, 1)]
        hands = [(sd * 0.03, -0.3, sz - 0.12) for sd in (-1, 1)]
    elif pose == "lean":
        elbows = [(sd * 0.15 * k, -0.4 * k, 0.12) for sd in (-1, 1)]
        hands = [(sd * 0.05, -0.5 * k, 0.28) for sd in (-1, 1)]
    elif pose == "point":
        elbows = [(-0.24 * k, shoulders[0][1] - 0.06, sz - 0.3), (0.26 * k, -0.15, sz - 0.05)]
        hands = [(-0.15 * k, -0.3 * k, 0.17), (0.3 * k, -0.42, sz + 0.1)]
    else:
        elbows = [(sd * 0.24 * k, shoulders[0][1] - 0.04, sz - 0.3) for sd in (-1, 1)]
        hands = [(sd * 0.14 * k, -0.3 * k, 0.17) for sd in (-1, 1)]
    arms(f, o, shoulders, elbows, hands, k)


def standing(b, origin, rng, kind="dobok", pose="stand", yaw=0.0, gear=None):
    """A standing figure; origin = floor point between the feet. gear = "Blue"/"Red" adds protector and helmet."""
    f = Figure(b, origin, yaw)
    o = outfit(rng, kind)
    k = rng.uniform(0.95, 1.06)
    hip_z = 0.93 * k
    guard = pose == "guard"
    for side in (-1, 1):
        fy = side * 0.16 if guard else 0.0
        fx = side * (0.17 if guard else 0.11)
        knee = (fx * 0.9, fy * 0.5 - (0.05 if guard else 0.0), hip_z * 0.5)
        ankle = (fx, fy, 0.08)
        f.limb((side * 0.1 * k, 0, hip_z), knee, 0.08 * k, o["legs"], 0.058 * k)
        f.joint(0.058 * k, knee, o["legs"])
        f.limb(knee, ankle, 0.056 * k, o["legs"], 0.042 * k)
        shoe(f, o, ankle, k, barefoot_mat=o["skin"] if kind == "dobok" else None)
    up = Vector((0, -0.08 if guard else 0.0, 1)).normalized()
    hip = Vector((0, 0, hip_z))
    f.trunk(tuple(hip), tuple(up), 0.5 * k, 0.155 * k, 0.19 * k, 0.62, o["top"])
    if o["belt"]:
        f.trunk(tuple(hip + up * 0.05), tuple(up), 0.045, 0.175 * k, 0.175 * k, 0.68, o["belt"])
    if gear:   # hogu (trunk protector) and head guard in the side colour
        f.trunk(tuple(hip + up * 0.1), tuple(up), 0.36 * k, 0.185 * k, 0.2 * k, 0.72, f"MI_Plastic{gear}")
    neck = hip + up * 0.56 * k
    head(f, o, tuple(neck), tuple(up), rng, k, helmet=f"MI_Plastic{gear}" if gear else None)
    sh = [tuple(neck + Vector((sd * 0.19 * k, 0, -0.07))) for sd in (-1, 1)]
    nz = neck.z
    if guard:
        elbows = [(sd * 0.2 * k, -0.16, nz - 0.32) for sd in (-1, 1)]
        hands = [(sd * 0.11 * k, -0.33, nz - 0.08) for sd in (-1, 1)]
    elif pose == "paddle":
        elbows = [(sd * 0.24 * k, -0.2, nz - 0.25) for sd in (-1, 1)]
        hands = [(sd * 0.1 * k, -0.42, nz - 0.12) for sd in (-1, 1)]
        f.box((0.04, 0.03, 0.14), (0.1 * k, -0.45, nz - 0.07), "MI_PlasticRed")
        f.ball(0.12, (0.1 * k, -0.48, nz + 0.12), "MI_BlackVinyl", scale=(0.9, 0.3, 1.4))
    elif pose == "arms_crossed":
        elbows = [(sd * 0.22 * k, -0.1, nz - 0.32) for sd in (-1, 1)]
        hands = [(-sd * 0.12 * k, -0.17, nz - 0.24) for sd in (-1, 1)]
    else:
        elbows = [(sd * 0.24 * k, 0.02, nz - 0.33) for sd in (-1, 1)]
        hands = [(sd * 0.26 * k, -0.03, nz - 0.6) for sd in (-1, 1)]
    arms(f, o, sh, elbows, hands, k)


# ---------------------------------------------------------------- spectator seating
def seat(b, x, y, z, mat):
    b.box((0.44, 0.42, 0.05), (x, y, z + 0.44), mat)
    b.box((0.44, 0.05, 0.42), (x, y + 0.22, z + 0.72), mat, rot=Matrix.Rotation(math.radians(-12), 4, 'X'))
    b.box((0.04, 0.4, 0.44), (x - 0.25, y + 0.02, z + 0.22), "MI_TrussMetal")


SEAT_PITCH, ROW_D, ROW_H = 0.5, 0.85, 0.42
OCCUPANCY = {"Sparse": 0.3, "Half": 0.6, "Full": 0.93}

# Stadium seat block: 10 seats x 6 rows on 0.85 m / 0.42 m steps; row 0 sits at the origin (place it on a
# riser top), rows climb towards +Y. 5 m wide, so blocks tile edge to edge along a stand.
for occ in ("Empty", "Sparse", "Half", "Full"):
    for var in (("A", "B") if occ != "Empty" else ("",)):
        rng = random.Random(f"{occ}{var}")
        b = Builder(f"SM_SeatBlock_{occ}{var}")
        for r in range(6):
            for i in range(10):
                x, y, z = -2.25 + i * SEAT_PITCH, r * ROW_D, r * ROW_H
                seat(b, x, y, z, "MI_SeatDark")
                if occ != "Empty" and rng.random() < OCCUPANCY[occ]:
                    seated(b, (x + rng.uniform(-0.02, 0.02), y + 0.02, z + 0.465), rng)
            b.box((0.04, 0.4, 0.44), (2.5, r * ROW_D + 0.02, r * ROW_H + 0.22), "MI_TrussMetal")
        b.finish()

# Telescopic gym bleacher, 8 m x 8 rows (pulled out), solid steps with wood benches.
BL_W, BL_D, BL_H, BL_ROWS = 8.0, 0.76, 0.3, 8
for occ in ("Sparse", "Half"):
    rng = random.Random(f"bleacher{occ}")
    b = Builder(f"SM_Bleacher_{occ}")
    for r in range(BL_ROWS):
        top = (r + 1) * BL_H
        b.box((BL_W, BL_D, top), (0, r * BL_D, top / 2), "MI_BleacherDeck")
        b.box((BL_W, 0.3, 0.04), (0, r * BL_D + 0.18, top + 0.42), "MI_BleacherWood")
        for x in (-3.6, -1.2, 1.2, 3.6):
            b.box((0.05, 0.05, 0.4), (x, r * BL_D + 0.18, top + 0.2), "MI_TrussMetal")
        for i in range(16):
            x = -3.75 + i * 0.5
            if rng.random() < OCCUPANCY[occ] * 0.85:
                seated(b, (x + rng.uniform(-0.08, 0.08), r * BL_D + 0.16, top + 0.44), rng)
    back = BL_ROWS * BL_D
    b.box((BL_W, 0.05, 1.0), (0, back - 0.4, BL_ROWS * BL_H + 0.5), "MI_TrussMetal")
    for x in (-BL_W / 2, BL_W / 2):
        b.rod((x, -0.1, 1.0), (x, back - 0.4, BL_ROWS * BL_H + 1.0), 0.025, "MI_TrussMetal")
    b.finish()

# Club mates on a bench along the club dojang wall (doboks and coloured belts)
for var, n in (("A", 4), ("B", 5)):
    rng = random.Random(f"club{var}")
    b = Builder(f"SM_BenchClubMates_{var}")
    b.box((3.0, 0.36, 0.05), (0, 0, 0.42), "MI_WoodLight")
    for x in (-1.3, 0, 1.3):
        b.box((0.05, 0.3, 0.4), (x, 0, 0.2), "MI_BlackPlastic")
    xs = sorted(rng.uniform(-1.3, 1.3) for _ in range(n))
    for i in range(1, n):
        xs[i] = max(xs[i], xs[i - 1] + 0.55)
    shift = (xs[0] + xs[-1]) / 2
    for x in xs:
        seated(b, (x - shift, 0.02, 0.445), rng, kind="dobok",
               pose=rng.choice(["rest", "lean", "rest", "clap"]))
    b.finish()

# Warm-up area groups: athletes in gear drilling with a coach
for var in ("A", "B"):
    rng = random.Random(f"warmup{var}")
    b = Builder(f"SM_WarmupGroup_{var}")
    if var == "A":
        standing(b, (-0.6, 0, 0), rng, "dobok", "guard", yaw=math.radians(90), gear="Blue")
        standing(b, (0.6, 0, 0), rng, "dobok", "paddle", yaw=math.radians(-90))
        standing(b, (0.2, 1.4, 0), rng, "coach", "arms_crossed", yaw=math.radians(160))
    else:
        standing(b, (-0.7, 0.1, 0), rng, "dobok", "guard", yaw=math.radians(80), gear="Red")
        standing(b, (0.7, -0.1, 0), rng, "dobok", "guard", yaw=math.radians(-100), gear="Blue")
        standing(b, (-1.5, 1.2, 0), rng, "coach", "stand", yaw=math.radians(200))
        standing(b, (1.8, 1.0, 0), rng, "dobok", "stand", yaw=math.radians(180))
    b.finish()

# ---------------------------------------------------------------- scoreboards and screens
# Portable scoreboard on a rolling stand (club dojang: one; gym: two)
b = Builder("SM_ScoreboardPortable")
for k in range(4):
    a = math.radians(45 + 90 * k)
    b.rod((0, 0, 0.12), (0.45 * math.cos(a), 0.45 * math.sin(a), 0.06), 0.02, "MI_BlackPlastic", seg=6)
    b.sphere(0.04, (0.45 * math.cos(a), 0.45 * math.sin(a), 0.04), "MI_BlackPlastic")
b.box((0.08, 0.08, 1.5), (0, 0.06, 0.8), "MI_TrussMetal")
b.box((1.3, 0.07, 0.6), (0, 0, 1.75), "MI_BlackPlastic")
b.canvas(1.2, 0.48, (0, -0.036, 1.75), "MI_ScreenScoreboard")
b.finish()

# Gym wall scoreboard (basketball, switched off)
b = Builder("SM_ScoreboardGymWall")
b.box((3.2, 0.25, 1.4), (0, 0.125, 0.7), "MI_BlackPlastic")
b.canvas(3.1, 1.24, (0, -0.001, 0.7), "MI_ScreenGym")
b.finish()

# Centre-hung video cube: scoreboards on two faces, event screens on the other two
b = Builder("SM_VideoCube")
b.box((6.2, 6.2, 2.7), (0, 0, 1.6), "MI_BlackPlastic")
b.box((5.6, 5.6, 0.25), (0, 0, 0.125), "MI_BlackPlastic")
for facing in ((0, -1, 0), (0, 1, 0)):
    b.canvas(6.0, 2.4, (facing[0] * 3.101, facing[1] * 3.101, 1.6), "MI_ScreenScoreboard", facing=facing)
for facing in ((1, 0, 0), (-1, 0, 0)):
    b.canvas(4.8, 2.4, (facing[0] * 3.101, facing[1] * 3.101, 1.6), "MI_ScreenEvent", facing=facing)
for facing in ((0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0)):
    b.canvas(5.6, 0.12, (facing[0] * 2.801, facing[1] * 2.801, 0.125), "MI_StageLed", facing=facing)
for x, y in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
    b.rod((x, y, 2.95), (x * 0.3, y * 0.3, 7.0), 0.015, "MI_TrussMetal", seg=4)
b.finish()

# LED ribbon board, 8 m x 1 m (fascia between seating tiers)
b = Builder("SM_LedRibbon")
b.box((8.0, 0.15, 1.1), (0, 0.075, 0.55), "MI_BlackPlastic")
b.canvas(8.0, 1.0, (0, -0.001, 0.55), "MI_Ribbon")
b.finish()

# Event screen (big rectangular video wall, 2:1)
b = Builder("SM_EventScreen")
b.box((8.4, 0.3, 4.4), (0, 0.15, 2.2), "MI_BlackPlastic")
b.canvas(8.0, 4.0, (0, -0.001, 2.2), "MI_ScreenEvent")
b.finish()

# Fabric banner, 3 m x 1 m (3:1) with top and bottom rods; printed face -Y, plain back
b = Builder("SM_Banner3x1")
b.canvas(3.0, 1.0, (0, -0.006, 0.5), "MI_Banner")
b.box((3.0, 0.01, 1.0), (0, 0.0, 0.5), "MI_BlackFabric")
for z in (0.0, 1.0):
    b.rod((-1.55, 0, z), (1.55, 0, z), 0.012, "MI_TrussMetal", seg=6)
b.finish()

# Portrait frame, 0.6 x 0.8 m picture (3:4), centred like SM_FrameLandscape
b = Builder("SM_FramePortrait")
w, h, t = 0.6, 0.8, 0.04
b.box((w + 2 * t, 0.04, t), (0, 0, h / 2 + t / 2), "MI_WoodMid")
b.box((w + 2 * t, 0.04, t), (0, 0, -h / 2 - t / 2), "MI_WoodMid")
b.box((t, 0.04, h), (-w / 2 - t / 2, 0, 0), "MI_WoodMid")
b.box((t, 0.04, h), (w / 2 + t / 2, 0, 0), "MI_WoodMid")
b.box((w, 0.01, h), (0, 0.015, 0), "MI_PotWhite")
b.canvas(w, h, (0, 0.009, 0), "MI_Canvas")
b.finish()

# ---------------------------------------------------------------- gym
# Wall-mounted basketball hoop (origin at the wall, floor level); FIBA rim 3.05 m, board 1.8 x 1.05 m
b = Builder("SM_BasketballHoop")
BY = -1.2
b.box((0.6, 0.06, 1.4), (0, -0.03, 3.6), "MI_TrussMetal")
for z0, z1 in ((3.1, 3.05), (4.2, 3.75)):
    for x in (-0.25, 0.25):
        b.rod((x, -0.05, z0), (x * 1.6, BY + 0.05, z1), 0.03, "MI_TrussMetal", seg=6)
b.box((1.8, 0.03, 1.05), (0, BY, 3.425), "MI_Glass")
for size, loc in (((1.8, 0.035, 0.05), (0, BY, 3.925)), ((1.8, 0.035, 0.05), (0, BY, 2.925)),
                  ((0.05, 0.035, 1.05), (-0.875, BY, 3.425)), ((0.05, 0.035, 1.05), (0.875, BY, 3.425)),
                  ((0.59, 0.035, 0.05), (0, BY - 0.001, 3.5)), ((0.59, 0.035, 0.05), (0, BY - 0.001, 3.08)),
                  ((0.05, 0.035, 0.45), (-0.27, BY - 0.001, 3.29)), ((0.05, 0.035, 0.45), (0.27, BY - 0.001, 3.29))):
    b.box(size, loc, "MI_LineWhite")
rim_c = Vector((0, BY - 0.151 - 0.225, 3.05))
ring = [rim_c + Vector((0.225 * math.cos(math.radians(a)), 0.225 * math.sin(math.radians(a)), 0)) for a in range(0, 360, 30)]
low = [rim_c + Vector((0.14 * math.cos(math.radians(a)), 0.14 * math.sin(math.radians(a)), -0.42)) for a in range(0, 360, 30)]
for i in range(12):
    b.rod(ring[i], ring[(i + 1) % 12], 0.01, "MI_RimOrange", seg=4)
    b.rod(ring[i], low[(i + 1) % 12], 0.004, "MI_LineWhite", seg=3)
    b.rod(ring[i], low[(i - 1) % 12], 0.004, "MI_LineWhite", seg=3)
b.box((0.04, 0.2, 0.03), (0, BY - 0.1, 3.05), "MI_RimOrange")
b.finish()

# High-bay light (hangs below its mounting point)
b = Builder("SM_HighBay")
b.cyl(0.01, 0.5, (0, 0, -0.5), "MI_TrussMetal", seg=6)
b.box((0.16, 0.16, 0.14), (0, 0, -0.57), "MI_TrussMetal")
b.cyl(0.28, 0.32, (0, 0, -0.96), "MI_DuctMetal", seg=20, r2=0.1)
b.cyl(0.27, 0.01, (0, 0, -0.97), "MI_LightLens", seg=20)
b.finish()

# Gym floor: 36 m court decal (MI_GymCourt over T_GymCourt)
b = Builder("SM_FloorDecal36")
b.floor_canvas(36.0, 36.0, (0, 0, 0.0), "MI_GymCourt")
b.finish()

# ---------------------------------------------------------------- multi-mat hall
# Perimeter / dividing board, 3.2 m x 0.8 m printed face (4:1)
b = Builder("SM_AdBoard")
b.box((3.2, 0.06, 0.82), (0, 0.03, 0.51), "MI_BlackPlastic")
b.canvas(3.2, 0.8, (0, -0.001, 0.51), "MI_Ad")
for x in (-1.4, 1.4):
    b.box((0.06, 0.5, 0.06), (x, 0.2, 0.03), "MI_BlackPlastic")
b.finish()

# Court number sign on a post (two-sided)
b = Builder("SM_CourtSign")
b.cyl(0.25, 0.04, (0, 0, 0), "MI_BlackPlastic", seg=16)
b.cyl(0.03, 2.0, (0, 0, 0.04), "MI_TrussMetal", seg=8)
b.box((0.64, 0.04, 0.64), (0, 0, 2.3), "MI_BlackPlastic")
b.canvas(0.6, 0.6, (0, -0.021, 2.3), "MI_CourtNumber")
b.canvas(0.6, 0.6, (0, 0.021, 2.3), "MI_CourtNumber", facing=(0, 1, 0))
b.finish()

# ---------------------------------------------------------------- arenas
# Raised competition platform: 13 m square, 0.6 m high, LED band below the lip; the mat sits on top.
STAGE, STAGE_H = 13.0, 0.6
b = Builder("SM_RaisedStage")
b.box((STAGE + 0.1, STAGE + 0.1, 0.06), (0, 0, STAGE_H - 0.03), "MI_StageTop")
b.box((STAGE - 0.1, STAGE - 0.1, STAGE_H - 0.06), (0, 0, (STAGE_H - 0.06) / 2), "MI_StageSkirt")
for facing in ((0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0)):
    c = Vector(facing) * (STAGE / 2 - 0.049)
    b.canvas(STAGE - 0.1, 0.06, (c.x, c.y, STAGE_H - 0.12), "MI_StageLed", facing=facing)
    c = Vector(facing) * (STAGE / 2 - 0.049)
    b.canvas(STAGE - 0.1, 0.03, (c.x, c.y, 0.04), "MI_StageLed", facing=facing)
b.finish()

# Stage steps: 1.6 m wide, 3 risers up to 0.6 m; back edge meets the stage at +Y
b = Builder("SM_StageSteps")
for i in range(3):
    h = (i + 1) * 0.2
    b.box((1.6, 0.32, h), (0, -0.48 + i * 0.32 + 0.16, h / 2), "MI_StageSkirt")
    b.box((1.6, 0.03, 0.02), (0, -0.48 + i * 0.32 + 0.015, h + 0.005), "MI_LineWhite")
for x in (-0.82, 0.82):
    b.rod((x, -0.48, 0.95), (x, 0.48, 1.55), 0.02, "MI_TrussMetal", seg=6)
    b.rod((x, -0.48, 0.0), (x, -0.48, 0.95), 0.02, "MI_TrussMetal", seg=6)
b.finish()

# Hanging national flag, 1.5 x 1.0 m (uniform 3:2 display), two-sided, on a bar with suspension wires
b = Builder("SM_FlagHanging")
b.canvas(1.5, 1.0, (0, -0.002, 0.5), "MI_Flag", facing=(0, -1, 0))
b.canvas(1.5, 1.0, (0, 0.002, 0.5), "MI_Flag", facing=(0, 1, 0))
b.rod((-0.8, 0, 1.02), (0.8, 0, 1.02), 0.015, "MI_TrussMetal", seg=6)
for x in (-0.75, 0.75):
    b.rod((x, 0, 1.02), (x * 0.2, 0, 2.2), 0.004, "MI_TrussMetal", seg=3)
b.finish()

# Broadcast camera on a tripod (lens faces -Y)
b = Builder("SM_BroadcastCamera")
for k in range(3):
    a = math.radians(90 + 120 * k)
    b.rod((0, 0, 1.15), (0.5 * math.cos(a), 0.5 * math.sin(a), 0), 0.018, "MI_TrussMetal", seg=6)
b.box((0.18, 0.18, 0.12), (0, 0, 1.2), "MI_BlackPlastic")
b.box((0.22, 0.5, 0.28), (0, 0.05, 1.4), "MI_BlackPlastic")
b.rod((0, -0.2, 1.42), (0, -0.62, 1.42), 0.075, "MI_BlackPlastic", seg=12)
b.cyl(0.07, 0.01, (0, -0.625, 1.42), "MI_Glass", seg=12, rot=Matrix.Rotation(math.radians(90), 4, 'X'))
b.box((0.2, 0.08, 0.14), (-0.18, 0.1, 1.55), "MI_BlackPlastic")
b.rod((0.0, 0.25, 1.35), (0.25, 0.75, 1.15), 0.015, "MI_TrussMetal", seg=6)
b.rod((0.0, 0.25, 1.35), (-0.25, 0.75, 1.15), 0.015, "MI_TrussMetal", seg=6)
b.finish()

# Camera jib (crane): column, 4 m arm, counterweight, camera at the front (-Y)
b = Builder("SM_CameraJib")
for k in range(3):
    a = math.radians(90 + 120 * k)
    b.rod((0, 0, 0.6), (0.8 * math.cos(a), 0.8 * math.sin(a), 0), 0.03, "MI_TrussMetal", seg=6)
b.cyl(0.06, 1.2, (0, 0, 0.5), "MI_TrussMetal", seg=10)
b.rod((0, 1.2, 1.5), (0, -3.0, 2.6), 0.05, "MI_TrussMetal", seg=8)
b.box((0.4, 0.4, 0.5), (0, 1.3, 1.25), "MI_BlackPlastic")
b.box((0.2, 0.4, 0.24), (0, -3.0, 2.38), "MI_BlackPlastic")
b.rod((0, -3.2, 2.38), (0, -3.5, 2.38), 0.06, "MI_BlackPlastic", seg=10)
b.finish()


def truss_segment(b, p1, p2, s=0.15, rc=0.024, rl=0.01, mat="MI_TrussMetal"):
    """Square box truss from p1 to p2 (axis-aligned), 30 cm section, zig-zag lacing every 0.5 m."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    ax = max(range(3), key=lambda i: abs(d[i]))
    u, v = [i for i in range(3) if i != ax]
    corners = []
    for cu, cv in ((-s, -s), (s, -s), (s, s), (-s, s)):
        off = Vector((0, 0, 0))
        off[u], off[v] = cu, cv
        corners.append(off)
        b.rod(p1 + off, p2 + off, rc, mat, seg=8)
    steps = max(1, int(d.length / 0.5))
    for i in range(steps):
        a, c = p1 + d * (i / steps), p1 + d * ((i + 1) / steps)
        for k in range(4):
            b.rod(a + corners[k], c + corners[(k + 1) % 4], rl, mat, seg=4)


# Entrance arch for the world-final walk: truss towers, header and a 2:1 screen facing the arena (-Y)
b = Builder("SM_EntranceArch")
for x in (-2.8, 2.8):
    truss_segment(b, (x, 0, 0), (x, 0, 6.0))
    b.box((0.6, 0.6, 0.05), (x, 0, 0.025), "MI_BlackPlastic")
    b.canvas(0.06, 5.6, (x - math.copysign(0.16, x), -0.16, 3.0), "MI_StageLed")
truss_segment(b, (-2.95, 0, 6.0), (2.95, 0, 6.0))
b.box((5.0, 0.2, 2.6), (0, 0.1, 4.4), "MI_BlackPlastic")
b.canvas(4.8, 2.4, (0, -0.001, 4.4), "MI_EntranceScreen")
b.finish()

# Runway: 2 m wide, 10 m long along Y, black carpet with LED edges
b = Builder("SM_Runway")
b.box((2.0, 10.0, 0.1), (0, 0, 0.05), "MI_CarpetBlack")
for x in (-0.97, 0.97):
    b.box((0.04, 10.0, 0.012), (x, 0, 0.106), "MI_StageLed")
b.finish()

# Moving-head fixture (hangs below its mounting point, head aims down)
b = Builder("SM_MovingHead")
b.box((0.36, 0.3, 0.16), (0, 0, -0.08), "MI_BlackPlastic")
b.box((0.04, 0.12, 0.34), (-0.2, 0, -0.3), "MI_BlackPlastic")
b.box((0.04, 0.12, 0.34), (0.2, 0, -0.3), "MI_BlackPlastic")
b.cyl(0.15, 0.36, (0, 0, -0.6), "MI_BlackPlastic", seg=16, r2=0.12)
b.cyl(0.13, 0.01, (0, 0, -0.61), "MI_LightLens", seg=16)
b.finish()

# Victory podium: 1 centre, 2 left, joint 3 right (taekwondo awards two bronzes)
b = Builder("SM_Podium")
for (label, x, w, h) in (("1", 0.0, 1.2, 0.6), ("2", -1.25, 1.2, 0.4), ("3", 1.55, 1.8, 0.22)):
    b.box((w, 1.0, h), (x, 0, h / 2), "MI_PodiumWhite")
    b.canvas(min(h * 0.9, 0.5), min(h * 0.9, 0.5), (x, -0.501, h / 2), f"MI_Podium{label}")
b.finish()

log("DONE", env_builder.OUT_DIR)
log.close()
bpy.context.window.scene = previous_scene
