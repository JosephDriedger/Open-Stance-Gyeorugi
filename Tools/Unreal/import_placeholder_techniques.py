"""Import the placeholder technique animations and make the montages the move data names.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/import_placeholder_techniques.py quit"

Reads Resources/Models/Animation/PlaceholderTechniques/Placeholder_<Name>.fbx (Tools/Blender/build_placeholder_techniques.py)
and creates, under /Game/Animation/Moves/Placeholder/:
    AS_Placeholder_<Name>     animation sequence on the production fighter skeleton (Stance and every technique)
    AM_Placeholder_<Name>     montage of it (techniques only; DT_MoveData's PlaceholderMontage column points here)
Sequences of those names are re-imported in place; existing montages are kept (they play the re-imported clip). Log: Saved/Logs/import_placeholder_techniques.txt.
"""
import os
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
SOURCE = f"{REPO}/Resources/Models/Animation/PlaceholderTechniques"
DEST = "/Game/Animation/Moves/Placeholder"
BODY = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
NAMES = ["Stance", "SideKick", "Roundhouse", "Hook", "Axe", "Punch", "SpinSide", "SpinHook", "Tornado"]
EAL = unreal.EditorAssetLibrary
LOG = open(f"{REPO}/Saved/Logs/import_placeholder_techniques.txt", "w", encoding="utf-8")


def log(*parts):
    LOG.write(" ".join(str(p) for p in parts) + "\n")
    LOG.flush()


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    skeleton = EAL.load_asset(BODY).get_editor_property("skeleton")
    log("skeleton", skeleton.get_path_name())
    for body in ("MH_FighterCompact", "MH_FighterStocky", "MH_FighterLeanTall", "MH_FighterTall"):
        other = EAL.load_asset(f"/Game/Characters/Fighters/Export/{body}_Body")
        log(" ", body, "skeleton", other.get_editor_property("skeleton").get_path_name() if other else None)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for name in NAMES:
        fbx = f"{SOURCE}/Placeholder_{name}.fbx"
        if not os.path.exists(fbx):
            log("missing", fbx)
            continue
        ui = unreal.FbxImportUI()
        ui.import_mesh = False
        ui.import_animations = True
        ui.import_as_skeletal = True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        ui.automated_import_should_detect_type = False
        ui.import_materials = False
        ui.import_textures = False
        ui.skeleton = skeleton
        anim_data = ui.anim_sequence_import_data
        anim_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        anim_data.set_editor_property("remove_redundant_keys", False)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = fbx, DEST, f"AS_Placeholder_{name}"
        task.automated, task.replace_existing, task.save, task.options = True, True, True, ui
        tools.import_asset_tasks([task])
        sequence = EAL.load_asset(f"{DEST}/AS_Placeholder_{name}")
        if not isinstance(sequence, unreal.AnimSequence):
            log("import failed", name, task.get_editor_property("imported_object_paths"))
            continue
        log("imported", name, f"{sequence.get_play_length():.3f}s")
        if name == "Stance":
            continue
        montage_path = f"{DEST}/AM_Placeholder_{name}"
        if EAL.does_asset_exist(montage_path):
            # The sequence is re-imported in place, so an existing montage already plays the new clip (deleting and
            # re-creating it fails once it has been loaded).
            montage = EAL.load_asset(montage_path)
            log("montage kept", montage.get_path_name(), f"{montage.get_play_length():.3f}s")
            continue
        factory = unreal.AnimMontageFactory()
        factory.set_editor_property("source_animation", sequence)
        montage = tools.create_asset(f"AM_Placeholder_{name}", DEST, unreal.AnimMontage, factory)
        EAL.save_asset(montage_path, only_if_is_dirty=False)
        log("montage", montage.get_path_name() if montage else "FAILED", f"{montage.get_play_length():.3f}s" if montage else "")
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
