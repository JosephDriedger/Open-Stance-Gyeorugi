"""Import the nations' flags for the menu (Fighter Select cards and side panels).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/import_flags.py quit"

Reads Resources/UI/Flags/<CODE>.png (320 px wide; public-domain flag images from flagcdn.com, named by the roster's
country codes, e.g. KOR, IRI, NGR) and writes /Game/Menu/Flags/T_Flag_<CODE> as UI textures (no mipmaps, UI group,
UserInterface2D compression). Existing textures are replaced. Log: Saved/Logs/import_flags.txt.
"""
import glob
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
DEST = "/Game/Menu/Flags"
EAL = unreal.EditorAssetLibrary
LOG = open(f"{REPO}/Saved/Logs/import_flags.txt", "w", encoding="utf-8")
try:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for png in sorted(glob.glob(f"{REPO}/Resources/UI/Flags/*.png")):
        code = os.path.splitext(os.path.basename(png))[0]
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = png, DEST, f"T_Flag_{code}"
        task.automated, task.replace_existing, task.save = True, True, False
        tools.import_asset_tasks([task])
        texture = EAL.load_asset(f"{DEST}/T_Flag_{code}")
        if not isinstance(texture, unreal.Texture2D):
            LOG.write(f"FAILED {code}\n")
            continue
        texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property("srgb", True)
        EAL.save_asset(f"{DEST}/T_Flag_{code}", only_if_is_dirty=False)
        LOG.write(f"imported {code} {texture.blueprint_get_size_x()}x{texture.blueprint_get_size_y()}\n")
    LOG.write("DONE\n")
except Exception:
    LOG.write("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
    if "quit" in sys.argv[1:]:
        unreal.SystemLibrary.quit_editor()
