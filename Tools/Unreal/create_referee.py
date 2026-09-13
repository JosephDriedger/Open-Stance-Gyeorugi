"""Create the referee roster (MetaHuman presets) and export each body for the Blender outfit build.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/create_referee.py"            whole roster
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/create_referee.py" Kelvin     one referee

Reference: Resources/Images/Referee_Ref.png. Matches pick a referee at random from ROSTER, so the
roster mixes ages, builds and skin tones. All wear the same uniform (Tools/Blender/build_referee_outfit.py).
Outputs per referee <P>
  /Game/Characters/Officials/MH_Referee_<P>                 MetaHuman Character (copy of preset <P>)
  /Game/Characters/Officials/Export/MH_Referee_<P>_*        exported head / body / full-body meshes
  Resources/Models/MetaHuman/MH_Referee_<P>_Body.fbx (+ _Head, _FullBody)
No cloud requests.
"""
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT_DIR = f"{REPO}/Resources/Models/MetaHuman"
LOG = f"{REPO}/Saved/Logs/create_referee.txt"
PACKAGE = "/Game/Characters/Officials"
EXPORT_PATH = f"{PACKAGE}/Export"
# preset name -> height (cm)
ROSTER = {"Kelvin": 178.0, "Bo": 172.0, "Jorge": 176.0, "Omari": 184.0, "Walter": 175.0, "Vivian": 168.0}
EAL = unreal.EditorAssetLibrary

os.makedirs(OUT_DIR, exist_ok=True)
_log = open(LOG, "w", encoding="utf-8")


def log(*args):
    msg = " ".join(str(a) for a in args)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[create_referee] {msg}")


def export_fbx(asset, filename):
    task = unreal.AssetExportTask()
    task.object, task.filename = asset, filename
    task.automated, task.prompt, task.replace_identical = True, False, True
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


def create(preset, height):
    name = f"MH_Referee_{preset}"
    path = f"{PACKAGE}/{name}"
    if not EAL.does_asset_exist(path):
        if not EAL.duplicate_asset(f"/MetaHumanCharacter/Optional/Presets/{preset}", path):
            raise RuntimeError(f"could not duplicate preset {preset}")
        log("duplicated", preset, "->", path)
    character = EAL.load_asset(path)
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError(f"Unable to edit {name}; close its MetaHuman Creator tab and run again.")
    try:
        constraints = subsystem.get_body_constraints(character)
        by_name = {str(c.name).lower().replace(" ", "_"): c for c in constraints}
        if "height" in by_name:
            by_name["height"].is_active = True
            by_name["height"].target_measurement = height
        subsystem.set_body_constraints(character, list(by_name.values()))
        subsystem.commit_body_state(character)
        geo = unreal.MetaHumanGeometryExportParams()
        geo.project_path = EXPORT_PATH
        geo.head_skeletal_mesh = True
        geo.body_skeletal_mesh = True
        geo.full_body_skeletal_mesh = True
        geo.overwrite_existing_assets = True
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(character, geo)
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)
    EAL.save_asset(path)
    for part in ("Body", "Head", "FullBody"):
        mesh = EAL.load_asset(f"{EXPORT_PATH}/{name}_{part}")
        if mesh:
            export_fbx(mesh, f"{OUT_DIR}/{name}_{part}.fbx")
        else:
            log("missing exported mesh", name, part)


try:
    # first draft used a single "MH_Referee" (Kelvin); the roster replaces it
    for old in (f"{PACKAGE}/MH_Referee", f"{EXPORT_PATH}/MH_Referee_Body", f"{EXPORT_PATH}/MH_Referee_Head", f"{EXPORT_PATH}/MH_Referee_FullBody"):
        if EAL.does_asset_exist(old):
            EAL.delete_asset(old)
            log("removed draft", old)
    wanted = sys.argv[1:] or list(ROSTER)
    for preset in wanted:
        create(preset, ROSTER[preset])
        log("created", preset)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
