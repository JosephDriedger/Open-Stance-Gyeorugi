"""Creates /Game/Maps/L_MainMenu, the empty level the menu runs in.

The menu draws itself (Source/OpenStance/Public/Menu), so the level holds nothing but World Settings, whose game
mode override is AOpenStanceMenuGameMode: no pawn, and a player controller that opens the title screen. Project
Settings point GameDefaultMap at this level, so the game starts in the menu. Safe to re-run: an existing level
is opened and its game mode set again.

  UnrealEditor-Cmd.exe <project> -unattended -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/build_menu_level.py quit"
"""
import sys

import unreal

PATH = "/Game/Maps/L_MainMenu"

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    levels.load_level(PATH)
else:
    levels.new_level(PATH)

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.OpenStanceMenuGameMode)
saved = levels.save_current_level()
unreal.log("L_MainMenu %s" % ("saved" if saved else "NOT SAVED"))

if "quit" in sys.argv[1:]:
    unreal.SystemLibrary.quit_editor()
