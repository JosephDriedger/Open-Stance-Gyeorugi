"""Import the belt-chain mocap targets (Resources/Models/Animation/MotionBuilder_BeltChain) and check their skeletons in engine.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="Interchange.FeatureFlags.Import.FBX 0,py D:/Open-Stance-Gyeorugi/Tools/Unreal/test_belt_chain_targets.py [Medium ...] [vneck] [keep] quit"

For every body type named (default all nine) and each of dobok/sparring (and the WhiteVNeck folder with `vneck`), imports the
characterized target FBX into /Game/__BeltChainImportTest__/ (skeletal mesh only: no textures, animations or physics asset),
then compares its skeleton with the project's own fighter body skeleton (/Game/Characters/Fighters/Export/MH_Fighter*_Body):
bones missing or extra, parent differences, rest-position differences, and the 16 belt_ chain bones and their parents. The
imported assets are deleted afterwards unless `keep` is given. Each run owns a unique scratch subfolder. Report:
Saved/Logs/belt_chain_targets.json and .txt. The legacy FBX importer is explicitly selected by the command above;
the earlier Interchange run stalled during import. Run without another copy writing these same report paths.
"""
import json
import sys
import traceback
import uuid
import os

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
ROOT = f"{REPO}/Resources/Models/Animation/MotionBuilder_BeltChain"
ROOT = os.environ.get('OPENSTANCE_TARGET_ROOT', ROOT)
TEST = "/Game/__BeltChainImportTest__/Run_" + uuid.uuid4().hex
OUT = f"{REPO}/Saved/Logs/belt_chain_targets"
OUT = os.environ.get('OPENSTANCE_TARGET_AUDIT_OUT', OUT)
KINDS = ["Medium", "Compact", "Stocky", "LeanTall", "Tall", "Male_Athletic", "Male_Lean", "Female_Athletic", "Female_Strong"]
EAL = unreal.EditorAssetLibrary
Belt = unreal.OpenStanceBeltChainLibrary
log_f = open(OUT + ".txt", "w", encoding="utf-8")


def log(*a):
    msg = " ".join(str(x) for x in a)
    log_f.write(msg + "\n")
    log_f.flush()
    unreal.log(f"[belt_chain_targets] {msg}")


def bones(mesh):
    out = {}
    for row in Belt.list_bones(mesh):
        name, parent, x, y, z = row.split("|")
        out[name] = (parent, (float(x), float(y), float(z)))
    return out


def import_target(path, folder, name):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("automated_import_should_detect_type", False)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def check(kind, sub, outfit, keep):
    tag = f"{kind}{'_VNeck' if sub else ''}_{outfit}"
    stem = f"OpenStance_{kind}" + ("_Sparring" if outfit == "Sparring" else "")
    fbx = f"{ROOT}/{kind}{'/' + sub if sub else ''}/{stem}.fbx"
    folder = f"{TEST}/{tag}"
    row = {"tag": tag, "fbx": fbx}
    imported = import_target(fbx, folder, f"SK_{tag}")
    row["imported"] = [p.split(".")[0].split("/")[-1] for p in imported]
    mesh = EAL.load_asset(f"{folder}/SK_{tag}")
    if mesh is None:
        row["error"] = "no skeletal mesh imported"
        return row
    target = bones(mesh)
    ref_name = "MH_FighterBase" if kind == "Medium" else f"MH_Fighter{kind}"
    ref_mesh = EAL.load_asset(f"/Game/Characters/Fighters/Export/{ref_name}_Body")
    if ref_mesh is None:
        row["comparison_unavailable"] = "No corresponding imported project body; target import alone is not a compatibility pass."
        row["bones"] = len(target)
        chain = [n for n in target if n.startswith("belt_")]
        row["chain_bones"] = len(chain)
        row["chain_parents_ok"] = len(chain) == 16 and all(
            target[n][0] == ("pelvis" if n.endswith("_01") else n[:-2] + f"{int(n[-2:]) - 1:02d}") for n in chain)
        if not keep:
            EAL.delete_directory(folder)
        return row
    ref = bones(ref_mesh)
    row["bones"] = len(target)
    row["project_body_bones"] = len(ref)
    chain = [n for n in target if n.startswith("belt_")]
    row["chain_bones"] = len(chain)
    row["chain_parents_ok"] = len(chain) == 16 and all(
        target[n][0] == ("pelvis" if n.endswith("_01") else n[:-2] + f"{int(n[-2:]) - 1:02d}") for n in chain)
    shared = [n for n in ref if n in target]
    row["shared_with_project_body"] = len(shared)
    row["project_bones_missing"] = sorted(n for n in ref if n not in target)[:12]
    row["project_bones_missing_count"] = sum(1 for n in ref if n not in target)
    extra = sorted(n for n in target if n not in ref and not n.startswith("belt_"))
    row["extra_non_chain_bones"] = len(extra)
    row["extra_sample"] = extra[:8]
    row["parent_mismatches"] = [(n, ref[n][0], target[n][0]) for n in shared if ref[n][0] != target[n][0]][:8]
    dev = [max(abs(a - b) for a, b in zip(ref[n][1], target[n][1])) for n in shared]
    row["max_rest_deviation_cm"] = round(max(dev), 3) if dev else None
    row["mean_rest_deviation_cm"] = round(sum(dev) / len(dev), 3) if dev else None
    row["materials"] = len(mesh.get_editor_property("materials"))
    if not keep:
        EAL.delete_directory(folder)
    return row


try:
    args = [a for a in sys.argv[1:] if a != "quit"]
    kinds = [a for a in args if a in KINDS] or KINDS
    rows = []
    for kind in kinds:
        for sub in ([""] + (["WhiteVNeck"] if "vneck" in args else [])):
            for outfit in ("Dobok", "Sparring"):
                try:
                    row = check(kind, sub, outfit, "keep" in args)
                except Exception:
                    row = {"tag": f"{kind}/{sub}/{outfit}", "error": traceback.format_exc()[-400:]}
                rows.append(row)
                log(json.dumps(row))
                # Preserve completed checks if a later importer stalls or crashes.
                with open(OUT + ".json", "w") as checkpoint:
                    json.dump(rows, checkpoint, indent=1)
    json.dump(rows, open(OUT + ".json", "w"), indent=1)
    if "keep" not in args:
        EAL.delete_directory(TEST)
    log("DONE", len(rows), "targets")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    log_f.close()
    if "quit" in sys.argv[1:]:
        unreal.SystemLibrary.quit_editor()
