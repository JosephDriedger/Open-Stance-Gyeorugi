"""Create the four non-base fighter body types (GDD 5.4.2) and export what the Blender refit needs.

Medium is the base fighter (create_base_fighter.py, 175 cm). This makes Compact, Stocky, Lean tall
and Tall the same way and exports them for Tools/Blender/fit_to_body.py:

    UnrealEditor-Cmd.exe OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecutePythonScript="D:/Open-Stance-Gyeorugi/Tools/Unreal/create_body_types.py"

Outputs per type (<Name> = Compact, Stocky, LeanTall, Tall)
  /Game/Characters/Fighters/MH_Fighter<Name>                MetaHuman Character asset
  /Game/Characters/Fighters/Export/MH_Fighter<Name>_*       exported head / body / full-body meshes
  Resources/Models/MetaHuman/MH_Fighter<Name>_{Body,Head,FullBody}.fbx

Height is set directly. MetaHuman's body has no weight control, so weight becomes girth: the trunk and
limb circumferences are scaled by sqrt(BMI / medium BMI) (cross-section area follows mass at a fixed
height), measured after the height change so proportions stay MetaHuman-consistent. Medium is
175 cm, 68 kg (BMI 22.2). No cloud requests.
"""
import math
import os
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT_DIR = f"{REPO}/Resources/Models/MetaHuman"
LOG = f"{REPO}/Saved/Logs/create_body_types.txt"
PACKAGE = "/Game/Characters/Fighters"
EXPORT_PATH = f"{PACKAGE}/Export"
MEDIUM_BMI = 68.0 / 1.75 ** 2

# name: (height cm, weight kg), GDD 5.4.2
BODY_TYPES = {
    "Compact": (165.0, 60.0),
    "Stocky": (172.0, 80.0),
    "LeanTall": (185.0, 72.0),
    "Tall": (192.0, 84.0),
}
# Circumference constraints that follow body mass (lengths and the neck base/wrist/hand stay as the
# height change set them).
GIRTHS = ["Chest", "Waist", "Hip", "High Hip", "Thigh", "Knee", "Calf", "Bicep", "Forearm", "Neck"]

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG), exist_ok=True)
_log = open(LOG, "w", encoding="utf-8")


def log(*args):
    msg = " ".join(str(a) for a in args)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[create_body_types] {msg}")


def export_fbx(asset, filename):
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True
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


def by_name(constraints):
    return {str(c.name): c for c in constraints}


def build(subsystem, name, height, weight):
    asset_path = f"{PACKAGE}/MH_Fighter{name}"
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        character = unreal.EditorAssetLibrary.load_asset(asset_path)
        log("using existing", asset_path)
    else:
        character = tools.create_asset(f"MH_Fighter{name}", PACKAGE, unreal.MetaHumanCharacter,
                                       unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
        log("created", asset_path)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError(f"Unable to edit {asset_path}; close its MetaHuman Creator tab and run again.")
    try:
        cons = by_name(subsystem.get_body_constraints(character))
        cons["Height"].is_active = True
        cons["Height"].target_measurement = height
        subsystem.set_body_constraints(character, list(cons.values()))
        subsystem.commit_body_state(character)

        # Girths as the MetaHuman body measures them at this height, then scaled by mass.
        cons = by_name(subsystem.get_body_constraints(character))
        factor = math.sqrt(weight / (height / 100.0) ** 2 / MEDIUM_BMI)
        log(name, f"{height:.0f} cm {weight:.0f} kg: BMI {weight / (height / 100.0) ** 2:.1f}, girth factor {factor:.3f}")
        for g in GIRTHS:
            c = cons[g]
            before = c.target_measurement
            c.is_active = True
            c.target_measurement = min(c.max_measurement, max(c.min_measurement, before * factor))
            log(f"   {g}: {before:.1f} -> {c.target_measurement:.1f} cm")
        subsystem.set_body_constraints(character, list(cons.values()))
        subsystem.commit_body_state(character)

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

    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    for part in ("Body", "Head", "FullBody"):
        mesh = unreal.EditorAssetLibrary.load_asset(f"{EXPORT_PATH}/MH_Fighter{name}_{part}")
        if mesh is None:
            log("missing exported mesh", name, part)
            continue
        export_fbx(mesh, f"{OUT_DIR}/MH_Fighter{name}_{part}.fbx")


try:
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    for name, (height, weight) in BODY_TYPES.items():
        try:
            build(subsystem, name, height, weight)
        except Exception:
            log("ERROR", name, "\n" + traceback.format_exc())
    unreal.EditorAssetLibrary.save_directory(PACKAGE, only_if_is_dirty=True, recursive=True)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
