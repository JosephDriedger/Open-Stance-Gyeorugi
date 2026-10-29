"""Import a belt-chain FBX (Tools/Blender/belt_bone_chain.py) and give it a simulating physics asset.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/setup_belt_chain.py [Medium] quit"

Takes Resources/Models/FinalRefinement/BoneChainBelt/<Kind>/<Kind>_BeltChain.fbx (rig, body, dobok and tails, the
chain bones at rest and unkeyed) and creates, add-only, under /Game/Characters/Fighters/BeltChain/<Kind>/:
    SK_BeltChain_<Kind>          skeletal mesh (new skeleton SK_BeltChain_<Kind>_Skeleton)
    <animation>                  the study's body animation
    PA_BeltChain_<Kind>          physics asset: kinematic capsules on pelvis/thighs/calves, simulated ball-jointed
                                 capsules on belt_l_01..08 and belt_r_01..08 (C++ helper OpenStanceBeltChainLibrary)

With the argument `fit` it imports <Kind>_BeltFollowerFit.fbx (the follower refitted to the real gear: real belt band
and knot plus the chain tails, see Tools/Blender/refit_belt_to_gear.py) as SK_BeltFollowerFit_<Kind> with larger collision
capsules. With the argument `follower` it imports <Kind>_BeltFollower.fbx (belt band, waistband and tails only) as
SK_BeltFollower_<Kind> + PA_BeltFollower_<Kind> instead: the mesh that follows the body under Leader Pose.
It never touches the existing Gear/ assets. Existing assets with the same names are replaced only when
OPEN_STANCE_REBUILD_BELT=1. Run Tools/Unreal/belt_chain_test.py afterwards to watch the chain simulate.
"""
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
LOG = f"{REPO}/Saved/Logs/setup_belt_chain.txt"
EAL = unreal.EditorAssetLibrary
Belt = unreal.OpenStanceBeltChainLibrary
REBUILD = os.environ.get("OPEN_STANCE_REBUILD_BELT") == "1"

# kinematic capsules the tails collide with: bone, bone it runs towards, radius (cm)
BODY = [("pelvis", "spine_01", 14.0), ("thigh_l", "calf_l", 9.5), ("thigh_r", "calf_r", 9.5),
        ("calf_l", "foot_l", 6.5), ("calf_r", "foot_r", 6.5)]
# the real jacket skirt hangs 22 cm in front of the pelvis centre and wraps the thighs, so the capsules the tails
# collide with are bigger than the bare body when the follower is the one refitted to the real gear (`fit`)
_fit_scale = float(os.environ.get("OPEN_STANCE_BELT_FIT_SCALE", "1.12"))  # 1.0 lets the cloth skirt cover the tails in bends, 1.35 floats them 6 cm off it
BODY_FIT = [(b, a, r * _fit_scale) for b, a, r in [("pelvis", "spine_01", 19.5), ("thigh_l", "calf_l", 13.0), ("thigh_r", "calf_r", 13.0),
                                                  ("calf_l", "foot_l", 8.0), ("calf_r", "foot_r", 8.0)]]
if os.environ.get("OPEN_STANCE_BELT_BODY_SCALE"):  # experiment: scale the body capsules, e.g. 0.1 to switch collision off
    BODY = [(b, a, r * float(os.environ["OPEN_STANCE_BELT_BODY_SCALE"])) for b, a, r in BODY]
CHAIN_RADIUS_CM, CHAIN_MASS_KG, SWING_DEG, LINEAR_DAMPING, ANGULAR_DAMPING = 1.2, 0.1, 40.0, 0.3, 10.0  # 6 g links twisted

CHAIN_MASS_KG = float(os.environ.get("OPEN_STANCE_BELT_MASS", CHAIN_MASS_KG))  # experiment knob
ANGULAR_DAMPING = float(os.environ.get("OPEN_STANCE_BELT_ANGDAMP", ANGULAR_DAMPING))
SWING_DEG = float(os.environ.get("OPEN_STANCE_BELT_SWING", SWING_DEG))
CHAIN_RADIUS_CM = float(os.environ.get("OPEN_STANCE_BELT_RADIUS", CHAIN_RADIUS_CM))
_log = open(LOG, "w", encoding="utf-8")


def log(*a):
    msg = " ".join(str(x) for x in a)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[setup_belt_chain] {msg}")


def import_fbx(kind, folder, style):
    fbx = f"{REPO}/Resources/Models/FinalRefinement/BoneChainBelt/{kind}/{kind}_{style}.fbx"
    if not os.path.exists(fbx):
        raise RuntimeError(f"missing {fbx}; export it with belt_bone_chain.export_fbx")
    mesh_path = f"{folder}/SK_{style}_{kind}"
    if EAL.does_asset_exist(mesh_path) and not REBUILD:
        log("mesh exists, keeping", mesh_path)
        return EAL.load_asset(mesh_path)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("automated_import_should_detect_type", False)
    data = ui.get_editor_property("skeletal_mesh_import_data")
    data.set_editor_property("import_morph_targets", False)
    data.set_editor_property("update_skeleton_reference_pose", False)
    # keep the exported (smooth) normals; recomputing them gives each skinned face its own shading
    data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx)
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", f"SK_{style}_{kind}")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = [str(p) for p in task.get_editor_property("imported_object_paths")]
    log("imported", imported)
    return EAL.load_asset(mesh_path)


# tail centre line y of each type's refit (Tools/Blender/run_refit_headless.py); capsule size follows the jacket's distance from the pelvis
TAIL_FRONT_Y = {"Medium": 0.2319, "Compact": 0.2225, "Stocky": 0.2437, "LeanTall": 0.2347, "Tall": 0.2485}
PELVIS_Y = 0.024


def fit_scale(kind):
    return (TAIL_FRONT_Y[kind] - PELVIS_Y) / (TAIL_FRONT_Y["Medium"] - PELVIS_Y)


def main(kind, style):
    global BODY
    if style == "BeltFollowerFit":
        BODY = [(b, a, r * fit_scale(kind)) for b, a, r in BODY_FIT]
        log(f"{kind}: body capsule scale {fit_scale(kind):.3f}")
    folder = f"/Game/Characters/Fighters/BeltChain/{kind}"
    EAL.make_directory(folder)
    mesh = import_fbx(kind, folder, style)
    if mesh is None:
        raise RuntimeError("skeletal mesh import failed; see the Output Log")
    chain = [str(n) for n in Belt.find_chain_bones(mesh, "belt_")]
    log("chain bones", len(chain), chain[:3], "...")
    if len(chain) != 16:
        raise RuntimeError(f"expected 16 belt_ bones, found {len(chain)}")
    pa_path = f"{folder}/PA_{style}_{kind}"
    if EAL.does_asset_exist(pa_path):
        if not REBUILD:
            log("physics asset exists, keeping", pa_path)
            return
        pa = EAL.load_asset(pa_path)  # rebuilt in place: the helper replaces every body and joint
    else:
        pa = Belt.create_empty_physics_asset(folder, f"PA_{style}_{kind}")
    if pa is None:
        raise RuntimeError("physics asset creation failed")
    result = Belt.build_belt_chain_physics_asset(
        mesh, pa, [unreal.Name(b) for b, _, _ in BODY], [unreal.Name(a) for _, a, _ in BODY], [r for _, _, r in BODY],
        "belt_", CHAIN_RADIUS_CM, CHAIN_MASS_KG, SWING_DEG, LINEAR_DAMPING, ANGULAR_DAMPING)
    log("physics asset:", result)
    if result.startswith("ERROR"):
        raise RuntimeError(result)
    EAL.save_asset(pa_path, only_if_is_dirty=False)
    EAL.save_asset(f"{folder}/SK_{style}_{kind}", only_if_is_dirty=False)
    log("saved", pa_path)


try:
    args = [a for a in sys.argv[1:] if a != "quit"]
    style = "BeltFollowerFit" if "fit" in args else "BeltFollower" if "follower" in args else "BeltChain"
    for k in [a for a in args if a not in ("follower", "fit")] or ["Medium"]:
        main(k, style)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
    if "quit" in sys.argv[1:]:
        unreal.SystemLibrary.quit_editor()
