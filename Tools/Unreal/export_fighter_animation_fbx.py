"""Export MetaHuman's body range-of-motion animation, with its skeleton, as FBX.

    UnrealEditor-Cmd.exe OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecutePythonScript="D:/Open-Stance-Gyeorugi/Tools/Unreal/export_fighter_animation_fbx.py"

Writes Saved/Exports/<Type>_ROM_skeleton.fbx (centimetres, Z up, 30 fps). Nothing is saved to the project. Then
Tools/Blender/assemble_animated_fbx.py attaches the fighter's full-body mesh and gear pieces (from the Resources FBX
files) to that animated skeleton and writes the finished file to Resources/Previews/. (Exporting the mesh with the
animation crashes Unreal's material baking on the full-body mesh, and its skeletal mesh merge can't be driven from
Python here, which is why the pieces are assembled in Blender.)
Set OPEN_STANCE_BODY_TYPE (Medium, Compact, Stocky, LeanTall, Tall) to choose the fighter.
"""
import os
import traceback

import unreal

TYPE = os.environ.get("OPEN_STANCE_BODY_TYPE", "Medium")
ASSET = "MH_FighterBase" if TYPE == "Medium" else f"MH_Fighter{TYPE}"
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
OUT_DIR = "D:/Open-Stance-Gyeorugi/Saved/Exports"
OUT = f"{OUT_DIR}/{TYPE}_ROM_skeleton.fbx"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/export_fighter_animation_fbx.txt"
os.makedirs(OUT_DIR, exist_ok=True)
o = open(LOG, "w", encoding="utf-8")


def w(*a):
    o.write(" ".join(str(x) for x in a) + "\n")
    o.flush()


try:
    EAL = unreal.EditorAssetLibrary
    anim = EAL.load_asset(ANIM)
    opts = unreal.FbxExportOption()
    opts.set_editor_property("export_preview_mesh", False)   # exporting the mesh with it crashes in material baking
    opts.set_editor_property("fbx_export_compatibility", unreal.FbxExportCompatibility.FBX_2020)
    task = unreal.AssetExportTask()
    task.object = anim
    task.filename = OUT
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.options = opts
    ok = unreal.Exporter.run_asset_export_task(task)
    w("export", OUT, "ok" if ok else "FAILED", os.path.getsize(OUT) if os.path.exists(OUT) else "missing")
    w("DONE")
except Exception:
    w("ERROR", traceback.format_exc())
o.close()
unreal.SystemLibrary.quit_editor()
