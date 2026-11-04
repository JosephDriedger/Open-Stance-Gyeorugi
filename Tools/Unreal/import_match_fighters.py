"""Import the match fighters: every premade fighter in the layered dobok with its sparring gear, per side.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/import_match_fighters.py quit"

Reads Resources/Models/FinalRefinement/Match/Roster/<Key>_<Chung|Hong>/SK_Match_<Key>_<Side>.fbx
(Tools/Blender/build_match_fighters.sh) and writes /Game/Characters/Fighters/Match/<Key>_<Side>/SK_Match_<Key>_<Side> on the
production fighter skeleton (the placeholder clips' skeleton). The greybox match shows the chosen fighters with these.
Existing assets are replaced. Log: Saved/Logs/import_match_fighters.txt.
"""
import json
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
SOURCE = f"{REPO}/Resources/Models/FinalRefinement/Match/Roster"
DEST = "/Game/Characters/Fighters/Match"
SKELETON_FROM = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
KEYS = [f["key"] for f in json.load(open(f"{REPO}/Tools/Blender/portrait_roster.json"))["fighters"]]
EAL = unreal.EditorAssetLibrary
LOG = open(f"{REPO}/Saved/Logs/import_match_fighters.txt", "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    skeleton = EAL.load_asset(SKELETON_FROM).get_editor_property("skeleton")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for key in KEYS:
        for side in ("Chung", "Hong"):
            name = f"{key}_{side}"
            fbx = f"{SOURCE}/{name}/SK_Match_{name}.fbx"
            if not os.path.exists(fbx):
                log("missing", fbx)
                continue
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
            task.filename, task.destination_path, task.destination_name = fbx, f"{DEST}/{name}", f"SK_Match_{name}"
            task.automated, task.replace_existing, task.save, task.options = True, True, True, ui
            tools.import_asset_tasks([task])
            mesh = EAL.load_asset(f"{DEST}/{name}/SK_Match_{name}")
            if not isinstance(mesh, unreal.SkeletalMesh):
                log("import failed", name)
                continue
            for path in EAL.list_assets(f"{DEST}/{name}", recursive=True):
                EAL.save_asset(path, only_if_is_dirty=True)
            log("imported", name, "height %.1f cm" % (mesh.get_bounds().box_extent.z * 2))
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
    if "quit" in sys.argv[1:]:
        unreal.SystemLibrary.quit_editor()
