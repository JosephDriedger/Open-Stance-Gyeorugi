"""Chaos cloth physics on the garments that should move (C++ helper: Source/OpenStanceEditorTools).

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/setup_cloth.py"

Run after import_fighter_gear.py / import_referee_outfit.py (re-importing a mesh drops its cloth).
Each rule pins the garment where it is held (knot, belt, waistband) and lets it move lower down,
with Max Distance fading in between; collisions come from the character's body physics asset.

  Fighter:  belt tails swing, jacket skirt below the belt sways, pant hems flap
  Referee:  tie swings from the knot, trouser legs move below the knee
  Rigid (skinned only): chest protector, helmet, gloves, foot guards, belt band, shirt, shoes
"""
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
LOG = f"{REPO}/Saved/Logs/setup_cloth.txt"
EAL = unreal.EditorAssetLibrary
Cloth = unreal.OpenStanceClothLibrary
ROSTER = ["Kelvin", "Bo", "Jorge", "Omari", "Walter", "Vivian"]
FALLBACK_PHYS = "/MetaHumanCharacter/Body/IdentityTemplate/PHYS_Body"
BIG = 1.0e5

_log = open(LOG, "w", encoding="utf-8")


def log(*a):
    msg = " ".join(str(x) for x in a)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[setup_cloth] {msg}")


def body_physics(body_mesh_path):
    body = EAL.load_asset(body_mesh_path)
    phys = body.get_editor_property("physics_asset") if body else None
    return phys or EAL.load_asset(FALLBACK_PHYS)


def z_range(mesh):
    b = mesh.get_bounds()
    return b.origin.z - b.box_extent.z, b.origin.z + b.box_extent.z


def cloth(path, phys, pin_z, free_z, max_cm, box_min=(-BIG, -BIG, -BIG), box_max=(BIG, BIG, BIG), section=0):
    mesh = EAL.load_asset(path)
    if mesh is None:
        log("missing", path)
        return
    result = Cloth.setup_section_cloth(mesh, section, phys, pin_z, free_z, max_cm,
                                       unreal.Vector(*box_min), unreal.Vector(*box_max))
    EAL.save_asset(path, only_if_is_dirty=False)
    log(path.split("/")[-1], f"pin z {pin_z:.1f} free z {free_z:.1f} max {max_cm} cm ->", result, "|", Cloth.describe_cloth(mesh))


try:
    # --- fighter (dobok) ---
    gear = "/Game/Characters/Fighters/Gear"
    phys = body_physics("/Game/Characters/Fighters/Export/MH_FighterBase_Body")
    belt_lo, belt_hi = z_range(EAL.load_asset(f"{gear}/SK_Fighter_Belt"))
    band_bottom = belt_hi - 7.0
    # belt: band stays on the waist, the knot tails (front, below the band) swing
    cloth(f"{gear}/SK_Fighter_Belt", phys, band_bottom, belt_lo, 10.0, box_min=(-25, -BIG, -BIG), box_max=(25, BIG, BIG))
    jacket_lo, _ = z_range(EAL.load_asset(f"{gear}/SK_Fighter_Jacket"))
    # jacket: only the skirt below the belt, within the torso width (sleeves stay skinned in A-pose)
    # (pinned from the bottom of the belt band: the belt tails hang lower than the jacket hem)
    cloth(f"{gear}/SK_Fighter_Jacket", phys, band_bottom - 2.0, jacket_lo, 4.0, box_min=(-24, -BIG, -BIG), box_max=(24, BIG, BIG))
    pants_lo, pants_hi = z_range(EAL.load_asset(f"{gear}/SK_Fighter_Pants"))
    cloth(f"{gear}/SK_Fighter_Pants", phys, pants_lo + 0.30 * (pants_hi - pants_lo), pants_lo, 3.0)

    # --- referees ---
    for p in ROSTER:
        base = f"/Game/Characters/Officials/Outfits/{p}"
        phys = body_physics(f"/Game/Characters/Officials/Export/MH_Referee_{p}_Body")
        tie_lo, tie_hi = z_range(EAL.load_asset(f"{base}/SK_Referee_Tie"))
        cloth(f"{base}/SK_Referee_Tie", phys, tie_hi - 0.18 * (tie_hi - tie_lo), tie_lo, 12.0)
        tr_lo, tr_hi = z_range(EAL.load_asset(f"{base}/SK_Referee_Trousers"))
        cloth(f"{base}/SK_Referee_Trousers", phys, tr_lo + 0.45 * (tr_hi - tr_lo), tr_lo + 0.02 * (tr_hi - tr_lo), 2.5)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
