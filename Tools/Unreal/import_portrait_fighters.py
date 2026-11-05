"""Import the menu portrait fighters (every body type as a man and a woman, in the dobok) and refresh the stance clips.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/import_portrait_fighters.py"

Reads Resources/Models/FinalRefinement/Portrait/<Kind>_<Sex>/SK_Portrait_<Kind>_<Sex>.fbx (Tools/Blender/
build_portrait_fighters.sh) and writes /Game/Characters/Fighters/Portrait/SK_Portrait_<Kind>_<Sex>, with its materials
and textures, on the production fighter skeleton, so the placeholder technique clips (authored on the same suite rig)
play on it without distortion. Also imports every premade fighter's own portrait (Tools/Blender/portrait_roster.json,
build_roster_portraits.sh) from Portrait/Roster/<Key>/ to /Game/Characters/Fighters/Portrait/Roster/<Key>/SK_Portrait_<Key>.
Pass `roster` to import only those. Existing assets of those names are replaced. Log: Saved/Logs/import_portrait_fighters.txt.
"""
import json
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
SOURCE = f"{REPO}/Resources/Models/FinalRefinement/Portrait"
DEST = "/Game/Characters/Fighters/Portrait"
SKELETON_FROM = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
BUILDS = [f"{k}_{s}" for k in ("Compact", "LeanTall", "Stocky", "Tall") for s in ("Male", "Female")]
ROSTER = [f["key"] for f in json.load(open(f"{REPO}/Tools/Blender/portrait_roster.json"))["fighters"]]
# (folder under SOURCE and DEST, asset name stem)
TARGETS = ([] if "roster" in sys.argv[1:] else [(t, t) for t in BUILDS]) + [(f"Roster/{k}", k) for k in ROSTER]
EAL = unreal.EditorAssetLibrary
LOG = open(f"{REPO}/Saved/Logs/import_portrait_fighters.txt", "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    skeleton = EAL.load_asset(SKELETON_FROM).get_editor_property("skeleton")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for sub, target in TARGETS:
        fbx = f"{SOURCE}/{sub}/SK_Portrait_{target}.fbx"
        if not os.path.exists(fbx):
            log("missing", fbx)
            continue
        folder = f"{DEST}/{sub}"
        ui = unreal.FbxImportUI()
        ui.import_mesh = True
        ui.import_as_skeletal = True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        ui.automated_import_should_detect_type = False
        ui.import_animations = False
        ui.import_materials = True
        ui.import_textures = True
        ui.create_physics_asset = False
        ui.skeleton = skeleton
        ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
        ui.skeletal_mesh_import_data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = fbx, folder, f"SK_Portrait_{target}"
        task.automated, task.replace_existing, task.save, task.options = True, True, True, ui
        tools.import_asset_tasks([task])
        mesh = EAL.load_asset(f"{folder}/SK_Portrait_{target}")
        if not isinstance(mesh, unreal.SkeletalMesh):
            log("import failed", target, task.get_editor_property("imported_object_paths"))
            continue
        b = mesh.get_bounds()
        log("imported", target, "height %.1f cm" % (b.box_extent.z * 2), "materials", len(mesh.get_editor_property("materials")))
        for path in EAL.list_assets(folder, recursive=True):
            EAL.save_asset(path, only_if_is_dirty=True)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
    if "quit" in sys.argv[1:]:  # the command line's own quit can hang after an import; leave from here instead
        unreal.SystemLibrary.quit_editor()
