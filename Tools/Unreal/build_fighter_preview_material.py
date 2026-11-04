"""Make the UI material the menu's fighter portraits draw with (SOpenStanceFighterRender).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/build_fighter_preview_material.py"

/Game/Menu/FighterPreview/M_FighterPreview: a user-interface material that shows the studio's colour capture (texture
parameter Color) where its depth capture (texture parameter Depth, scene depth in cm) hit the fighter, and is clear
elsewhere, so the fighter stands on the menu panel with no backdrop. Replaces the asset if it exists. Also logs the body
meshes the studio uses. Log: Saved/Logs/build_fighter_preview_material.txt.
"""
import traceback

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
PATH = "/Game/Menu/FighterPreview/M_FighterPreview"
DEPTH_CUTOFF = 10000.0  # cm: the studio camera is a few metres from the fighter; empty pixels read as far plane
LOG = open("D:/Open-Stance-Gyeorugi/Saved/Logs/build_fighter_preview_material.txt", "w")


def log(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n")
    LOG.flush()


try:
    if EAL.does_asset_exist(PATH):
        EAL.delete_asset(PATH)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    m = tools.create_asset("M_FighterPreview", "/Game/Menu/FighterPreview", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_UI)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)

    color = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -100)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    depth = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 200)
    depth.set_editor_property("parameter_name", "Depth")
    depth.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    # A texture parameter needs a default texture of a matching type or the material does not compile (it then draws
    # nothing): an sRGB one for Color, a linear one for Depth.
    defaults = {True: None, False: None}
    for candidate in ("/Engine/EngineResources/DefaultTexture", "/Engine/EngineResources/WhiteSquareTexture",
                      "/Engine/EngineResources/Black", "/Engine/EngineMaterials/DefaultWhiteGrid",
                      "/Engine/EngineMaterials/BlackSquareTexture", "/Engine/EngineResources/DefaultTextureCube",
                      "/Engine/EngineMaterials/DefaultDiffuse", "/Engine/EngineMaterials/T_Default_Material_Grid_M",
                      "/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq", "/Engine/EngineMaterials/DefaultNormal"):
        tex = EAL.load_asset(candidate)
        if isinstance(tex, unreal.Texture2D):
            srgb = tex.get_editor_property("srgb")
            log("default candidate", candidate, "srgb", srgb, tex.get_editor_property("compression_settings"))
            if defaults[srgb] is None and tex.get_editor_property("compression_settings") in (unreal.TextureCompressionSettings.TC_DEFAULT, unreal.TextureCompressionSettings.TC_MASKS, unreal.TextureCompressionSettings.TC_GRAYSCALE):
                defaults[srgb] = tex
    log("defaults", defaults)
    color.set_editor_property("texture", defaults[True])
    depth.set_editor_property("texture", defaults[False])
    if defaults[False] is not None and defaults[False].get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_MASKS:
        depth.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    cutoff = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 450)
    cutoff.set_editor_property("parameter_name", "DepthCutoff")
    cutoff.set_editor_property("default_value", DEPTH_CUTOFF)
    # opacity = depth < cutoff ? 1 : 0, as saturate(cutoff - depth)
    sub = MEL.create_material_expression(m, unreal.MaterialExpressionSubtract, -300, 300)
    MEL.connect_material_expressions(cutoff, "", sub, "A")
    MEL.connect_material_expressions(depth, "R", sub, "B")
    sat = MEL.create_material_expression(m, unreal.MaterialExpressionSaturate, -150, 300)
    MEL.connect_material_expressions(sub, "", sat, "")
    MEL.connect_material_property(color, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(sat, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m)
    log("compile", "shader instructions", MEL.get_statistics(m).num_pixel_shader_instructions if hasattr(MEL, "get_statistics") else "?")
    EAL.save_asset(PATH, only_if_is_dirty=False)
    log("material", PATH, "saved")

    for stem in ("MH_FighterCompact", "MH_FighterLeanTall", "MH_FighterStocky", "MH_FighterTall", "MH_FighterBase"):
        for part in ("Body", "Head", "FullBody"):
            mesh = EAL.load_asset(f"/Game/Characters/Fighters/Export/{stem}_{part}")
            if not mesh:
                log(stem, part, "missing")
                continue
            b = mesh.get_bounds()
            log(stem, part, type(mesh).__name__, mesh.get_editor_property("skeleton").get_path_name() if isinstance(mesh, unreal.SkeletalMesh) else "",
                "height %.1f" % (b.box_extent.z * 2), "origin z %.1f" % b.origin.z)
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    LOG.close()
    unreal.SystemLibrary.quit_editor()
