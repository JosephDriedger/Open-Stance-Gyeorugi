"""Which rig bones can the proposed 41-marker set (Docs/Mocap_Marker_Set.md) drive, and which can't it?

    py Tools/Validation/marker_set_coverage.py

Plug-in Gait style sets solve rigid body segments (head, thorax, pelvis, upper arms, forearms, hands, thighs,
shanks, feet) from marker clusters. This lists every bone of the MetaHuman body skeleton (the production rig) and
of the custom fighter skeleton (Resources/Models/Fighter_Rigged.fbx) under one of:

  solved    a marker segment gives the bone's orientation directly
  derived   follows from solved bones by rule (spine split between pelvis and thorax, twist bones, neck, clavicles,
            IK helpers, corrective bones the engine drives from the main joints)
  free      no marker information at all: fingers, toes, anything else (needs a pose rule or extra markers)

It is a structural audit of rig vs marker set, not a solve: no capture data exists yet.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_gear_poses as c  # noqa: E402

# marker segment -> rig bones it orients (side-suffix aware)
SOLVED = {
    "pelvis (LASI RASI LPSI RPSI)": [r"^pelvis$"],
    "thorax (C7 T10 CLAV STRN RBAK)": [r"^spine_05$", r"^spine_04$"],
    "head (LFHD RFHD LBHD RBHD)": [r"^head$"],
    "upper arm (SHO ELB UPA)": [r"^upperarm_[lr]$"],
    "forearm (ELB WRA WRB FRM)": [r"^lowerarm_[lr]$"],
    "hand (WRA WRB FIN)": [r"^hand_[lr]$"],
    "thigh (ASI KNE THI)": [r"^thigh_[lr]$"],
    "shank (KNE ANK TIB)": [r"^calf_[lr]$"],
    "foot (ANK HEE TOE MT5)": [r"^foot_[lr]$"],
}
DERIVED = [
    (r"^root$", "root: pelvis footprint"),
    (r"^spine_0[123]$", "spine: split between pelvis and thorax"),
    (r"^neck_0[12]$", "neck: between thorax and head"),
    (r"^clavicle_[lr]$", "clavicle: follows thorax, shoulder marker sets the shoulder joint"),
    (r"(twist|Twist)", "twist bone: share of the segment twist"),
    (r"^ball_[lr]$", "ball: from foot segment (second metatarsal marker LTOE sits at the ball), no flex"),
    (r"^ik_", "IK helper: derived from FK"),
    (r"(Cor|correctiveRoot|_fwd|_bck|_in|_out|_lwr|_up|_kneeBack|_knee|latissimus|bicep|tricep|elbow|kneeFwd|_dn|clavicle_scap|clavicle_pec)",
     "corrective: engine drives it from the main joints"),
    (r"^(thumb|index|middle|ring|pinky)_.*(bulge|half|dip|pip|mcp|palm|slide|twist)", "finger corrective: driven from the finger joints"),
    (r"^(MH_Fighter|Armature)", "mesh/scene node (not a bone)"),
]
FREE = [
    (r"^(thumb_0[123]|(index|middle|ring|pinky)_(metacarpal|0[123]))_[lr]$", "finger joints (no finger markers)"),
    (r"toe_0[12]_[lr]$", "toe joints (markers stop at the metatarsal heads)"),
]


def classify(name):
    for seg, pats in SOLVED.items():
        if any(re.search(p, name) for p in pats):
            return "solved", seg
    for pat, why in DERIVED:
        if re.search(pat, name):
            return "derived", why
    for pat, why in FREE:
        if re.search(pat, name):
            return "free", why
    return "free", "other"


def audit(label, names):
    groups = {}
    for n in names:
        k, why = classify(n)
        groups.setdefault((k, why), []).append(n)
    total = len(names)
    cnt = {k: sum(len(v) for (kk, _), v in groups.items() if kk == k) for k in ("solved", "derived", "free")}
    print(f"\n== {label}: {total} bones: {cnt['solved']} solved, {cnt['derived']} derived, {cnt['free']} free")
    for (k, why), v in sorted(groups.items(), key=lambda t: (t[0][0], -len(t[1]))):
        print(f"  {k:8s} {len(v):4d}  {why}" + (f"   e.g. {', '.join(v[:3])}" if k == "free" else ""))
    return groups


body = c.load_fbx(os.path.join(c.MODELS, "MetaHuman", "MH_FighterBase_Body.fbx"))
g = audit("MetaHuman body skeleton (production rig)", list(body["G"].keys()))
fighter = c.load_fbx(os.path.join(c.MODELS, "Fighter_Rigged.fbx"))
audit("Custom fighter skeleton (MotionBuilder test rig)", list(fighter["G"].keys()))
print("\nfree bones on the MetaHuman skeleton that matter for the shot list:")
for (k, why), v in g.items():
    if k == "free":
        print(f"  {why}: {len(v)}")
