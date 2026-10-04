"""Hand poses and facial expressions for the fighters, keyed by hand (not mocap).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/create_pose_library.py,quit"

Hands (/Game/Characters/Fighters/Animation/Hands, skeleton metahuman_base_skel):
    AS_Hand_<Guard|Punch|Relaxed|Open>_<Both|L|R>
    One-second held poses, additive in local space on the reference pose. They only rotate the 38 finger joints
    (metacarpals, three joints per finger, thumb), so they layer over any body animation and keep each body type's
    own finger lengths. Angles are absolute bends from a straight finger, measured against the reference pose, so
    the result does not depend on how curled the reference fingers are. MetaHuman's body post-process drives the
    finger corrective bones from these joints.

Face (/Game/Characters/Fighters/Animation/Face, skeleton Face_Archetype_Skeleton):
    AS_Face_<Neutral|Focus|Kiai|Wince|Celebrate>  one-second held expressions
    AS_Face_Blink                                  0.25 s blink
    Curves only (ctrl_expressions_*): the MetaHuman face solver (RigLogic, run by the face post-process AnimBP)
    turns them into eyelid, brow, cheek, mouth and jaw joint motion plus wrinkle maps, exactly as it does for the
    face control board. Strengths are modelled on MetaHuman's own facial poses (Facial_Poses/*_gpf_*).

Log: Saved/Logs/create_pose_library.txt. Check renders: Tools/Unreal/capture_pose_library.py.
"""
import math
import traceback

import unreal

EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/create_pose_library.txt"
BODY_SKEL = "/MetaHumanCharacter/Female/Medium/NormalWeight/Body/metahuman_base_skel"
FACE_SKEL = "/MetaHumanCharacter/Face/Face_Archetype_Skeleton"
HANDS = "/Game/Characters/Fighters/Animation/Hands"
FACE = "/Game/Characters/Fighters/Animation/Face"
FPS, SECONDS = 30, 1.0
FINGERS = ["index", "middle", "ring", "pinky"]

# Hand poses. bend: (knuckle, middle joint, end joint) in degrees from straight, per finger. cup: extra metacarpal
# flex toward the palm (ring, pinky). thumb: (base, middle, end) in degrees toward the palm target. spread: degrees
# away from the middle finger. A sparring guard is a loose fist; a punch closes fully with the thumb locked over
# the index and middle fingers.
HAND_POSES = {
    "Guard":   dict(bend={"index": (72, 88, 50), "middle": (78, 92, 52), "ring": (82, 92, 52), "pinky": (86, 88, 50)},
                    cup=(4, 9), thumb=(18, 28, 30), thumb_target="middle_02", spread={}),
    "Punch":   dict(bend={"index": (88, 102, 62), "middle": (90, 104, 62), "ring": (90, 102, 62), "pinky": (92, 98, 60)},
                    cup=(7, 14), thumb=(24, 36, 34), thumb_target="middle_02", spread={}),
    "Relaxed": dict(bend={"index": (10, 20, 10), "middle": (14, 26, 14), "ring": (18, 30, 16), "pinky": (22, 34, 18)},
                    cup=(2, 4), thumb=(4, 8, 10), thumb_target="index_01", spread={}),
    "Open":    dict(bend={"index": (2, 4, 2), "middle": (2, 4, 2), "ring": (3, 5, 3), "pinky": (4, 6, 3)},
                    cup=(0, 0), thumb=(-4, -2, 0), thumb_target="index_01", spread={"index": 2, "ring": 3, "pinky": 6}),
}

# Facial expressions: ctrl_expressions_<name> = value; names ending in "*" get both L and R.
FACE_POSES = {
    "Neutral": {},
    "Focus": {    # locked-in sparring look: lowered brows, narrowed eyes, lips pressed, jaw set
        "browdown*": 0.35, "browlateral*": 0.30, "eyesquintinner*": 0.35, "eyelowerlidup*": 0.30,
        "eyecheekraise*": 0.10, "eyeblink*": 0.08, "mouthlipspress*": 0.30, "mouthpressu*": 0.15,
        "mouthpressd*": 0.15, "mouthcornerdepress*": 0.10, "jawclench*": 0.35, "nosenostrildilate*": 0.15,
    },
    "Kiai": {     # the shout on a scoring technique
        "jawopen": 0.62, "browdown*": 0.60, "browlateral*": 0.55, "eyesquintinner*": 0.70,
        "eyefacescrunch*": 0.30, "eyecheekraise*": 0.40, "nosewrinkle*": 0.45, "nosewrinkleupper*": 0.45,
        "nosenostrildilate*": 0.60, "mouthupperlipraise*": 0.60, "mouthlowerlipdepress*": 0.50,
        "mouthstretch*": 0.55, "mouthcornerpull*": 0.20, "mouthcornerwide*": 0.35, "neckstretch*": 0.60,
        "neckmastoidcontract*": 0.30, "tonguedown": 0.40,
    },
    "Wince": {    # taking a hit: eyes squeezed, teeth clenched, slightly lopsided
        "eyeblinkl": 0.70, "eyeblinkr": 0.60, "eyesquintinner*": 0.90, "eyefacescrunch*": 0.70,
        "eyecheekraise*": 0.70, "eyelidpress*": 0.30, "browdown*": 0.70, "browlateral*": 0.60,
        "nosewrinkle*": 0.65, "nosewrinkleupper*": 0.40, "mouthupperlipraisel": 0.50, "mouthupperlipraiser": 0.35,
        "mouthlowerlipdepressl": 0.45, "mouthlowerlipdepressr": 0.30, "mouthstretchl": 0.60, "mouthstretchr": 0.40,
        "mouthcornerpulll": 0.25, "mouthcornerpullr": 0.15, "jawclench*": 0.70, "jawopen": 0.04,
        "neckstretch*": 0.55,
    },
    "Celebrate": {  # big open smile after a win
        "eyesquintinner*": 0.80, "eyecheekraise*": 0.70, "eyefacescrunch*": 0.15, "browraisein*": 0.40,
        "browraiseouter*": 0.35, "mouthcornerpull*": 1.00, "mouthdimple*": 0.50, "mouthupperlipraise*": 0.45,
        "mouthlowerlipdepress*": 0.50, "mouthstretch*": 0.15, "mouthcornerwide*": 0.30, "jawopen": 0.45,
        "nosewrinkle*": 0.20, "nosenostrildilate*": 0.30,
    },
}
BLINK = [(0.0, 0.0), (0.07, 1.0), (0.10, 1.0), (0.25, 0.0)]

out = open(LOG, "w")


def log(*a):
    out.write(" ".join(str(x) for x in a) + "\n")
    out.flush()


# --- quaternion helpers (x, y, z, w); qmul(a, b) applies b first, like Unreal's FQuat a * b --------------------
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(a):
    return (-a[0], -a[1], -a[2], a[3])


def qrot(q, v):
    x, y, z, w = q
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + (y * tz - z * ty), v[1] + w * ty + (z * tx - x * tz), v[2] + w * tz + (x * ty - y * tx))


def qaxis(axis, deg):
    s = math.sin(math.radians(deg) / 2)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(math.radians(deg) / 2))


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    n = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def perp(v, d):
    return norm(sub(v, mul(d, dot(v, d))))


# --- reference pose ----------------------------------------------------------------------------------------
class Ref:
    def __init__(self, skel):
        pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
        self.local, self.comp = {}, {}
        for nm in unreal.AnimPoseExtensions.get_bone_names(pose):
            n = str(nm)
            lt = unreal.AnimPoseExtensions.get_bone_pose(pose, nm, unreal.AnimPoseSpaces.LOCAL)
            ct = unreal.AnimPoseExtensions.get_bone_pose(pose, nm, unreal.AnimPoseSpaces.WORLD)
            self.local[n] = ((lt.rotation.x, lt.rotation.y, lt.rotation.z, lt.rotation.w),
                             (lt.translation.x, lt.translation.y, lt.translation.z),
                             (lt.scale3d.x, lt.scale3d.y, lt.scale3d.z))
            self.comp[n] = ((ct.rotation.x, ct.rotation.y, ct.rotation.z, ct.rotation.w),
                            (ct.translation.x, ct.translation.y, ct.translation.z))

    def P(self, b):
        return self.comp[b][1]

    def X(self, b, sign):
        """Bone direction: finger bones point down their local X axis (negated on the mirrored side)."""
        return norm(qrot(self.comp[b][0], (sign, 0.0, 0.0)))


def hand_pose(ref, side, spec):
    """Local rotations {bone: quat} for one hand."""
    s = "_" + side
    sign = 1.0 if ref.local["index_02" + s][1][0] >= 0 else -1.0
    X = lambda b: ref.X(b + s, sign)
    P = lambda b: ref.P(b + s)
    across = sub(P("pinky_01"), P("index_01"))
    n = norm(cross(across, X("middle_01")))
    bend = (0.0, 0.0, 0.0)
    for f in FINGERS:
        for a, b in (("01", "02"), ("02", "03")):
            da, db = X(f"{f}_{a}"), X(f"{f}_{b}")
            bend = add(bend, sub(db, mul(da, dot(db, da))))
    if dot(n, bend) < 0:
        n = mul(n, -1.0)
    log(f"  {side}: palm normal {tuple(round(c, 3) for c in n)}, reference curl {math.sqrt(dot(bend, bend)):.3f}")

    rots = {}

    def apply(bone, axis_comp, deg):
        full = bone + s
        if abs(deg) < 1e-4:
            return
        axis_local = norm(qrot(qinv(ref.comp[full][0]), axis_comp))
        cur = rots.get(full, ref.local[full][0])
        rots[full] = qmul(cur, qaxis(axis_local, deg))

    ring_cup, pinky_cup = spec["cup"]
    for f in FINGERS:
        chain = [f"{f}_metacarpal", f"{f}_01", f"{f}_02", f"{f}_03"]
        cup = {"ring": ring_cup, "pinky": pinky_cup}.get(f, 0.0)
        mc = chain[0]
        apply(mc, norm(cross(X(mc), n)), cup)
        sp = spec["spread"].get(f, 0.0)
        if sp:
            d = X(chain[1])
            away = perp(sub(P(chain[1]), P("middle_01")), d)
            apply(chain[1], norm(cross(d, away)), sp)
        for j in (1, 2, 3):
            dp, d = X(chain[j - 1]), X(chain[j])
            ang = math.degrees(math.acos(max(-1.0, min(1.0, dot(dp, d)))))
            phi = ang if dot(n, sub(d, dp)) >= 0 else -ang
            target = spec["bend"][f][j - 1]
            apply(chain[j], norm(cross(d, n)), target - phi)
    tgt = P(spec["thumb_target"])
    for j, b in enumerate(["thumb_01", "thumb_02", "thumb_03"]):
        d = X(b)
        toward = perp(sub(tgt, P(b)), d)
        apply(b, norm(cross(d, toward)), spec["thumb"][j])
    return rots, n


def fingertip_report(ref, side, rots, n):
    """Distance of each fingertip from the palm plane after posing (forward kinematics from the hand)."""
    s = "_" + side
    sign = 1.0 if ref.local["index_02" + s][1][0] >= 0 else -1.0
    hand = "hand" + s
    comp = {hand: ref.comp[hand]}
    palm_c = ref.P("middle_metacarpal" + s)
    res = []
    for f in FINGERS + ["thumb"]:
        chain = ["thumb_01", "thumb_02", "thumb_03"] if f == "thumb" else [f"{f}_metacarpal", f"{f}_01", f"{f}_02", f"{f}_03"]
        parent = hand
        for b in chain:
            full = b + s
            pq, pp = comp[parent]
            lq = rots.get(full, ref.local[full][0])
            comp[full] = (qmul(pq, lq), add(pp, qrot(pq, ref.local[full][1])))
            parent = full
        last = chain[-1] + s
        seg = math.sqrt(dot(ref.local[last][1], ref.local[last][1])) * 0.85
        tip = add(comp[last][1], qrot(comp[last][0], (sign * seg, 0.0, 0.0)))
        res.append(f"{f}={dot(sub(tip, palm_c), n):+.1f}")
    return " ".join(res)


# --- asset helpers -----------------------------------------------------------------------------------------
def new_anim(folder, name, skel, seconds):
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    f = unreal.AnimSequenceFactory()
    f.set_editor_property("target_skeleton", skel)
    anim = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.AnimSequence, f)
    c = anim.controller
    c.open_bracket(unreal.Text("Open Stance pose library"))
    c.set_frame_rate(unreal.FrameRate(FPS, 1))
    c.set_number_of_frames(unreal.FrameNumber(max(1, int(round(seconds * FPS)))))
    return anim, c, path


def build_hands(skel):
    ref = Ref(skel)
    frames = int(round(SECONDS * FPS))
    for pose, spec in HAND_POSES.items():
        log(f"hand pose {pose}")
        per_side = {}
        for side in ("l", "r"):
            rots, n = hand_pose(ref, side, spec)
            per_side[side] = rots
            log(f"    tips from palm (cm, + = palm side) {side}: {fingertip_report(ref, side, rots, n)}")
        for variant, sides in (("Both", ("l", "r")), ("L", ("l",)), ("R", ("r",))):
            anim, c, path = new_anim(HANDS, f"AS_Hand_{pose}_{variant}", skel, SECONDS)
            for side in sides:
                for f in FINGERS + ["thumb"]:
                    chain = ["thumb_01", "thumb_02", "thumb_03"] if f == "thumb" else [f"{f}_metacarpal", f"{f}_01", f"{f}_02", f"{f}_03"]
                    for b in chain:
                        full = f"{b}_{side}"
                        q = per_side[side].get(full, ref.local[full][0])
                        t, sc = ref.local[full][1], ref.local[full][2]
                        c.add_bone_track(full)
                        c.set_bone_track_keys(full, [unreal.Vector(*t)] * (frames + 1), [unreal.Quat(*q)] * (frames + 1),
                                              [unreal.Vector(*sc)] * (frames + 1))
            c.close_bracket()
            AL.set_additive_animation_type(anim, unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
            AL.set_additive_base_pose_type(anim, unreal.AdditiveBasePoseType.ABPT_REF_POSE)
            EAL.save_asset(path, only_if_is_dirty=False)
            log(f"    saved {path} ({len(AL.get_animation_track_names(anim))} tracks)")


def expand(spec):
    vals = {}
    for k, v in spec.items():
        for name in ([k[:-1] + "l", k[:-1] + "r"] if k.endswith("*") else [k]):
            vals["ctrl_expressions_" + name] = v
    return vals


def build_face(skel):
    known = set()
    rom = EAL.load_asset("/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/FaceROM/mhc_mh001_fmn_rom_face")
    if rom:
        known = {str(x).lower() for x in AL.get_animation_curve_names(rom, unreal.RawCurveTrackTypes.RCT_FLOAT)}
    clips = {k: ([(0.0, None), (SECONDS, None)], expand(v)) for k, v in FACE_POSES.items()}
    for name, (keys, vals) in clips.items():
        unknown = [c for c in vals if known and c not in known]
        if unknown:
            log(f"  WARNING {name}: curves not on the face rig: {unknown}")
        anim, c, path = new_anim(FACE, f"AS_Face_{name}", skel, SECONDS)
        c.close_bracket()
        for curve, v in vals.items():
            AL.add_curve(anim, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
            AL.add_float_curve_keys(anim, curve, [0.0, SECONDS], [v, v])
        EAL.save_asset(path, only_if_is_dirty=False)
        log(f"face {name}: {len(vals)} curves -> {path}")
    anim, c, path = new_anim(FACE, "AS_Face_Blink", skel, BLINK[-1][0])
    c.close_bracket()
    for curve in ("ctrl_expressions_eyeblinkl", "ctrl_expressions_eyeblinkr"):
        AL.add_curve(anim, curve, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
        AL.add_float_curve_keys(anim, curve, [t for t, _ in BLINK], [v for _, v in BLINK])
    EAL.save_asset(path, only_if_is_dirty=False)
    log(f"face Blink: {path} length {anim.get_play_length():.2f}s")


try:
    body = EAL.load_asset(BODY_SKEL)
    face = EAL.load_asset(FACE_SKEL)
    build_hands(body)
    build_face(face)
    log("DONE")
except Exception:
    log("ERROR " + traceback.format_exc())
out.close()
