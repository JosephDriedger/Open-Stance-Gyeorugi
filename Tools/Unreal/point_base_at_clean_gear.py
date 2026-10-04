"""Point the Medium fighter (MH_FighterBase) at the clean gear in /Game/Characters/Fighters/Gear/Medium/.

    UnrealEditor-Cmd.exe OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecutePythonScript="D:/Open-Stance-Gyeorugi/Tools/Unreal/point_base_at_clean_gear.py"

Adds the Medium wardrobe items to the character's collection, replaces its SkeletalMesh selection (the old
Meshy-based gear in Gear/) with them, saves the character, and logs the result to
Saved/Logs/point_base_at_clean_gear.txt. MH_FighterBase.uasset is a Perforce file: it must be writable (checked
out) before this runs.
"""
import traceback

import unreal

LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/point_base_at_clean_gear.txt"
CHARACTER = "/Game/Characters/Fighters/MH_FighterBase"
GEAR = "/Game/Characters/Fighters/Gear/Medium"
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
o = open(LOG, "w", encoding="utf-8")


def w(*a):
    o.write(" ".join(str(x) for x in a) + "\n")
    o.flush()


try:
    EAL = unreal.EditorAssetLibrary
    ch = EAL.load_asset(CHARACTER)
    col = ch.get_editor_property("internal_collection")
    inst = col.default_instance
    w("before:", [str(col.get_item_display_name(k)) for k in col.get_item_keys_for_slot("SkeletalMesh")])

    keys = []
    for p in PARTS:
        item = EAL.load_asset(f"{GEAR}/WI_Fighter_{p}")
        if item is None:
            raise RuntimeError(f"missing {GEAR}/WI_Fighter_{p}")
        k = col.try_add_item_from_wardrobe_item("SkeletalMesh", item)
        if k is None:
            found = col.get_item_keys_for_wardrobe_item(item)
            k = found[0] if found else None
        if k is None:
            raise RuntimeError(f"could not add {p}")
        keys.append((p, k))
    w("added keys:", [(p, str(k)) for p, k in keys])

    def sel(k):
        return unreal.MetaHumanPipelineSlotSelection(slot_name="SkeletalMesh", selected_item=k)

    inst.set_single_slot_selection("SkeletalMesh", keys[0][1])  # replaces every existing SkeletalMesh selection
    for p, k in keys[1:]:
        ok = inst.try_add_slot_selection(sel(k))
        w("select", p, ok)
    data = inst.get_slot_selection_data()
    w("selection data:", data)
    EAL.save_asset(CHARACTER, only_if_is_dirty=False)
    w("saved", CHARACTER)
    w("DONE")
except Exception:
    w("ERROR", traceback.format_exc())
o.close()
unreal.SystemLibrary.quit_editor()
