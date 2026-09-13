"""Entry point for the fighter rig tools.

Blender Python console (Scripting workspace):
    p = r"D:\\Open-Stance-Gyeorugi\\Tools\\Blender\\run.py"; exec(compile(open(p).read(), p, "exec"))
    run("pipeline")          # import -> build rig -> weights -> export -> verify
    run("posetest"); pose_chamber()

Command line:
    blender --background --factory-startup --python Tools/Blender/run.py -- pipeline
"""
import importlib
import os
import sys

# co_filename works both for `blender --python` and for exec(compile(src, path, "exec")) in the console.
TOOLS_DIR = os.path.dirname(os.path.abspath(sys._getframe(0).f_code.co_filename))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

PIPELINE = [
    # rig
    "import_source", "build_rig", "reweight", "body_shapes", "export_fbx", "verify_fbx",
    # customization
    "segment_parts", "assign_parts", "split_parts", "make_masks", "preview_material", "export_parts",
    "save_blend",
]
# These define helper functions meant for interactive use, so they run in the caller's namespace.
SHARED = {"viewtools", "posetest", "preview_material"}


def run(name, **params):
    """Run a tool script by name (without .py), or "pipeline" for the full rebuild.

    Keyword params are injected as globals into the script, e.g.
    run("transfer_weights", TRANSFER_TARGETS=["MyHelmet"]).
    """
    import rig_config
    importlib.reload(rig_config)

    if name == "pipeline":
        for step in PIPELINE:
            run(step)
        return

    path = os.path.join(TOOLS_DIR, name + ".py")
    code = compile(open(path, encoding="utf-8").read(), path, "exec")
    if name in SHARED:
        globals().update(params)
        exec(code, globals())
    else:
        exec(code, {"__name__": "__main__", "__file__": path, **params})
    print(f"[run] {name} done")


if "--" in sys.argv:
    for arg in sys.argv[sys.argv.index("--") + 1:]:
        run(arg)
