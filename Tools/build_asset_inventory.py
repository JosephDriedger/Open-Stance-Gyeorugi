"""Builds Docs/Art_Asset_Inventory.csv, the art asset inventory and production checklist (GDD 15, 18.1, 20).

  py -3 Tools/build_asset_inventory.py

It walks Content/ (Perforce, so only on a machine with it synced) and the tracked source folders and writes one row per
asset. Everything it cannot know from the files is left blank for the team to fill in and is kept when the script is
run again: the columns Revision, Status override, Milestone, Acceptance owner, Review and Usage rights (see MANUAL below)
are copied across from the existing CSV by Unreal path or name. Nothing here claims an asset is missing unless the Gaps
section of Docs/Art_Asset_Inventory.md says why.
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Docs", "Art_Asset_Inventory.csv")

COLUMNS = [
    "Category", "Name", "Type", "Unreal path", "Source path", "Version control", "Revision", "Origin", "Status",
    "Milestone", "Acceptance owner", "Review", "Usage rights", "Notes",
]
MANUAL = ["Revision", "Milestone", "Acceptance owner", "Review", "Usage rights"]

TYPES = [
    ("SK_", "Skeletal mesh"), ("SM_", "Static mesh"), ("MI_", "Material instance"), ("M_", "Material"), ("T_", "Texture"),
    ("WI_", "Wardrobe item"), ("MH_", "MetaHuman character"), ("AS_", "Animation sequence"), ("PA_", "Physics asset"),
    ("L_", "Level"), ("DT_", "Data table"), ("ABP_", "Animation blueprint"), ("AM_", "Animation montage"),
    ("SKEL_", "Skeleton"), ("NS_", "Niagara system"), ("BP_", "Blueprint"),
]


def asset_type(name, ext):
    if ext == ".umap":
        return "Level"
    for prefix, label in TYPES:
        if name.startswith(prefix):
            return label
    return "Asset"


def classify(rel):
    """Category, origin and status from the folder an asset lives in (the pipelines are described in Tools/*/README.md)."""
    p = rel.replace("\\", "/")
    if p.startswith("Characters/Fighters/Gear"):
        return "Fighter gear and wardrobe", "Generated: Tools/Blender fitting, Tools/Unreal import", "Generated"
    if p.startswith("Characters/Fighters/BeltChain"):
        return "Fighter belt", "Generated: Tools/Blender/belt_bone_chain.py", "Generated"
    if p.startswith("Characters/Fighters/Animation"):
        return "Fighter animation", "Generated: Tools/Unreal/create_pose_library.py (hand-keyed, not mocap)", "Generated"
    if p.startswith("Characters/Fighters/Export"):
        return "Fighter export", "Generated: Tools/Unreal export for the Blender refit", "Generated (working)"
    if p.startswith("Characters/Fighters"):
        return "Fighter characters", "MetaHuman Creator, built by Tools/Unreal/create_base_fighter.py", "Generated"
    if p.startswith("Characters/Officials/Outfits"):
        return "Referee outfits", "Generated: Tools/Blender/build_referee_outfit.py", "Generated"
    if p.startswith("Characters/Officials/Export"):
        return "Referee export", "Generated: Tools/Unreal export", "Generated (working)"
    if p.startswith("Characters/Officials"):
        return "Referees", "MetaHuman presets, built by Tools/Unreal/create_referee.py", "Generated"
    if p.startswith("Environment/Meshes"):
        return "Environment meshes", "Generated: Tools/Blender environment scripts", "Generated"
    if p.startswith("Environment/Textures"):
        return "Environment textures", "Generated: Tools/Environment procedural generator", "Generated"
    if p.startswith("Environment/Materials"):
        return "Environment materials", "Generated: Tools/Unreal environment build", "Generated"
    if p.startswith("Maps"):
        return "Levels", "Built by Tools/Unreal/build_arenas.py and build_menu_level.py", "Generated"
    if p.startswith("Combat"):
        return "Combat data", "Built by Tools/Unreal/create_move_data_table.py from Data/Combat/DT_MoveData.csv", "Test data (placeholder tuning)"
    return "Other", "", ""


def read_existing():
    existing = {}
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["Unreal path"] or row["Name"]] = row
    return existing


def source_index():
    """Resources/Environment files by stem, so a mesh or texture can point at its source."""
    index = {}
    for base in ("Environment/Meshes", "Environment/Textures"):
        folder = os.path.join(ROOT, "Resources", base)
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                index[os.path.splitext(name)[0]] = "Resources/" + base + "/" + name
    return index


def main():
    existing = read_existing()
    sources = source_index()
    rows = []

    content = os.path.join(ROOT, "Content")
    if os.path.isdir(content):
        for folder, _, files in os.walk(content):
            for file in sorted(files):
                name, ext = os.path.splitext(file)
                if ext not in (".uasset", ".umap"):
                    continue
                rel = os.path.relpath(os.path.join(folder, file), content)
                if rel.replace("\\", "/").startswith(("Developers/", "Collections/")):
                    continue  # per-user editor data, not project assets
                category, origin, status = classify(rel)
                game_path = "/Game/" + os.path.splitext(rel)[0].replace("\\", "/")
                rows.append({
                    "Category": category, "Name": name, "Type": asset_type(name, ext), "Unreal path": game_path,
                    "Source path": sources.get(name, ""), "Version control": "Perforce", "Origin": origin, "Status": status,
                    "Notes": "",
                })

    # Things that are not Unreal assets but are inventoried art: source folders, menu art, fonts, reference sheets.
    extras = [
        ("Fighter source", "Resources/Models", "Folder", "", "Resources/Models/", "Git (generated studies ignored)",
         "Fighter and MetaHuman FBX, fitted gear, referee outfits, MotionBuilder test character", "Generated"),
        ("Fighter source", "Mocap test character", "FBX", "", "Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx", "Git",
         "Characterized MotionBuilder target built by Tools/MotionBuilder; preparation, not captured motion", "Test asset"),
        ("Environment source", "Resources/Environment", "Folder", "", "Resources/Environment/", "Git", "Environment meshes and textures", "Generated"),
        ("Reference art", "Fighter, ring, referee and dojang reference images", "PNG", "", "Resources/References/", "Git", "Concept references", "Reference"),
        ("UI", "Menu prototype and screenshots", "HTML and PNG", "", "Docs/Prototype/", "Git", "Clickable prototype and per-screen captures the C++ menu was ported from", "Prototype"),
        ("UI", "Controller glyphs and stick-motion icons", "Code", "", "Source/OpenStance/Public/Menu/Slate/SOpenStanceArt.h", "Git",
         "Drawn in C++ (SOpenStanceGestureIcon and related); no texture files", "Generated"),
        ("UI", "Menu art (title, fighter portraits, venue pictures)", "Code", "", "Source/OpenStance/Private/Menu/Slate/SOpenStanceArt.cpp", "Git",
         "Drawn in C++", "Placeholder"),
        ("Fonts", "Roboto family (Regular, Medium, Bold, Bold Condensed and Italic)", "TTF", "", "Source/OpenStance/Private/Menu/OpenStanceMenuTheme.cpp", "Engine content",
         "Loaded from the engine's own fonts by the menu theme", "Engine"),
        ("Mocap", "Mocap shot list", "Document", "", "Docs/Open_Stance_Mocap_Shot_List.docx", "Git",
         "The capture plan; recording-day steps in Docs/Mocap_Record.md, limited test in Docs/Mocap_Test.md", "Plan"),
        ("Audio", "Audio recording list", "Document", "", "Docs/Open_Stance_Audio_Recording_List.docx", "Git",
         "The voice and effects recording plan; no audio assets exist yet", "Plan"),
    ]
    for category, name, kind, game_path, source, vc, notes, status in extras:
        rows.append({"Category": category, "Name": name, "Type": kind, "Unreal path": game_path, "Source path": source,
                     "Version control": vc, "Origin": "", "Status": status, "Notes": notes})

    for row in rows:
        old = existing.get(row["Unreal path"] or row["Name"], {})
        for column in COLUMNS:
            row.setdefault(column, "")
        for column in MANUAL:
            row[column] = old.get(column, "")

    rows.sort(key=lambda r: (r["Category"], r["Unreal path"], r["Name"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row["Category"]] = counts.get(row["Category"], 0) + 1
    print("%d rows -> %s" % (len(rows), OUT))
    for category in sorted(counts):
        print("  %-28s %d" % (category, counts[category]))


if __name__ == "__main__":
    sys.exit(main())
