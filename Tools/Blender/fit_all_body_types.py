"""Fit the dobok and gear to every MetaHuman body type, then bake hidden face maps.

Run headless (no window), once per body:

    blender --background --factory-startup --python Tools/Blender/fit_all_body_types.py -- Compact Stocky LeanTall Tall

With no names it does all five (Base is the Medium fighter). Each body is fitted from a fresh copy of Fighter_Rigged.blend
(fit_to_body edits the scene), so run order doesn't matter. Needs
Tools/Unreal/create_body_types.py to have exported Resources/Models/MetaHuman/MH_Fighter<Name>_*.fbx.
Outputs Resources/Models/Fitted/MH_Fighter<Name>_Body/ and a log per body in Tools/Blender/logs/.
"""
import os
import shutil
import sys
import traceback

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
names = names or ["Base", "Compact", "Stocky", "LeanTall", "Tall"]   # Base = the Medium fighter
LOGS = f"{ROOT}/Tools/Blender/logs"
STATUS = f"{ROOT}/Saved/Logs/fit_all_body_types.txt"


def say(msg):
    with open(STATUS, "a") as f:
        f.write(msg + "\n")


open(STATUS, "w").close()
for name in names:
    try:
        bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/Resources/Models/Fighter_Rigged.blend")
        p = f"{ROOT}/Tools/Blender/run.py"
        g = {"__name__": "driver", "__file__": p}
        exec(compile(open(p).read(), p, "exec"), g)
        m = f"{ROOT}/Resources/Models/MetaHuman/MH_Fighter{name}"
        g["run"]("fit_to_body", TARGET_FBX=f"{m}_Body.fbx", TARGET_HEAD_FBX=f"{m}_Head.fbx")
        g["run"]("hidden_face_maps", TARGET_NAME=f"MH_Fighter{name}_Body")
        bpy.ops.wm.save_as_mainfile(
            filepath=f"{ROOT}/Resources/Models/Fitted/MH_Fighter{name}_Body/FitPreview_MH_Fighter{name}.blend", copy=True)
        for log in ("fit_to_body", "hidden_face_maps"):
            shutil.copy(f"{LOGS}/{log}.txt", f"{LOGS}/{log}_{name}.txt")
        say(f"{name}: done")
    except Exception:
        say(f"{name}: ERROR\n{traceback.format_exc()}")
say("ALL DONE")
