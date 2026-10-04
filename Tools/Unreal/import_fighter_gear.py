"""Import the fitted dobok and sparring gear into Unreal and add it to the base fighter MetaHuman.

Prerequisites: create_base_fighter.py, then Tools/Blender/fit_to_body.py for MH_FighterBase_Body.

Clean gear (Tools/Blender/build_clean_gear.py), every body type: set OPEN_STANCE_BODY_TYPE to Medium,
Compact, Stocky, LeanTall or Tall (Medium is the base fighter, MH_FighterBase). Meshes, wardrobe items and
hidden face maps go to /Game/Characters/Fighters/Gear/<Type>/ and are selected on the type's MetaHuman
character. The shared material, instances and textures live in Gear/Clean/ and are built on first use.
All of it is add-only: assets from the earlier Meshy-based gear (Gear/ root) are never touched.

Outputs (under /Game/Characters/Fighters/Gear)
  Textures/T_Fighter_BaseColor, Textures/T_Fighter_Masks
  M_FighterGear             recolour master material (rules: Docs/Character_Customization.md)
  MI_FighterGear_Chung      TeamSide 0 (blue, baked texture)
  MI_FighterGear_Hong       TeamSide 1 (fixed red #C8102E)
  SK_Fighter_<Part>         skeletal meshes on the MetaHuman body skeleton
  WI_Fighter_<Part>         MetaHuman wardrobe items (SkeletalMesh slot)
and selects every wardrobe item on /Game/Characters/Fighters/MH_FighterBase.
"""
import os
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
TYPE = os.environ.get("OPEN_STANCE_BODY_TYPE", "")   # "" = the original Meshy gear in Gear/ (legacy)
LOG = f"{REPO}/Saved/Logs/import_fighter_gear{'_' + TYPE if TYPE else ''}.txt"
FITTED = f"{REPO}/Resources/Models/Fitted/MH_FighterBase_Body"
TEXTURES = f"{REPO}/Resources/Models/Textures"
GEAR = "/Game/Characters/Fighters/Gear"
CHARACTER = "/Game/Characters/Fighters/MH_FighterBase"
BODY_MESH = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
PART_DIR = GEAR        # where this body's meshes, wardrobe items and hidden face maps live
SHARED = GEAR          # shared material, instances and textures
if TYPE:
    asset = "MH_FighterBase" if TYPE == "Medium" else f"MH_Fighter{TYPE}"
    FITTED = f"{REPO}/Resources/Models/Fitted/{asset}_Body"
    CHARACTER = f"/Game/Characters/Fighters/{asset}"
    BODY_MESH = f"/Game/Characters/Fighters/Export/{asset}_Body"
    PART_DIR = f"{GEAR}/{TYPE}"
    SHARED = f"{GEAR}/Clean"
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
GEAR_PARTS = {"Helmet", "Protector", "Gloves", "FootGuards"}   # removed for menu / career views

# Reference luminance per masked region, measured by Tools/Blender/preview_material.py
REF_TEAM, REF_BELT, REF_COLLAR = 0.0559, 0.0036, 0.0281
HONG_RED = unreal.LinearColor(0.578, 0.0052, 0.0273, 1.0)   # sRGB #C8102E in linear

os.makedirs(os.path.dirname(LOG), exist_ok=True)
_log = open(LOG, "w", encoding="utf-8")


def log(*args):
    msg = " ".join(str(a) for a in args)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[import_fighter_gear] {msg}")


tools = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary


def import_file(filename, dest_path, dest_name, options=None):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    tools.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    log("import", filename, "->", paths)
    return EAL.load_asset(f"{dest_path}/{dest_name}")


def set_skeletal_mesh_pipeline(item):
    """Give a wardrobe item the SkeletalMesh item pipeline (required by Creator's validation).

    Both pipelines must be subobjects: runtime pipeline outer = item, editor pipeline outer =
    runtime pipeline (UMetaHumanItemEditorPipeline::GetRuntimePipeline casts its outer). If the
    editor pipeline is left unset, the CDO is used and assembly crashes.
    """
    pipeline = unreal.new_object(unreal.MetaHumanSkeletalMeshPipeline, outer=item)
    item.set_editor_property("pipeline", pipeline)
    if pipeline.get_editor_property("editor_pipeline") is None:
        editor_cls = unreal.load_class(None, "/Script/MetaHumanDefaultEditorPipeline.MetaHumanSkeletalMeshEditorPipeline")
        pipeline.set_editor_property("editor_pipeline", unreal.new_object(editor_cls, outer=pipeline))
    editor = pipeline.get_editor_property("editor_pipeline")
    log("pipeline", item.get_name(), pipeline.get_path_name(), "editor", editor.get_path_name() if editor else None)
    return pipeline


def set_hidden_face_map(item, part):
    """Body hidden face map (Tools/Blender/hidden_face_maps.py): body triangles under the garment are
    removed while it's worn, so skin can't poke through when animation bends the body."""
    png = f"{FITTED}/T_HFM_{part}.png"
    if not os.path.exists(png):
        return
    tex = import_file(png, f"{PART_DIR}/HiddenFaceMaps", f"T_HFM_{part}")
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    EAL.save_asset(f"{PART_DIR}/HiddenFaceMaps/T_HFM_{part}")
    editor = item.get_editor_property("pipeline").get_editor_property("editor_pipeline")
    hfm = unreal.HiddenFaceMapTexture()
    hfm.set_editor_property("Texture", tex)
    # UMetaHumanSkeletalMeshEditorPipeline isn't exposed to Python as its own type, so its
    # properties are only reachable by their native (CamelCase) names.
    editor.set_editor_property("BodyHiddenFaceMapTexture", hfm)
    check = editor.get_editor_property("BodyHiddenFaceMapTexture").get_editor_property("Texture")
    log("hidden face map", item.get_name(), check.get_path_name() if check else "NOT SET")


def expr(material, cls, x, y, **props):
    e = MEL.create_material_expression(material, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def build_material(base_tex, mask_tex, surf_tex, weave_tex):
    path = f"{SHARED}/M_FighterGear"
    if EAL.does_asset_exist(path):
        # Rebuild in place (instances and meshes reference it, so don't delete)
        m = EAL.load_asset(path)
        MEL.delete_all_material_expressions(m)
    else:
        m = tools.create_asset("M_FighterGear", SHARED, unreal.Material, unreal.MaterialFactoryNew())

    base = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, -200, parameter_name="BaseColor", texture=base_tex)
    masks = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 300, parameter_name="Masks", texture=mask_tex,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    lum_w = expr(m, unreal.MaterialExpressionConstant3Vector, -1400, -450, constant=unreal.LinearColor(0.2126, 0.7152, 0.0722, 1))
    lum = expr(m, unreal.MaterialExpressionDotProduct, -1100, -350)
    MEL.connect_material_expressions(base, "RGB", lum, "A")
    MEL.connect_material_expressions(lum_w, "", lum, "B")

    def tint(color_expr, ref_name, ref_default, detail, y):
        ref = expr(m, unreal.MaterialExpressionScalarParameter, -900, y + 80, parameter_name=ref_name, default_value=ref_default)
        div = expr(m, unreal.MaterialExpressionDivide, -700, y)
        MEL.connect_material_expressions(lum, "", div, "A")
        MEL.connect_material_expressions(ref, "", div, "B")
        cap = expr(m, unreal.MaterialExpressionMin, -550, y, const_b=3.0)
        MEL.connect_material_expressions(div, "", cap, "A")
        pw = expr(m, unreal.MaterialExpressionPower, -400, y, const_exponent=detail)
        MEL.connect_material_expressions(cap, "", pw, "Base")
        mul = expr(m, unreal.MaterialExpressionMultiply, -250, y)
        MEL.connect_material_expressions(color_expr, "", mul, "A")
        MEL.connect_material_expressions(pw, "", mul, "B")
        return mul

    # Side colour: Chung is the baked texture; Hong is a fixed red. No free team colour parameter.
    hong = expr(m, unreal.MaterialExpressionConstant3Vector, -900, -700, constant=HONG_RED)
    team_side = expr(m, unreal.MaterialExpressionScalarParameter, -700, -850, parameter_name="TeamSide", default_value=0.0)
    hong_tint = tint(hong, "RefTeam", REF_TEAM, 0.8, -700)
    team_alpha = expr(m, unreal.MaterialExpressionMultiply, -250, -850)
    MEL.connect_material_expressions(masks, "R", team_alpha, "A")
    MEL.connect_material_expressions(team_side, "", team_alpha, "B")
    lerp_team = expr(m, unreal.MaterialExpressionLinearInterpolate, 0, -500)
    MEL.connect_material_expressions(base, "RGB", lerp_team, "A")
    MEL.connect_material_expressions(hong_tint, "", lerp_team, "B")
    MEL.connect_material_expressions(team_alpha, "", lerp_team, "Alpha")

    belt_col = expr(m, unreal.MaterialExpressionVectorParameter, -900, -100, parameter_name="BeltColor",
                    default_value=unreal.LinearColor(0.002, 0.002, 0.002, 1))
    belt_tint = tint(belt_col, "RefBelt", REF_BELT, 0.35, -100)
    lerp_belt = expr(m, unreal.MaterialExpressionLinearInterpolate, 200, -300)
    MEL.connect_material_expressions(lerp_team, "", lerp_belt, "A")
    MEL.connect_material_expressions(belt_tint, "", lerp_belt, "B")
    MEL.connect_material_expressions(masks, "G", lerp_belt, "Alpha")

    collar_col = expr(m, unreal.MaterialExpressionVectorParameter, -900, 350, parameter_name="CollarColor",
                      default_value=unreal.LinearColor(0.002, 0.002, 0.002, 1))
    collar_tint = tint(collar_col, "RefCollar", REF_COLLAR, 0.35, 350)
    lerp_collar = expr(m, unreal.MaterialExpressionLinearInterpolate, 400, -100)
    MEL.connect_material_expressions(lerp_belt, "", lerp_collar, "A")
    MEL.connect_material_expressions(collar_tint, "", lerp_collar, "B")
    MEL.connect_material_expressions(masks, "B", lerp_collar, "Alpha")

    # Surface patch: R = roughness (cotton 0.88, padded vinyl 0.38), G = how much fabric weave shows. The weave
    # normal map tiles on UV1 (1 UV unit = 5 cm of surface, set by Tools/Blender/build_clean_gear.py).
    surf = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 700, parameter_name="Surface", texture=surf_tex,
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    uv1 = expr(m, unreal.MaterialExpressionTextureCoordinate, -1700, 1000, coordinate_index=1)
    weave = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, 1000, parameter_name="WeaveNormal", texture=weave_tex,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_expressions(uv1, "", weave, "UVs")
    flat = expr(m, unreal.MaterialExpressionConstant3Vector, -1100, 900, constant=unreal.LinearColor(0, 0, 1, 1))
    normal = expr(m, unreal.MaterialExpressionLinearInterpolate, -800, 950)
    MEL.connect_material_expressions(flat, "", normal, "A")
    MEL.connect_material_expressions(weave, "RGB", normal, "B")
    MEL.connect_material_expressions(surf, "G", normal, "Alpha")
    MEL.connect_material_property(lerp_collar, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(surf, "R", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)
    m.set_editor_property("used_with_skeletal_mesh", True)
    m.set_editor_property("two_sided", True)   # cloth: sleeve and collar interiors are visible
    MEL.recompile_material(m)
    EAL.save_asset(path)
    log("built", path)
    return m


def make_instance(parent, name, team_side):
    path = f"{SHARED}/{name}"
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else tools.create_asset(
        name, SHARED, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    MEL.set_material_instance_scalar_parameter_value(mi, "TeamSide", float(team_side))
    EAL.save_asset(path)
    log("material instance", path, "TeamSide", team_side)
    return mi


try:
    # Legacy FBX importer so FbxImportUI options (existing skeleton, no materials) apply.
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX false")

    chung_path = f"{SHARED}/MI_FighterGear_Chung"
    if EAL.does_asset_exist(chung_path) and not os.environ.get("OPEN_STANCE_REBUILD_MATERIAL"):
        mi_chung = EAL.load_asset(chung_path)             # shared: built by the first run
    else:
        tex_dir = f"{SHARED}/Textures"
        base_tex = import_file(f"{TEXTURES}/T_Fighter_BaseColor.png", tex_dir, "T_Fighter_BaseColor")
        base_tex.set_editor_property("srgb", True)
        mask_tex = import_file(f"{TEXTURES}/T_Fighter_Masks.png", tex_dir, "T_Fighter_Masks")
        mask_tex.set_editor_property("srgb", False)
        mask_tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        surf_tex = import_file(f"{TEXTURES}/T_Fighter_Surface.png", tex_dir, "T_Fighter_Surface")
        surf_tex.set_editor_property("srgb", False)
        surf_tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        weave_tex = import_file(f"{TEXTURES}/T_Fighter_Weave_N.png", tex_dir, "T_Fighter_Weave_N")
        weave_tex.set_editor_property("srgb", False)
        weave_tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        for name in ("T_Fighter_Masks", "T_Fighter_BaseColor", "T_Fighter_Surface", "T_Fighter_Weave_N"):
            EAL.save_asset(f"{tex_dir}/{name}")

        material = build_material(base_tex, mask_tex, surf_tex, weave_tex)
        mi_chung = make_instance(material, "MI_FighterGear_Chung", 0)
        make_instance(material, "MI_FighterGear_Hong", 1)

    skeleton = EAL.load_asset(BODY_MESH).get_editor_property("skeleton")
    log("body skeleton", skeleton.get_path_name())

    meshes = {}
    for part in PARTS:
        ui = unreal.FbxImportUI()
        ui.import_mesh = True
        ui.import_as_skeletal = True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        ui.skeleton = skeleton
        ui.import_materials = False
        ui.import_textures = False
        ui.import_animations = False
        ui.create_physics_asset = False
        ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
        mesh = import_file(f"{FITTED}/SK_Fighter_{part}.fbx", PART_DIR, f"SK_Fighter_{part}", ui)
        if mesh is None:
            log("FAILED to import", part)
            continue
        # Indexing the array returns a copy of the struct, so rebuild the list
        mats = []
        for slot in mesh.get_editor_property("materials"):
            slot.set_editor_property("material_interface", mi_chung)
            mats.append(slot)
        mesh.set_editor_property("materials", mats)
        bounds = mesh.get_bounds()
        log("mesh", part, "bounds extent (cm)", bounds.box_extent)
        EAL.save_asset(f"{PART_DIR}/SK_Fighter_{part}")
        meshes[part] = mesh
        log("mesh", part, "bones in skeleton", skeleton.get_path_name(), "materials", len(mats))

    # Wardrobe items for MetaHuman Creator (SkeletalMesh slot follows the body)
    character = EAL.load_asset(CHARACTER)
    collection = character.get_editor_property("internal_collection")
    for part, mesh in meshes.items():
        name = f"WI_Fighter_{part}"
        path = f"{PART_DIR}/{name}"
        # Existing items are updated in place: the character's collection references them, and
        # Creator lists them via Config/DefaultMetaHumanCharacter.ini (WardrobePaths).
        existed = EAL.does_asset_exist(path)
        if existed:
            item = EAL.load_asset(path)
        else:
            item = tools.create_asset(name, PART_DIR, unreal.MetaHumanWardrobeItem, unreal.MetaHumanWardrobeItemFactory())
        if item.get_editor_property("pipeline") is None:
            set_skeletal_mesh_pipeline(item)
        set_hidden_face_map(item, part)
        ref = unreal.EditorOnlyAssetReference()
        ref.set_editor_property("asset", mesh)
        item.set_editor_property("principal_asset", ref)
        item.set_editor_property("thumbnail_name", unreal.Text(part))
        EAL.save_asset(path, only_if_is_dirty=False)
        if existed:
            log("wardrobe item", path, "updated")
            continue
        key = collection.try_add_item_from_wardrobe_item("SkeletalMesh", item)
        if key is None:
            log("could not add wardrobe item", name)
            continue
        ok = collection.default_instance.try_add_slot_selection(
            unreal.MetaHumanPipelineSlotSelection(slot_name="SkeletalMesh", selected_item=key))
        log("wardrobe item", path, "selected" if ok else "added (not selected)", "gear" if part in GEAR_PARTS else "dobok")

    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if subsystem.try_add_object_to_edit(character):
        try:
            subsystem.assemble_for_preview(character=character)
            log("assembled preview")
        finally:
            subsystem.remove_object_to_edit(character)
    EAL.save_asset(CHARACTER)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
