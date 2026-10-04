"""Export MetaHuman's stock skin, eye and teeth textures to PNG for the test model outside Unreal.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/export_stock_skin_textures.py"

The fighters have no Creator-synthesized skin textures (MH_FighterBase's synthesized texture maps are empty), so the
Blender/MotionBuilder test model uses the plugin's generic maps: body skin colour and normal, the MetaHuman Animator
archetype head colour (same head UV layout as every DNA head), eyeball sclera and iris, teeth.
Writes Resources/Models/MetaHuman/Textures/Stock/<name>.png. Log: Saved/Logs/export_stock_skin_textures.txt.
"""
import os
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Resources/Models/MetaHuman/Textures/Stock"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/export_stock_skin_textures.txt"
TEXTURES = [
    "/MetaHumanCharacter/Optional/BodyTextures/T_Skin_V1_Body_BC",
    "/MetaHumanCharacter/Optional/BodyTextures/T_Skin_V1_Chest_BC",
    "/MetaHumanCharacter/Optional/BodyTextures/T_Skin_V2_Body_BC",
    "/MetaHumanCharacter/Optional/BodyTextures/T_Skin_V2_Chest_BC",
    "/MetaHumanCharacter/Optional/BodyTextures/SurfaceDetail/T_Chr0005_Body_N",
    "/MetaHumanCharacter/Optional/BodyTextures/SurfaceDetail/T_Chr0005_Chest_N",
    "/MetaHumanAnimator/IdentityTemplate/DefaultArchetypeTexture/T_MetaHumanIdentity_Head_D",
    "/MetaHumanAnimator/IdentityTemplate/DefaultArchetypeTexture/T_MetaHumanIdentity_Teeth_D",
    "/MetaHumanCharacter/Lookdev_UHM/Teeth/Textures/T_Teeth_BaseColor",
    "/MetaHumanCharacter/Lookdev_UHM/Eye/Textures/T_EyeSclera_D",
    "/MetaHumanCharacter/Lookdev_UHM/Eye/Textures/T_Iris001_01_D",
    "/MetaHumanCharacter/Lookdev_UHM/Eye/Textures/T_Veins_D",
]
os.makedirs(OUT, exist_ok=True)
f = open(LOG, "w")
try:
    for p in TEXTURES:
        t = unreal.EditorAssetLibrary.load_asset(p)
        if t is None:
            f.write(f"missing {p}\n")
            continue
        task = unreal.AssetExportTask()
        task.object = t
        task.filename = f"{OUT}/{p.split('/')[-1]}.png"
        task.automated, task.prompt, task.replace_identical = True, False, True
        ok = unreal.Exporter.run_asset_export_task(task)
        size = f"{t.blueprint_get_size_x()}x{t.blueprint_get_size_y()}"
        f.write(f"{'ok' if ok else 'FAILED'} {p} {size} srgb={t.get_editor_property('srgb')} -> {task.filename}\n")
        f.flush()
    f.write("DONE\n")
except Exception:
    f.write("ERROR " + traceback.format_exc())
f.close()
unreal.SystemLibrary.quit_editor()
