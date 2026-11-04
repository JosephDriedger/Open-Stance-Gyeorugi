"""Render the menu's fighter portrait studio for every body type (headless), to check the build, stance, lighting and cut-out.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_fighter_studio.py [seconds=S] quit"

Images: Saved/Screenshots/FighterStudio/<BodyType>_<Sex>.png (the colour capture, before the cut-out); log
Saved/Logs/capture_fighter_studio.txt with each depth summary.
"""
import os
import sys

import unreal

OUT = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "FighterStudio")
LOG = os.path.join(unreal.Paths.project_saved_dir(), "Logs", "capture_fighter_studio.txt")
args = sys.argv[1:]
seconds = float(next((a.split("=")[1] for a in args if a.startswith("seconds=")), 0.3))
lines = []
for body in (unreal.OpenStanceBodyType.COMPACT, unreal.OpenStanceBodyType.LEAN_TALL, unreal.OpenStanceBodyType.STOCKY,
             unreal.OpenStanceBodyType.TALL):
    for sex in (unreal.OpenStanceSex.MALE, unreal.OpenStanceSex.FEMALE):
        name = "%s_%s" % (str(body).split(".")[-1].split(":")[0].strip("<> "), str(sex).split(".")[-1].split(":")[0].strip("<> "))
        path = os.path.join(OUT, name + ".png").replace("\\", "/")
        summary = unreal.OpenStanceMenuCaptureLibrary.capture_fighter_studio(body, sex, False, seconds, path)
        lines.append("%s: %s" % (name, summary))
os.makedirs(os.path.dirname(LOG), exist_ok=True)
with open(LOG, "w") as f:
    f.write("\n".join(lines) + "\n")
if "quit" in args:
    unreal.SystemLibrary.quit_editor()
