"""Add the SkeletalMesh item pipeline to existing WI_Fighter_<Part> wardrobe items.

For items created before import_fighter_gear.py set pipelines. Safe to run in an open editor.
"""
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
LOG = f"{REPO}/Saved/Logs/fix_wardrobe_pipelines.txt"
GEAR = "/Game/Characters/Fighters/Gear"
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
EAL = unreal.EditorAssetLibrary

_log = open(LOG, "w", encoding="utf-8")


def log(*args):
    msg = " ".join(str(a) for a in args)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[fix_wardrobe_pipelines] {msg}")


try:
    editor_cls = unreal.load_class(None, "/Script/MetaHumanDefaultEditorPipeline.MetaHumanSkeletalMeshEditorPipeline")
    for part in PARTS:
        path = f"{GEAR}/WI_Fighter_{part}"
        item = EAL.load_asset(path)
        if item is None:
            log("missing", path)
            continue
        pipeline = item.get_editor_property("pipeline")
        if pipeline is None:
            pipeline = unreal.new_object(unreal.MetaHumanSkeletalMeshPipeline, outer=item)
            item.set_editor_property("pipeline", pipeline)
        if pipeline.get_editor_property("editor_pipeline") is None:
            pipeline.set_editor_property("editor_pipeline", unreal.new_object(editor_cls, outer=pipeline))
        editor = pipeline.get_editor_property("editor_pipeline")
        log(part, "pipeline", pipeline.get_path_name(), "editor", editor.get_path_name() if editor else None,
            "editor outer", editor.get_outer().get_path_name() if editor else None)
        EAL.save_asset(path, only_if_is_dirty=False)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
