"""Import a baked mocap FBX (Tools/MotionBuilder/retarget_c3d.py output) as an animation on the production fighter skeleton.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/import_mocap_clip.py <baked.fbx> <AssetName> quit"

Creates /Game/Animation/Mocap/<AssetName> (re-imported in place if it exists; check it out in Perforce first then).
Only the animation is imported; the meshes in the FBX are ignored. Afterwards the clip is sampled and the pelvis, feet and
hands checked for motion, NaNs and floor height. Log: Saved/Logs/import_mocap_clip.txt.
"""
import math
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
DEST = "/Game/Animation/Mocap"
BODY = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
EAL = unreal.EditorAssetLibrary
LOG = open(f"{REPO}/Saved/Logs/import_mocap_clip.txt", "w", encoding="utf-8")
args = [a for a in sys.argv[1:] if a not in ("quit", "verify")]
VERIFY_ONLY = "verify" in sys.argv[1:]   # skip the import, only check the existing asset


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


def import_clip(fbx, name, skeleton):
    ui = unreal.FbxImportUI()
    ui.import_mesh = False
    ui.import_animations = True
    ui.import_as_skeletal = True
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    ui.automated_import_should_detect_type = False
    ui.import_materials = False
    ui.import_textures = False
    ui.skeleton = skeleton
    ad = ui.anim_sequence_import_data
    ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    ad.set_editor_property("remove_redundant_keys", False)
    ad.set_editor_property("import_bone_tracks", True)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = fbx, DEST, name
    task.automated, task.replace_existing, task.save, task.options = True, True, True, ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    log("imported paths", list(task.get_editor_property("imported_object_paths")))


def component_space(anim, bone, t, parents):
    """Bone transform in component space by chaining local poses up to the root."""
    xf = unreal.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
    b = parents.get(bone)
    while b:
        xf = xf.multiply(unreal.AnimationLibrary.get_bone_pose_for_time(anim, b, t, False))
        b = parents.get(b)
    return xf.translation


try:
    fbx, name = args[0], args[1]
    assert os.path.exists(fbx), f"missing {fbx}"
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    skeleton = EAL.load_asset(BODY).get_editor_property("skeleton")
    log("skeleton", skeleton.get_path_name())
    if not VERIFY_ONLY:
        import_clip(fbx, name, skeleton)
    anim = EAL.load_asset(f"{DEST}/{name}")
    assert isinstance(anim, unreal.AnimSequence), f"import failed: {anim}"
    length = anim.get_play_length()
    frames = unreal.AnimationLibrary.get_num_frames(anim)
    log("sequence", anim.get_path_name(), f"length {length:.3f}s frames {frames} ({frames / length:.1f} fps)")
    log("skeleton match", anim.get_editor_property("skeleton") == skeleton)
    tracks = unreal.AnimationLibrary.get_animation_track_names(anim)
    log("bone tracks", len(tracks))

    # MetaHuman body hierarchy for the bones checked below
    names = [str(n) for n in tracks]
    parents = {}
    chain = {"pelvis": "root", "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02",
             "spine_04": "spine_03", "spine_05": "spine_04", "clavicle_l": "spine_05", "upperarm_l": "clavicle_l",
             "lowerarm_l": "upperarm_l", "hand_l": "lowerarm_l", "clavicle_r": "spine_05", "upperarm_r": "clavicle_r",
             "lowerarm_r": "upperarm_r", "hand_r": "lowerarm_r", "thigh_l": "pelvis", "calf_l": "thigh_l",
             "foot_l": "calf_l", "thigh_r": "pelvis", "calf_r": "thigh_r", "foot_r": "calf_r", "neck_01": "spine_05",
             "neck_02": "neck_01", "head": "neck_02"}
    for b, p in chain.items():
        parents[b] = p if p != "root" else "root"
    parents["root"] = None
    missing = [b for b in chain if b not in names]
    log("missing tracks", missing)

    samples = 24
    pts = {b: [] for b in ("pelvis", "foot_l", "foot_r", "hand_l", "hand_r", "head")}
    for i in range(samples):
        t = length * (i + 0.5) / samples
        for b in pts:
            pts[b].append(component_space(anim, b, t, parents))
    bad = [b for b, v in pts.items() for p in v if any(math.isnan(c) for c in (p.x, p.y, p.z))]
    log("nan", bad)
    for b, v in pts.items():
        xs = [p.x for p in v]; ys = [p.y for p in v]; zs = [p.z for p in v]
        log(f"{b:7s} z min {min(zs):7.1f} max {max(zs):7.1f} | x range {max(xs)-min(xs):6.1f} y range {max(ys)-min(ys):6.1f}"
            f" | first ({v[0].x:.1f}, {v[0].y:.1f}, {v[0].z:.1f})")
    hand_spread = [math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) for a, b in zip(pts["hand_l"], pts["hand_r"])]
    log("hand_l-hand_r distance min/max", round(min(hand_spread), 1), round(max(hand_spread), 1))
    head_above = all(h.z > p.z + 40 for h, p in zip(pts["head"], pts["pelvis"]))
    feet_low = all(min(l.z, r.z) < 25 for l, r in zip(pts["foot_l"], pts["foot_r"]))
    log("head above pelvis", head_above, "a foot near the floor every sample", feet_low)
    log("PASS" if (not bad and not missing and head_above and feet_low) else "CHECK")
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
    if "quit" in sys.argv[1:]:
        unreal.SystemLibrary.quit_editor()
