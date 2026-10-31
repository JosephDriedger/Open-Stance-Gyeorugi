"""Builds the MoveData table (GDD 16.6) from its reviewed CSV and checks it.

Run headless, no window:
  UnrealEditor-Cmd.exe <project> -unattended -nullrhi -ExecCmds="py .../create_move_data_table.py [seed] [replace] [production] quit"

  seed        first rewrite Data/Combat/DT_MoveData.csv from the moves built into the game module
  replace     overwrite /Game/Combat/DT_MoveData if it exists (default: fill the existing table's rows)
  production  fail on any row still using a placeholder montage

The CSV in Git is the reviewed source of truth; DT_MoveData.uasset is Perforce content (Docs/Combat_Data.md).
Problems are logged to Saved/Logs/create_move_data_table.txt, one per line, "ERROR" or "WARNING" first.
"""
import os
import sys

import unreal

PROJECT_DIR = unreal.Paths.project_dir()
CSV_PATH = os.path.join(PROJECT_DIR, "Data", "Combat", "DT_MoveData.csv").replace("\\", "/")
LOG_PATH = os.path.join(PROJECT_DIR, "Saved", "Logs", "create_move_data_table.txt")
TABLE_DIR = "/Game/Combat"
TABLE_NAME = "DT_MoveData"

lines = []


def log(text):
    lines.append(text)
    unreal.log(text)


def main(args):
    seed = "seed" in args
    replace = "replace" in args
    production = "production" in args

    if seed:
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        if not unreal.OpenStanceMoveDataLibrary.write_seed_csv(CSV_PATH):
            log("ERROR: could not write " + CSV_PATH)
            return 1
        log("Wrote seed moves to " + CSV_PATH)

    if not os.path.exists(CSV_PATH):
        log("ERROR: " + CSV_PATH + " is missing; run with 'seed' first.")
        return 1

    table_path = TABLE_DIR + "/" + TABLE_NAME
    exists = unreal.EditorAssetLibrary.does_asset_exist(table_path)
    if exists and replace:
        unreal.EditorAssetLibrary.delete_asset(table_path)
        exists = False
    if exists:
        table = unreal.EditorAssetLibrary.load_asset(table_path)
    else:
        factory = unreal.DataTableFactory()
        factory.set_editor_property("struct", unreal.OpenStanceMoveRow.static_struct())
        table = unreal.AssetToolsHelpers.get_asset_tools().create_asset(TABLE_NAME, TABLE_DIR, unreal.DataTable, factory)

    if not unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(table, CSV_PATH):
        log("ERROR: CSV import failed; see the editor log for the importer's messages.")
        return 1
    log("Imported %d rows into %s" % (len(unreal.DataTableFunctionLibrary.get_data_table_row_names(table)), table_path))

    issues = unreal.OpenStanceMoveDataLibrary.validate_move_table(table, production, True)
    for issue in issues:
        log(issue)
    errors = [i for i in issues if i.startswith("ERROR")]

    unreal.EditorAssetLibrary.save_asset(table_path)
    log("%d error(s), %d warning(s)" % (len(errors), len(issues) - len(errors)))
    return 1 if errors else 0


try:
    main([a.lower() for a in sys.argv[1:]])
finally:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
