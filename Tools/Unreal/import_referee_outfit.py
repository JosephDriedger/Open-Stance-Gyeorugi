"""Import the referee uniforms onto each referee MetaHuman and put them on.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/import_referee_outfit.py"            whole roster
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/import_referee_outfit.py" Kelvin     one referee

Prerequisites: create_referee.py, then run("build_referee_outfit", REFEREE=<P>) in Blender.
Outputs
  /Game/Characters/Officials/Materials/M_OfficialCloth, MI_Ref*          shared uniform materials
  /Game/Characters/Officials/Outfits/<P>/SK_Referee_<Part>                 meshes on the MetaHuman body skeleton
  /Game/Characters/Officials/Outfits/<P>/WI_Referee_<Part>                 wardrobe items (SkeletalMesh slot,
                                                                            body hidden face maps)
Each item is added to and selected on MH_Referee_<P>, so the referee is dressed when opened or assembled.
Each uniform is fitted to its own referee's body; don't mix them between referees.
"""
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
LOG = f"{REPO}/Saved/Logs/import_referee_outfit.txt"
SRC = f"{REPO}/Resources/Models/Referee"
OFFICIALS = "/Game/Characters/Officials"
ROSTER = ["Kelvin", "Bo", "Jorge", "Omari", "Walter", "Vivian"]
PARTS = ["Shirt", "Tie", "Trousers", "Belt", "Shoes"]
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
_log = open(LOG, "w", encoding="utf-8")


def log(*a):
    msg = " ".join(str(x) for x in a)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[import_referee_outfit] {msg}")


def srgb(r, g, b):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return unreal.LinearColor(lin(r), lin(g), lin(b), 1.0)


def import_task(filename, dest, name, options=None):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = filename, dest, name
    t.automated, t.replace_existing, t.save = True, True, True
    if options:
        t.options = options
    tools.import_asset_tasks([t])
    return EAL.load_asset(f"{dest}/{name}")


def build_materials():
    path = f"{OFFICIALS}/Materials/M_OfficialCloth"
    if EAL.does_asset_exist(path):
        m = EAL.load_asset(path)
        MEL.delete_all_material_expressions(m)
    else:
        m = tools.create_asset("M_OfficialCloth", f"{OFFICIALS}/Materials", unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, -100)
    c.set_editor_property("parameter_name", "Color")
    r = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 100)
    r.set_editor_property("parameter_name", "Roughness")
    r.set_editor_property("default_value", 0.8)
    mt = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 250)
    mt.set_editor_property("parameter_name", "Metallic")
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(mt, "", unreal.MaterialProperty.MP_METALLIC)
    m.set_editor_property("used_with_skeletal_mesh", True)
    m.set_editor_property("two_sided", True)
    MEL.recompile_material(m)
    EAL.save_asset(path)
    looks = {   # colours from Resources/Images/Referee_Ref.png
        "MI_RefShirt": (srgb(158, 188, 228), 0.85, 0.0),
        "MI_RefTie": (srgb(24, 36, 82), 0.55, 0.0),
        "MI_RefTrousers": (srgb(206, 196, 172), 0.9, 0.0),
        "MI_RefBelt": (srgb(98, 58, 32), 0.45, 0.0),
        "MI_RefBuckle": (srgb(190, 190, 185), 0.3, 1.0),
        "MI_RefShoe": (srgb(236, 236, 234), 0.6, 0.0),
        "MI_RefSole": (srgb(218, 216, 210), 0.8, 0.0),
    }
    out = {}
    for name, (col, rough, metal) in looks.items():
        p = f"{OFFICIALS}/Materials/{name}"
        mi = EAL.load_asset(p) if EAL.does_asset_exist(p) else tools.create_asset(
            name, f"{OFFICIALS}/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, m)
        MEL.set_material_instance_vector_parameter_value(mi, "Color", col)
        MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", metal)
        EAL.save_asset(p)
        out[name] = mi
    return out


def set_pipeline(item):
    """Runtime pipeline outer = item, editor pipeline outer = runtime pipeline (see import_fighter_gear.py)."""
    pipeline = item.get_editor_property("pipeline")
    if pipeline is None:
        pipeline = unreal.new_object(unreal.MetaHumanSkeletalMeshPipeline, outer=item)
        item.set_editor_property("pipeline", pipeline)
    if pipeline.get_editor_property("editor_pipeline") is None:
        cls = unreal.load_class(None, "/Script/MetaHumanDefaultEditorPipeline.MetaHumanSkeletalMeshEditorPipeline")
        pipeline.set_editor_property("editor_pipeline", unreal.new_object(cls, outer=pipeline))
    return pipeline.get_editor_property("editor_pipeline")


def import_referee(preset, mats):
    dest = f"{OFFICIALS}/Outfits/{preset}"
    body = EAL.load_asset(f"{OFFICIALS}/Export/MH_Referee_{preset}_Body")
    skeleton = body.get_editor_property("skeleton")
    character = EAL.load_asset(f"{OFFICIALS}/MH_Referee_{preset}")
    collection = character.get_editor_property("internal_collection")
    for part in PARTS:
        fbx = f"{SRC}/{preset}/SK_Referee_{part}.fbx"
        ui = unreal.FbxImportUI()
        ui.import_mesh, ui.import_as_skeletal = True, True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        ui.skeleton = skeleton
        ui.import_materials, ui.import_textures, ui.import_animations = False, False, False
        ui.create_physics_asset = False
        mesh = import_task(fbx, dest, f"SK_Referee_{part}", ui)
        if mesh is None:
            log("FAILED", preset, part)
            continue
        slots = []
        for slot in mesh.get_editor_property("materials"):
            name = str(slot.get_editor_property("material_slot_name")).split(".")[0]
            if name in mats:
                slot.set_editor_property("material_interface", mats[name])
            slots.append(slot)
        mesh.set_editor_property("materials", slots)
        EAL.save_asset(mesh.get_path_name())

        item_path = f"{dest}/WI_Referee_{part}"
        existed = EAL.does_asset_exist(item_path)
        item = EAL.load_asset(item_path) if existed else tools.create_asset(
            f"WI_Referee_{part}", dest, unreal.MetaHumanWardrobeItem, unreal.MetaHumanWardrobeItemFactory())
        editor = set_pipeline(item)
        ref = unreal.EditorOnlyAssetReference()
        ref.set_editor_property("asset", mesh)
        item.set_editor_property("principal_asset", ref)
        item.set_editor_property("thumbnail_name", unreal.Text(part))
        png = f"{SRC}/{preset}/T_HFM_{part}.png"
        if os.path.exists(png):
            tex = import_task(png, f"{dest}/HiddenFaceMaps", f"T_HFM_{part}")
            tex.set_editor_property("srgb", False)
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
            tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            EAL.save_asset(tex.get_path_name())
            hfm = unreal.HiddenFaceMapTexture()
            hfm.set_editor_property("Texture", tex)
            editor.set_editor_property("BodyHiddenFaceMapTexture", hfm)   # native name: class not exposed to Python
        EAL.save_asset(item_path, only_if_is_dirty=False)
        if not existed:
            key = collection.try_add_item_from_wardrobe_item("SkeletalMesh", item)
            if key is not None:
                collection.default_instance.try_add_slot_selection(
                    unreal.MetaHumanPipelineSlotSelection(slot_name="SkeletalMesh", selected_item=key))
        log(preset, part, "mesh + wardrobe item", "updated" if existed else "added and worn")
    # presets come dressed in MetaHuman's default T-shirt/shorts (Outfits slot); the uniform replaces it
    collection.default_instance.set_single_slot_selection("Outfits", unreal.MetaHumanPaletteItemKey())
    EAL.save_asset(character.get_path_name(), only_if_is_dirty=False)


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX false")
    mats = build_materials()
    for preset in (sys.argv[1:] or ROSTER):
        import_referee(preset, mats)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
