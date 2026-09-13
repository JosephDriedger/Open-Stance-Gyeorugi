"""Create the base fighter MetaHuman and export what the Blender refit needs.

Run inside the Open Stance project, e.g.:
    UnrealEditor.exe OpenStance.uproject -ExecutePythonScript="D:/Open-Stance-Gyeorugi/Tools/Unreal/create_base_fighter.py"
or from the Output Log (Python):  exec(open(r"D:/Open-Stance-Gyeorugi/Tools/Unreal/create_base_fighter.py").read())

Outputs
  /Game/Characters/Fighters/MH_FighterBase                 MetaHuman Character asset (medium build)
  /Game/Characters/Fighters/Export/MH_FighterBase_*        exported head / body / full-body skeletal meshes
  Resources/Models/MetaHuman/MH_FighterBase_Body.fbx       for Tools/Blender/fit_to_body.py
  Resources/Models/MetaHuman/MH_FighterBase_Head.fbx
  Resources/Models/MetaHuman/MH_FighterBase_FullBody.fbx
  Resources/Models/MetaHuman/T_iris_color_picker.png       iris colour chart, for natural eye presets

Geometry export needs the character open for editing but no face rig or texture download,
so this script makes no cloud requests.
"""
import os
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT_DIR = f"{REPO}/Resources/Models/MetaHuman"
LOG = f"{REPO}/Saved/Logs/create_base_fighter.txt"
PACKAGE = "/Game/Characters/Fighters"
NAME = "MH_FighterBase"
EXPORT_PATH = f"{PACKAGE}/Export"
HEIGHT_CM = 175.0

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG), exist_ok=True)
_log = open(LOG, "w", encoding="utf-8")


def log(*args):
    msg = " ".join(str(a) for a in args)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[create_base_fighter] {msg}")


def export_asset(asset, filename, exporter=None, fbx=False):
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if exporter:
        task.exporter = exporter
    if fbx:
        opts = unreal.FbxExportOption()
        opts.export_morph_targets = True
        opts.export_preview_mesh = False
        opts.level_of_detail = False
        opts.collision = False
        opts.vertex_color = True
        opts.fbx_export_compatibility = unreal.FbxExportCompatibility.FBX_2020
        task.options = opts
    ok = unreal.Exporter.run_asset_export_task(task)
    log("export", asset.get_path_name(), "->", filename, "ok" if ok else "FAILED")
    return ok


try:
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    asset_path = f"{PACKAGE}/{NAME}"

    character = unreal.EditorAssetLibrary.load_asset(asset_path) if unreal.EditorAssetLibrary.does_asset_exist(asset_path) else None
    if character is None:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        character = tools.create_asset(NAME, PACKAGE, unreal.MetaHumanCharacter, unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
        log("created", asset_path)
    else:
        log("using existing", asset_path)

    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("Unable to edit the character; close its MetaHuman Creator tab and run again.")

    try:
        # Medium build: set height, leave the other parametric measurements at their defaults.
        constraints = subsystem.get_body_constraints(character)
        by_name = {str(c.name).lower().replace(" ", "_"): c for c in constraints}
        log("body constraints:", sorted(by_name))
        if "height" in by_name:
            by_name["height"].is_active = True
            by_name["height"].target_measurement = HEIGHT_CM
        subsystem.set_body_constraints(character, list(by_name.values()))
        subsystem.commit_body_state(character)
        log("body state committed, height", HEIGHT_CM)

        geo = unreal.MetaHumanGeometryExportParams()
        geo.project_path = EXPORT_PATH
        geo.head_skeletal_mesh = True
        geo.body_skeletal_mesh = True
        geo.full_body_skeletal_mesh = True
        geo.overwrite_existing_assets = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(character, geo)
        log("geometry exported to", EXPORT_PATH)
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)

    unreal.EditorAssetLibrary.save_directory(PACKAGE, only_if_is_dirty=True, recursive=True)

    for part in ("Body", "Head", "FullBody"):
        mesh = unreal.EditorAssetLibrary.load_asset(f"{EXPORT_PATH}/{NAME}_{part}")
        if mesh is None:
            log("missing exported mesh", part)
            continue
        export_asset(mesh, f"{OUT_DIR}/{NAME}_{part}.fbx", fbx=True)

    iris = unreal.EditorAssetLibrary.load_asset("/MetaHumanCharacter/Lookdev_UHM/Eye/Textures/T_iris_color_picker")
    if iris:
        export_asset(iris, f"{OUT_DIR}/T_iris_color_picker.png", exporter=unreal.TextureExporterPNG())
    else:
        log("iris colour picker texture not found")

    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
