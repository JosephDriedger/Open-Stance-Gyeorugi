"""Build the two sparring venues from the reference images.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/build_arenas.py"              everything
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/build_arenas.py" arena        materials + competition arena only
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/build_arenas.py" dojang       materials + training dojang only

Prerequisites: py Tools/Environment/make_env_textures.py, then run("build_environment_meshes") in Blender.

Outputs
  /Game/Environment/Textures, /Game/Environment/Meshes, /Game/Environment/Materials (M_Env_* + MI_*)
  /Game/Maps/L_CompetitionArena   (Resources/Images/FightingRing_Ref.png)
  /Game/Maps/L_TrainingDojang     (Resources/Images/TrainingDojang_Ref.png)

Real dimensions: WT competition mat = 8 m octagon (flat to flat) inside a 12 m x 12 m square, 1 m tiles.
Layout units below are metres; Unreal is centimetres (M() converts).
"""
import math
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
LOG = f"{REPO}/Saved/Logs/build_arenas.txt"
TEX_SRC = f"{REPO}/Resources/Environment/Textures"
MESH_SRC = f"{REPO}/Resources/Environment/Meshes"
ENV = "/Game/Environment"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

_log = open(LOG, "w", encoding="utf-8")


def log(*a):
    msg = " ".join(str(x) for x in a)
    _log.write(msg + "\n")
    _log.flush()
    unreal.log(f"[build_arenas] {msg}")


def M(v):
    return v * 100.0


def vec(x, y, z):
    return unreal.Vector(M(x), M(y), M(z))


def srgb(r, g, b):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return unreal.LinearColor(lin(r), lin(g), lin(b), 1.0)


def grey(v):
    return unreal.LinearColor(v, v, v, 1.0)


# ------------------------------------------------------------------ import
def import_task(filename, dest, name, options=None):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = filename, dest, name
    t.automated, t.replace_existing, t.save = True, True, True
    if options:
        t.options = options
    tools.import_asset_tasks([t])
    return EAL.load_asset(f"{dest}/{name}")


def import_textures():
    tex = {}
    for fn in sorted(os.listdir(TEX_SRC)):
        if not fn.endswith(".png"):
            continue
        name = fn[:-4]
        t = import_task(f"{TEX_SRC}/{fn}", f"{ENV}/Textures", name)
        if name.endswith("_N"):
            t.set_editor_property("srgb", False)
            t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        elif name.endswith("_H"):
            t.set_editor_property("srgb", False)   # sampled as linear; _D detail maps stay sRGB like the default white
        EAL.save_asset(t.get_path_name())
        tex[name] = t
    log("textures", sorted(tex))
    return tex


def import_meshes():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX false")
    meshes = {}
    for fn in sorted(os.listdir(MESH_SRC)):
        if not fn.endswith(".fbx"):
            continue
        name = fn[:-4]
        ui = unreal.FbxImportUI()
        ui.import_mesh, ui.import_as_skeletal = True, False
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        ui.import_materials, ui.import_textures, ui.import_animations = False, False, False
        ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
        ui.static_mesh_import_data.set_editor_property("auto_generate_collision", True)
        meshes[name] = import_task(f"{MESH_SRC}/{fn}", f"{ENV}/Meshes", name, ui)
    log("meshes", len(meshes))
    return meshes


# ------------------------------------------------------------------ materials
def expr(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def new_material(name):
    path = f"{ENV}/Materials/{name}"
    if EAL.does_asset_exist(path):
        m = EAL.load_asset(path)
        MEL.delete_all_material_expressions(m)
    else:
        m = tools.create_asset(name, f"{ENV}/Materials", unreal.Material, unreal.MaterialFactoryNew())
    return m


def finish_material(m):
    MEL.recompile_material(m)
    EAL.save_asset(m.get_path_name())


def build_surface_material(white):
    """Colour x triplanar world-aligned greyscale detail; roughness/metallic scalars."""
    m = new_material("M_Env_Surface")
    color = expr(m, unreal.MaterialExpressionVectorParameter, -900, -300, parameter_name="Color", default_value=grey(0.5))
    tex = expr(m, unreal.MaterialExpressionTextureObjectParameter, -1500, 100, parameter_name="DetailTex", texture=white)
    size = expr(m, unreal.MaterialExpressionScalarParameter, -1700, -100, parameter_name="DetailSizeCm", default_value=100.0)
    strength = expr(m, unreal.MaterialExpressionScalarParameter, -700, 300, parameter_name="DetailStrength", default_value=0.0)
    wp = expr(m, unreal.MaterialExpressionWorldPosition, -1700, -300)
    uvw = expr(m, unreal.MaterialExpressionDivide, -1500, -300)
    MEL.connect_material_expressions(wp, "", uvw, "A")
    MEL.connect_material_expressions(size, "", uvw, "B")
    nrm = expr(m, unreal.MaterialExpressionVertexNormalWS, -1700, 400)
    absn = expr(m, unreal.MaterialExpressionAbs, -1500, 400)
    MEL.connect_material_expressions(nrm, "", absn, "")
    blend = None
    for i, (mask, weight) in enumerate((((True, True, False), (False, False, True)),     # XY plane, weight Z
                                        ((True, False, True), (False, True, False)),     # XZ plane, weight Y
                                        ((False, True, True), (True, False, False)))):   # YZ plane, weight X
        uv = expr(m, unreal.MaterialExpressionComponentMask, -1300, -400 + i * 150, r=mask[0], g=mask[1], b=mask[2])
        MEL.connect_material_expressions(uvw, "", uv, "")
        s = expr(m, unreal.MaterialExpressionTextureSample, -1100, -400 + i * 150)
        MEL.connect_material_expressions(uv, "", s, "UVs")
        MEL.connect_material_expressions(tex, "", s, "Tex")
        w = expr(m, unreal.MaterialExpressionComponentMask, -1300, 400 + i * 100, r=weight[0], g=weight[1], b=weight[2])
        MEL.connect_material_expressions(absn, "", w, "")
        mul = expr(m, unreal.MaterialExpressionMultiply, -900, -400 + i * 150)
        MEL.connect_material_expressions(s, "R", mul, "A")
        MEL.connect_material_expressions(w, "", mul, "B")
        if blend is None:
            blend = mul
        else:
            add = expr(m, unreal.MaterialExpressionAdd, -800, -350 + i * 150)
            MEL.connect_material_expressions(blend, "", add, "A")
            MEL.connect_material_expressions(mul, "", add, "B")
            blend = add
    one = expr(m, unreal.MaterialExpressionConstant, -700, 150, r=1.0)
    lerp = expr(m, unreal.MaterialExpressionLinearInterpolate, -500, 100)
    MEL.connect_material_expressions(one, "", lerp, "A")
    MEL.connect_material_expressions(blend, "", lerp, "B")
    MEL.connect_material_expressions(strength, "", lerp, "Alpha")
    base = expr(m, unreal.MaterialExpressionMultiply, -300, -200)
    MEL.connect_material_expressions(color, "", base, "A")
    MEL.connect_material_expressions(lerp, "", base, "B")
    rough = expr(m, unreal.MaterialExpressionScalarParameter, -300, 200, parameter_name="Roughness", default_value=0.6)
    metal = expr(m, unreal.MaterialExpressionScalarParameter, -300, 350, parameter_name="Metallic", default_value=0.0)
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    finish_material(m)
    return m


def build_mat_material(tex):
    """EVA puzzle mat: colour, 1 m tile normal map projected top-down in world space."""
    m = new_material("M_Env_Mat")
    color = expr(m, unreal.MaterialExpressionVectorParameter, -600, -300, parameter_name="Color", default_value=grey(0.5))
    wp = expr(m, unreal.MaterialExpressionWorldPosition, -1200, 0)
    mask = expr(m, unreal.MaterialExpressionComponentMask, -1000, 0, r=True, g=True, b=False)
    MEL.connect_material_expressions(wp, "", mask, "")
    div = expr(m, unreal.MaterialExpressionDivide, -800, 0, const_b=100.0)
    MEL.connect_material_expressions(mask, "", div, "A")
    n = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name="TileNormal",
             texture=tex["T_MatTile_N"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_expressions(div, "", n, "UVs")
    h = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 300, parameter_name="TileHeight",
             texture=tex["T_MatTile_H"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    MEL.connect_material_expressions(div, "", h, "UVs")
    shade = expr(m, unreal.MaterialExpressionLinearInterpolate, -300, 200, const_a=0.55, const_b=1.0)
    MEL.connect_material_expressions(h, "R", shade, "Alpha")
    base = expr(m, unreal.MaterialExpressionMultiply, -100, -200)
    MEL.connect_material_expressions(color, "", base, "A")
    MEL.connect_material_expressions(shade, "", base, "B")
    rough = expr(m, unreal.MaterialExpressionScalarParameter, -100, 300, parameter_name="Roughness", default_value=0.55)
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    finish_material(m)
    return m


def build_textured_material(white, emissive):
    """Mesh UV texture (pictures, screens). Emissive variant for screens and light panels."""
    m = new_material("M_Env_Emissive" if emissive else "M_Env_Textured")
    t = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0, parameter_name="Texture", texture=white)
    tint = expr(m, unreal.MaterialExpressionVectorParameter, -700, -250, parameter_name="Color", default_value=grey(1.0))
    mul = expr(m, unreal.MaterialExpressionMultiply, -450, -100)
    MEL.connect_material_expressions(t, "RGB", mul, "A")
    MEL.connect_material_expressions(tint, "", mul, "B")
    if emissive:
        k = expr(m, unreal.MaterialExpressionScalarParameter, -450, 150, parameter_name="Intensity", default_value=5.0)
        em = expr(m, unreal.MaterialExpressionMultiply, -250, 0)
        MEL.connect_material_expressions(mul, "", em, "A")
        MEL.connect_material_expressions(k, "", em, "B")
        MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        black = expr(m, unreal.MaterialExpressionConstant3Vector, -250, -250, constant=grey(0.0))
        MEL.connect_material_property(black, "", unreal.MaterialProperty.MP_BASE_COLOR)
        rough = expr(m, unreal.MaterialExpressionConstant, -250, 300, r=0.25)
    else:
        MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
        rough = expr(m, unreal.MaterialExpressionScalarParameter, -250, 300, parameter_name="Roughness", default_value=0.7)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    finish_material(m)
    return m


def build_glass_material():
    m = new_material("M_Env_Glass")
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("two_sided", True)
    c = expr(m, unreal.MaterialExpressionVectorParameter, -400, -100, parameter_name="Color", default_value=grey(0.8))
    o = expr(m, unreal.MaterialExpressionScalarParameter, -400, 150, parameter_name="Opacity", default_value=0.12)
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(o, "", unreal.MaterialProperty.MP_OPACITY)
    finish_material(m)
    return m


def instance(name, parent, scalars=None, vectors=None, textures=None):
    path = f"{ENV}/Materials/{name}"
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else tools.create_asset(
        name, f"{ENV}/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, v)
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, v)
    EAL.save_asset(path)
    return mi


def build_materials(tex):
    white = EAL.load_asset("/Engine/EngineResources/WhiteSquareTexture")
    surf = build_surface_material(white)
    mat = build_mat_material(tex)
    textured = build_textured_material(white, emissive=False)
    emissive = build_textured_material(white, emissive=True)
    glass = build_glass_material()

    def S(name, color, rough=0.6, metal=0.0, detail=None, size=100.0, strength=0.0):
        t = {"DetailTex": tex[detail]} if detail else None
        return instance(name, surf, {"Roughness": rough, "Metallic": metal, "DetailSizeCm": size, "DetailStrength": strength},
                        {"Color": color}, t)

    mi = {}
    mi["MI_MatBlue"] = instance("MI_MatBlue", mat, {"Roughness": 0.55}, {"Color": srgb(38, 98, 214)})
    mi["MI_MatRed"] = instance("MI_MatRed", mat, {"Roughness": 0.55}, {"Color": srgb(228, 64, 70)})
    mi["MI_TrussMetal"] = S("MI_TrussMetal", grey(0.55), 0.35, 1.0)
    mi["MI_BlackPlastic"] = S("MI_BlackPlastic", grey(0.02), 0.45)
    mi["MI_BlackFabric"] = S("MI_BlackFabric", grey(0.015), 0.9)
    mi["MI_BlackVinyl"] = S("MI_BlackVinyl", grey(0.012), 0.35)
    mi["MI_TableCloth"] = S("MI_TableCloth", grey(0.008), 0.95)
    mi["MI_PlasticBlue"] = S("MI_PlasticBlue", srgb(25, 70, 180), 0.35)
    mi["MI_PlasticRed"] = S("MI_PlasticRed", srgb(200, 32, 40), 0.35)
    mi["MI_PlasticBlack"] = S("MI_PlasticBlack", grey(0.02), 0.4)
    mi["MI_SeatDark"] = S("MI_SeatDark", srgb(20, 24, 32), 0.55)
    mi["MI_TowelWhite"] = S("MI_TowelWhite", grey(0.8), 1.0)
    mi["MI_DobokWhite"] = S("MI_DobokWhite", grey(0.85), 0.9)
    mi["MI_WoodLight"] = S("MI_WoodLight", srgb(200, 152, 102), 0.5, detail="T_Wood_D", size=120, strength=0.8)
    mi["MI_WoodMid"] = S("MI_WoodMid", srgb(150, 100, 62), 0.5, detail="T_Wood_D", size=120, strength=0.8)
    mi["MI_PotWhite"] = S("MI_PotWhite", grey(0.8), 0.4)
    mi["MI_PlantGreen"] = S("MI_PlantGreen", srgb(52, 112, 40), 0.7)
    mi["MI_PadBlue"] = S("MI_PadBlue", srgb(34, 62, 160), 0.45)
    mi["MI_FrameDark"] = S("MI_FrameDark", grey(0.03), 0.4, 0.6)
    mi["MI_Glass"] = instance("MI_Glass", glass, {"Opacity": 0.1}, {"Color": grey(0.9)})
    mi["MI_LightLens"] = instance("MI_LightLens", emissive, {"Intensity": 60.0}, {"Color": unreal.LinearColor(1.0, 0.95, 0.85, 1)})
    mi["MI_LightPanel"] = instance("MI_LightPanel", emissive, {"Intensity": 12.0}, {"Color": unreal.LinearColor(1.0, 0.97, 0.92, 1)})
    mi["MI_ScreenDark"] = instance("MI_ScreenDark", emissive, {"Intensity": 0.6}, {"Color": unreal.LinearColor(0.05, 0.08, 0.14, 1)})
    mi["MI_ScreenScoreboard"] = instance("MI_ScreenScoreboard", emissive, {"Intensity": 3.0}, None, {"Texture": tex["T_Scoreboard"]})
    mi["MI_ScreenExit"] = instance("MI_ScreenExit", emissive, {"Intensity": 4.0}, None, {"Texture": tex["T_ExitSign"]})
    mi["MI_Canvas"] = instance("MI_Canvas", textured, {"Roughness": 0.8}, None, {"Texture": tex["T_Taegukgi"]})
    mi["MI_Canvas_Kicker"] = instance("MI_Canvas_Kicker", textured, {"Roughness": 0.8}, None, {"Texture": tex["T_BannerKicker"]})
    mi["MI_Canvas_Stripes"] = instance("MI_Canvas_Stripes", textured, {"Roughness": 0.8}, None, {"Texture": tex["T_BannerStripes"]})
    mi["MI_WindowView"] = instance("MI_WindowView", emissive, {"Intensity": 2.5}, None, {"Texture": tex["T_WindowView"]})
    # large surfaces
    mi["MI_ArenaFloor"] = S("MI_ArenaFloor", grey(0.16), 0.35, detail="T_Concrete_D", size=400, strength=1.0)
    mi["MI_ArenaWall"] = S("MI_ArenaWall", grey(0.035), 0.7, detail="T_Concrete_D", size=300, strength=0.6)
    mi["MI_ArenaCeiling"] = S("MI_ArenaCeiling", grey(0.02), 0.9)
    mi["MI_ArenaRiser"] = S("MI_ArenaRiser", grey(0.05), 0.6, detail="T_Concrete_D", size=300, strength=0.6)
    mi["MI_Plaster"] = S("MI_Plaster", srgb(214, 206, 192), 0.85, detail="T_Plaster_D", size=200, strength=1.0)
    mi["MI_WoodWall"] = S("MI_WoodWall", srgb(176, 124, 76), 0.55, detail="T_Wood_D", size=150, strength=0.9)
    mi["MI_WoodFloor"] = S("MI_WoodFloor", srgb(160, 110, 66), 0.45, detail="T_Wood_D", size=90, strength=0.9)
    mi["MI_Mirror"] = S("MI_Mirror", grey(0.95), 0.02, 1.0)
    mi["MI_CeilingWhite"] = S("MI_CeilingWhite", grey(0.7), 0.9)
    mi["MI_DuctMetal"] = S("MI_DuctMetal", grey(0.35), 0.5, 1.0)
    log("materials", len(mi))
    return mi


# ------------------------------------------------------------------ placement helpers
class Placer:
    def __init__(self, meshes, mi):
        self.meshes, self.mi = meshes, mi
        self.cube = EAL.load_asset("/Engine/BasicShapes/Cube")
        self.cylinder = EAL.load_asset("/Engine/BasicShapes/Cylinder")
        self.count = 0

    def _finish(self, a, label, folder):
        a.set_actor_label(label)
        a.set_folder_path(folder)
        self.count += 1
        return a

    def prop(self, name, x, y, z=0.0, yaw=0.0, folder="Props", overrides=None, scale=1.0, label=None, pitch=0.0, roll=0.0):
        """Blender props face -Y in Blender, which is +Y in Unreal; yaw rotates from there."""
        a = actors.spawn_actor_from_object(self.meshes[name], vec(x, y, z), unreal.Rotator(roll, pitch, yaw))
        comp = a.static_mesh_component
        for slot in comp.get_material_slot_names():
            s = str(slot)
            if overrides and s in overrides:
                comp.set_material(comp.get_material_index(slot), self.mi[overrides[s]])
            elif s in self.mi:
                comp.set_material(comp.get_material_index(slot), self.mi[s])
        if scale != 1.0:
            a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        return self._finish(a, label or name, folder)

    def box(self, label, sx, sy, sz, cx, cy, cz, material, folder="Architecture", yaw=0.0):
        """Axis-aligned box: size and centre in metres."""
        a = actors.spawn_actor_from_object(self.cube, vec(cx, cy, cz), unreal.Rotator(0, 0, yaw))
        a.set_actor_scale3d(unreal.Vector(sx, sy, sz))
        a.static_mesh_component.set_material(0, self.mi[material])
        return self._finish(a, label, folder)

    def column(self, label, r, h, cx, cy, z0, material, folder="Architecture", axis_rot=None):
        a = actors.spawn_actor_from_object(self.cylinder, vec(cx, cy, z0 + h / 2), axis_rot or unreal.Rotator(0, 0, 0))
        a.set_actor_scale3d(unreal.Vector(r * 2, r * 2, h))
        a.static_mesh_component.set_material(0, self.mi[material])
        return self._finish(a, label, folder)


def light(cls, label, x, y, z, pitch=0.0, yaw=0.0, folder="Lighting"):
    a = actors.spawn_actor_from_class(cls, vec(x, y, z), unreal.Rotator(0, pitch, yaw))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a


def set_light(comp, intensity, color=(1.0, 0.96, 0.9), radius=None, cast_shadows=True, units=None, **props):
    """Properties are set directly: the Set* functions are ignored on stationary lights."""
    comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    if units is not None:
        comp.set_editor_property("intensity_units", units)
    comp.set_editor_property("intensity", intensity)
    comp.set_editor_property("light_color", unreal.Color(r=int(color[0] * 255), g=int(color[1] * 255), b=int(color[2] * 255), a=255))
    if radius is not None:
        comp.set_editor_property("attenuation_radius", M(radius))
    comp.set_editor_property("cast_shadows", cast_shadows)
    for k, v in props.items():
        comp.set_editor_property(k, v)


def post_process(label, bias, min_b=2.0, max_b=12.0, bloom=0.4, vignette=0.3):
    """min_b/max_b are EV100 (the project extends the default luminance range)."""
    a = actors.spawn_actor_from_class(unreal.PostProcessVolume, vec(0, 0, 2), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.set_folder_path("Lighting")
    a.set_editor_property("unbound", True)
    s = a.get_editor_property("settings")
    for k, v in (("auto_exposure_bias", bias), ("auto_exposure_min_brightness", min_b),
                 ("auto_exposure_max_brightness", max_b), ("bloom_intensity", bloom), ("vignette_intensity", vignette)):
        s.set_editor_property(f"override_{k}", True)
        s.set_editor_property(k, v)
    a.set_editor_property("settings", s)
    return a


def new_level(path):
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    levels.new_level(path)
    log("new level", path)


# ------------------------------------------------------------------ competition arena
def build_arena(p):
    new_level("/Game/Maps/L_CompetitionArena")
    HX, HY, HZ = 34.0, 30.0, 24.0     # hall half-extents / ceiling height (m)
    FLOOR = 18.0                      # half size of the flat floor before the stands

    p.box("Floor", 2 * HX, 2 * HY, 0.2, 0, 0, -0.1, "MI_ArenaFloor")
    p.prop("SM_MatOctagon", 0, 0, 0, folder="Mat")
    p.prop("SM_MatSquareBorder", 0, 0, 0, folder="Mat")

    # stands on all four sides: stepped risers with seat rows, black barrier wall in front
    rows, step_d, step_h = 18, 0.85, 0.42
    for side, (dirx, diry) in enumerate(((0, 1), (0, -1), (1, 0), (-1, 0))):
        along = 2 * FLOOR if diry else 2 * FLOOR
        yaw = {(0, 1): 0, (0, -1): 180, (1, 0): -90, (-1, 0): 90}[(dirx, diry)]
        # barrier
        bx = dirx * (FLOOR - 0.1)
        by = diry * (FLOOR - 0.1)
        if diry:
            p.box(f"Barrier_{side}", along, 0.2, 1.1, 0, by, 0.55, "MI_ArenaWall", "Stands")
        else:
            p.box(f"Barrier_{side}", 0.2, along, 1.1, bx, 0, 0.55, "MI_ArenaWall", "Stands")
        for r in range(rows):
            d = FLOOR + 1.0 + r * step_d
            z = 1.2 + r * step_h
            cx, cy = dirx * (d + step_d / 2), diry * (d + step_d / 2)
            if diry:
                p.box(f"Riser_{side}_{r}", along + 2 * d, step_d, z, 0, cy, z / 2, "MI_ArenaRiser", "Stands")
            else:
                p.box(f"Riser_{side}_{r}", step_d, along + 2 * d, z, cx, 0, z / 2, "MI_ArenaRiser", "Stands")
            if r % 2 == 1 and r > 12:
                continue   # a couple of aisle-free upper rows keep the actor count down
            n_sections = int((along + 2 * d - 4) // 5.5)
            for s_i in range(n_sections):
                off = -((n_sections - 1) * 5.5) / 2 + s_i * 5.5
                sx = off if diry else cx + dirx * 0.1
                sy = cy + diry * 0.1 if diry else off
                p.prop("SM_SeatRow10", sx, sy, z, yaw=yaw + 180, folder="Stands", label=f"Seats_{side}_{r}_{s_i}")
    top = 1.2 + rows * step_h
    # outer walls and ceiling
    p.box("Wall_N", 2 * HX + 20, 0.5, HZ, 0, FLOOR + 1 + rows * step_d + 0.25, HZ / 2, "MI_ArenaWall")
    p.box("Wall_S", 2 * HX + 20, 0.5, HZ, 0, -(FLOOR + 1 + rows * step_d + 0.25), HZ / 2, "MI_ArenaWall")
    p.box("Wall_E", 0.5, 2 * HY + 20, HZ, FLOOR + 1 + rows * step_d + 0.25, 0, HZ / 2, "MI_ArenaWall")
    p.box("Wall_W", 0.5, 2 * HY + 20, HZ, -(FLOOR + 1 + rows * step_d + 0.25), 0, HZ / 2, "MI_ArenaWall")
    p.box("Ceiling", 2 * HX + 20, 2 * HY + 20, 0.5, 0, 0, HZ, "MI_ArenaCeiling")

    # truss grid over the mat at 15 m with spot fixtures
    TZ = 15.0
    for i in range(-2, 3):
        for axis in (0, 1):
            for j in range(-2, 2):
                c = i * 4.0
                a = j * 4.0 + 2.0
                if axis == 0:
                    p.prop("SM_Truss4m", a, c, TZ, yaw=0, folder="Truss", label=f"Truss_x_{i}_{j}")
                else:
                    p.prop("SM_Truss4m", c, a, TZ, yaw=90, folder="Truss", label=f"Truss_y_{i}_{j}")
    for x in (-6, -2, 2, 6):
        for y in (-6, -2, 2, 6):
            p.prop("SM_SpotFixture", x, y, TZ - 0.15, folder="Truss", label=f"Spot_{x}_{y}")
            sp = light(unreal.SpotLight, f"SpotLight_{x}_{y}", x, y, TZ - 0.7, pitch=-90)
            centre = abs(x) < 4 and abs(y) < 4
            set_light(sp.spot_light_component, 60000.0 if centre else 40000.0, radius=40.0, cast_shadows=centre,
                      units=unreal.LightUnits.LUMENS, inner_cone_angle=16.0, outer_cone_angle=32.0,
                      volumetric_scattering_intensity=0.6)
    # dim fill over the stands
    for (x, y, yaw) in ((0, 26, 0), (0, -26, 0), (26, 0, 90), (-26, 0, 90)):
        rl = light(unreal.RectLight, f"StandFill_{x}_{y}", x, y, HZ - 2, pitch=-90, yaw=yaw)
        set_light(rl.rect_light_component, 30000.0, (0.9, 0.93, 1.0), radius=35.0, cast_shadows=False,
                  units=unreal.LightUnits.LUMENS, source_width=M(30), source_height=M(8))
    # small ceiling downlights (visual only)
    for x in range(-24, 25, 8):
        for y in range(-22, 23, 8):
            if abs(x) <= 8 and abs(y) <= 8:
                continue
            p.prop("SM_SpotFixture", x, y, HZ - 0.25, folder="Ceiling", label=f"Downlight_{x}_{y}", scale=0.8)

    # scoreboards: two per long side, high on the north and south walls
    wall_y = FLOOR + 1 + rows * step_d
    for sx in (-14, 14):
        p.prop("SM_Scoreboard", sx, wall_y - 0.4, 12.5, yaw=180, folder="Scoreboards", scale=1.6, label=f"Scoreboard_N_{sx}")
        p.prop("SM_Scoreboard", sx, -(wall_y - 0.4), 12.5, yaw=0, folder="Scoreboards", scale=1.6, label=f"Scoreboard_S_{sx}")

    # officials: recorder/judge tables on the far side and on both near diagonals
    def table_group(label, cx, cy, n_tables, monitors=True):
        # Props face +Y at yaw 0, i.e. front = (-sin yaw, cos yaw). Turn each table to face the mat;
        # officials sit behind it, also facing the mat; monitors and mics face the officials.
        yaw_deg = math.degrees(math.atan2(cx, -cy)) if (cx or cy) else 0.0
        yaw = math.radians(yaw_deg)
        fx, fy = -math.sin(yaw), math.cos(yaw)       # prop "front" (+Y in Unreal) after yaw
        rx, ry = math.cos(yaw), math.sin(yaw)
        for t in range(n_tables):
            off = (t - (n_tables - 1) / 2) * 1.85
            tx, ty = cx + rx * off, cy + ry * off
            p.prop("SM_JudgeTable", tx, ty, 0, yaw=yaw_deg, folder=f"Officials/{label}", label=f"{label}_Table{t}")
            for k in (-0.45, 0.45):
                sx, sy = tx + rx * k, ty + ry * k
                # chair behind the table (away from the mat), facing the mat
                p.prop("SM_ChairOffice", sx - fx * 0.75, sy - fy * 0.75, 0, yaw=yaw_deg, folder=f"Officials/{label}",
                       label=f"{label}_Chair{t}_{k}")
                if monitors and k < 0:
                    p.prop("SM_Monitor", sx - fx * 0.1, sy - fy * 0.1, 0.76, yaw=yaw_deg + 180, folder=f"Officials/{label}",
                           label=f"{label}_Monitor{t}")
                p.prop("SM_DeskMic", sx + rx * 0.35 + fx * 0.1, sy + ry * 0.35 + fy * 0.1, 0.76, yaw=yaw_deg + 180,
                       folder=f"Officials/{label}", label=f"{label}_Mic{t}_{k}")

    table_group("FarLeft", -7.0, 9.5, 2)
    table_group("FarCentre", 0.0, 9.5, 1)
    table_group("FarRight", 7.0, 9.5, 3)
    table_group("NearLeft", -9.8, -7.0, 3)
    table_group("NearRight", 9.8, -7.0, 3)

    # coach corners: Chung (blue) left, Hong (red) right, chairs facing the mat
    for side, colour, x in (("Chung", "Blue", -8.2), ("Hong", "Red", 8.2)):
        yaw = -90 if x < 0 else 90
        for k in (-0.35, 0.35):
            p.prop(f"SM_ChairStack{colour}", x, 5.8 + k, 0, yaw=yaw, folder=f"CoachCorner/{side}", label=f"{side}_Chair_{k}")
        p.prop("SM_TowelFolded", x, 5.45, 0.47, folder=f"CoachCorner/{side}", label=f"{side}_Towel")
        p.prop("SM_Bucket", x + (0.5 if x < 0 else -0.5), 5.9, 0, folder=f"CoachCorner/{side}",
               overrides={"MI_PlasticRed": "MI_PlasticBlue" if colour == "Blue" else "MI_PlasticRed"}, label=f"{side}_Bucket")

    # lighting and atmosphere
    fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, vec(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog.set_actor_label("HazeFog")
    fog.set_folder_path("Lighting")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.004)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.02, 0.022, 0.03, 1))
    fc.set_editor_property("enable_volumetric_fog", True)
    sky = light(unreal.SkyLight, "SkyLight", 0, 0, 5)
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("intensity", 0.15)
    post_process("PostProcess", bias=0.0, min_b=4.0, max_b=9.0, bloom=0.5, vignette=0.35)
    ps = actors.spawn_actor_from_class(unreal.PlayerStart, vec(0, -3.0, 0.1), unreal.Rotator(0, 0, 90))
    ps.set_folder_path("Gameplay")
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        vec(0, -17.5, 5.5), unreal.Rotator(0, -14, 90))
    levels.save_current_level()
    log("arena actors", p.count)


# ------------------------------------------------------------------ training dojang
def build_dojang(p):
    new_level("/Game/Maps/L_TrainingDojang")
    RX, RY, RZ = 9.0, 7.0, 4.2        # room half-size and height

    p.box("Floor", 2 * RX, 2 * RY, 0.1, 0, 0, -0.05, "MI_WoodFloor")
    # puzzle mats: blue field inside a 1 m red border, red training square outline
    MT = 0.025
    FX, FY = 7.0, 5.0                 # half size of the blue field
    p.box("Mat_Blue", 2 * FX, 2 * FY, MT, 0, 0.3, MT / 2, "MI_MatBlue", "Mat")
    p.box("Mat_Red_N", 2 * FX + 2, 1, MT, 0, 0.3 + FY + 0.5, MT / 2, "MI_MatRed", "Mat")
    p.box("Mat_Red_S", 2 * FX + 2, 1, MT, 0, 0.3 - FY - 0.5, MT / 2, "MI_MatRed", "Mat")
    p.box("Mat_Red_E", 1, 2 * FY, MT, FX + 0.5, 0.3, MT / 2, "MI_MatRed", "Mat")
    p.box("Mat_Red_W", 1, 2 * FY, MT, -FX - 0.5, 0.3, MT / 2, "MI_MatRed", "Mat")
    L, W_ = 8.0, 0.25
    for label, sx, sy, cx, cy in (("N", L, W_, 0, 0.3 + L / 2 - W_ / 2), ("S", L, W_, 0, 0.3 - L / 2 + W_ / 2),
                                  ("E", W_, L, L / 2 - W_ / 2, 0.3), ("W", W_, L, -L / 2 + W_ / 2, 0.3)):
        p.box(f"Mat_Square_{label}", sx, sy, MT + 0.002, cx, cy, (MT + 0.002) / 2, "MI_MatRed", "Mat")

    # walls
    WT = 0.2
    p.box("Wall_Far", 2 * RX, WT, RZ, 0, RY + WT / 2, RZ / 2, "MI_Plaster")
    p.box("Wall_Near", 2 * RX, WT, RZ, 0, -RY - WT / 2, RZ / 2, "MI_Plaster")
    p.box("Wall_Mirror", WT, 2 * RY, RZ, -RX - WT / 2, 0, RZ / 2, "MI_Plaster")
    p.box("Ceiling", 2 * RX + 1, 2 * RY + 1, 0.2, 0, 0, RZ + 0.1, "MI_CeilingWhite")
    # wood pilasters and cornice band on the far wall
    for x in (-8.4, -2.2, 2.2, 8.4):
        p.box(f"Pilaster_{x}", 0.5, 0.12, RZ, x, RY - 0.06, RZ / 2, "MI_WoodWall")
    p.box("Cornice_Far", 2 * RX, 0.12, 0.3, 0, RY - 0.06, RZ - 0.15, "MI_WoodWall")
    p.box("Skirting_Far", 2 * RX, 0.05, 0.15, 0, RY - 0.03, 0.075, "MI_WoodWall")

    # window wall (+X): wood lower wall, 4 windows, piers between them, outside view
    p.box("WindowWall_Lower", WT, 2 * RY, 0.9, RX + WT / 2, 0, 0.45, "MI_WoodWall")
    p.box("WindowWall_Top", WT, 2 * RY, 0.7, RX + WT / 2, 0, RZ - 0.35, "MI_Plaster")
    win_y = [-4.8, -1.6, 1.6, 4.8]
    piers = [-RY] + [y - 0.9 for y in win_y] + [RY]
    for i, y in enumerate(win_y):
        p.prop("SM_Window", RX + 0.02, y, 0.9, yaw=90, folder="Windows", label=f"Window_{i}")
    edges = [-RY, -5.7, -3.9, -2.5, -0.7, 0.7, 2.5, 3.9, 5.7, RY]
    for i in range(0, len(edges) - 1, 2):
        a, b_ = edges[i], edges[i + 1]
        p.box(f"Pier_{i}", WT, b_ - a, RZ - 1.6, RX + WT / 2, (a + b_) / 2, 0.9 + (RZ - 1.6) / 2, "MI_WoodWall")
    view = p.box("OutsideView", 0.05, 2 * RY + 8, 7.0, RX + 6.0, 0, 2.5, "MI_WindowView", "Windows")
    view.static_mesh_component.set_cast_shadow(False)   # the sun comes through the windows past it
    p.prop("SM_Bench", RX - 0.4, 3.2, 0, yaw=90, folder="Windows")
    p.prop("SM_TowelFolded", RX - 0.4, 3.6, 0.47, folder="Windows")
    p.prop("SM_PlantPot", RX - 0.5, 6.3, 0, folder="Windows")
    for i, z in enumerate((0.0, 0.2, 0.4, 0.6, 0.8, 1.0)):
        p.prop("SM_TargetShield", RX - 0.5, 5.2 + (i % 2) * 0.05, z, yaw=90, pitch=0, roll=90, folder="Equipment",
               label=f"PadStack_{i}", scale=1.0)

    # mirror wall (-X): wall pads at the base, mirrors above, reflections of the mat
    for i in range(14):
        p.prop("SM_WallPad", -RX + 0.05, -RY + 0.5 + i * 1.0, 0, yaw=-90, folder="MirrorWall", label=f"WallPad_{i}")
    p.box("Mirror", 0.02, 2 * RY - 0.6, 2.4, -RX + 0.02, 0, 0.6 + 1.3, "MI_Mirror", "MirrorWall")
    for y in range(-6, 7, 3):
        p.box(f"MirrorSeam_{y}", 0.03, 0.03, 2.4, -RX + 0.03, y, 1.9, "MI_FrameDark", "MirrorWall")
    p.box("MirrorTrim_Top", 0.06, 2 * RY - 0.6, 0.08, -RX + 0.03, 0, 3.14, "MI_WoodWall", "MirrorWall")
    p.prop("SM_FrameLandscape", -RX + 0.03, -3.5, 3.6, yaw=-90, folder="MirrorWall",
           overrides={"MI_Canvas": "MI_Canvas_Kicker"}, label="Banner_Kicker", scale=0.9)
    p.prop("SM_FrameLandscape", -RX + 0.03, 1.5, 3.6, yaw=-90, folder="MirrorWall",
           overrides={"MI_Canvas": "MI_Canvas_Stripes"}, label="Banner_Stripes", scale=0.9)

    # far wall (+Y): flag, banners, door, equipment
    FW = RY - 0.02
    p.prop("SM_FrameFlag", 1.2, FW, 2.75, yaw=180, folder="FarWall", label="Flag_Taegukgi")
    p.prop("SM_FrameLandscape", -4.3, FW, 2.9, yaw=180, folder="FarWall", overrides={"MI_Canvas": "MI_Canvas_Stripes"},
           label="Banner_Far_Left", scale=0.75)
    p.prop("SM_FrameLandscape", 5.8, FW, 2.9, yaw=180, folder="FarWall", overrides={"MI_Canvas": "MI_Canvas_Stripes"},
           label="Banner_Far_Right", scale=0.75)
    p.prop("SM_Door", -1.0, FW, 0, yaw=180, folder="FarWall")
    p.prop("SM_ExitSign", -1.0, FW - 0.02, 2.35, yaw=180, folder="FarWall")
    # dobok rack + shoe cubby left of the door
    p.box("DobokRail", 1.2, 0.05, 0.05, -4.3, FW - 0.35, 1.85, "MI_TrussMetal", "FarWall")
    p.box("DobokRack_Back", 1.3, 0.04, 2.0, -4.3, FW - 0.05, 1.0, "MI_WoodMid", "FarWall")
    for i, x in enumerate((-4.6, -4.0)):
        p.prop("SM_DobokHanging", x, FW - 0.35, 0.85, yaw=180, folder="FarWall", label=f"Dobok_{i}")
    p.prop("SM_ShoeCubby", -2.7, FW - 0.2, 0, yaw=180, folder="FarWall")
    p.prop("SM_Bench", -2.7, FW - 1.2, 0, yaw=0, folder="FarWall", scale=0.7)
    # paddle racks right of the flag
    for i, (x, colourful) in enumerate(((3.3, False), (4.9, True))):
        p.prop("SM_WallRack", x, FW, 0.5, yaw=180, folder="Equipment", label=f"PaddleRack_{i}")
        for row in range(3):
            for col in range(5):
                if colourful and (row + col) % 2:
                    kind = "SM_TargetShield"
                    p.prop(kind, x - 0.56 + col * 0.28, FW - 0.12, 0.5 + 1.15 - row * 0.42 - 0.62, yaw=180, folder="Equipment",
                           label=f"Rack{i}_Shield_{row}_{col}", scale=0.45)
                else:
                    p.prop("SM_KickPaddle", x - 0.56 + col * 0.28, FW - 0.1, 0.5 + 1.15 - row * 0.42 - 0.34, yaw=180,
                           folder="Equipment", label=f"Rack{i}_Paddle_{row}_{col}")
    p.prop("SM_ShoeCubby", 6.9, FW - 0.2, 0, yaw=180, folder="Equipment", label="GearShelf",
           overrides={"MI_BlackVinyl": "MI_PlasticBlue"})
    for i, (x, y) in enumerate(((-6.6, 6.0), (2.3, 6.2), (7.6, 6.1), (-7.9, 6.2))):
        p.prop("SM_HeavyBagStanding", x, y, 0, folder="Equipment", label=f"HeavyBag_{i}")
    for i in range(4):
        p.box(f"PadStackFloor_{i}", 0.62, 0.42, 0.14, 8.1, 6.3 - 0.0, 0.07 + i * 0.14, "MI_BlackVinyl", "Equipment")

    # ceiling: exposed ducts and linear LEDs
    for y in (-3.5, 3.5):
        duct = p.column(f"Duct_{y}", 0.25, 2 * RX, 0, y, RZ - 0.45 - RX, "MI_DuctMetal", "Ceiling",
                        axis_rot=unreal.Rotator(0, 90, 0))   # pitch 90: cylinder axis along X
        duct.set_actor_location(vec(0, y, RZ - 0.45), False, False)
    for x in range(-6, 7, 3):
        for y in (-5.5, -1.75, 1.75, 5.5):
            p.prop("SM_LedLinear", x, y, RZ, yaw=0, folder="Ceiling", label=f"Led_{x}_{y}")
    for x in (-6, 0, 6):
        for y in (-3.6, 0, 3.6):
            rl = light(unreal.RectLight, f"CeilingLight_{x}_{y}", x, y, RZ - 0.1, pitch=-90)
            set_light(rl.rect_light_component, 6000.0, (1.0, 0.95, 0.88), radius=12.0, cast_shadows=x == 0 and y == 0,
                      units=unreal.LightUnits.LUMENS, source_width=M(4), source_height=M(2))

    # late-afternoon sun through the windows, sky for the window light
    sun = light(unreal.DirectionalLight, "Sun", 0, 0, 10, pitch=-24, yaw=200)
    set_light(sun.get_component_by_class(unreal.DirectionalLightComponent), 8.0, (1.0, 0.82, 0.62), atmosphere_sun_light=True)
    atm = actors.spawn_actor_from_class(unreal.SkyAtmosphere, vec(0, 0, 0), unreal.Rotator(0, 0, 0))
    atm.set_folder_path("Lighting")
    sky = light(unreal.SkyLight, "SkyLight", 0, 0, 3)
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)
    sky.light_component.set_editor_property("intensity", 1.0)
    post_process("PostProcess", bias=0.5, min_b=4.0, max_b=11.0, bloom=0.45, vignette=0.25)
    ps = actors.spawn_actor_from_class(unreal.PlayerStart, vec(0, -3.0, 0.1), unreal.Rotator(0, 0, 90))
    ps.set_folder_path("Gameplay")
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        vec(0.0, -6.6, 1.7), unreal.Rotator(0, -4, 90))
    levels.save_current_level()
    log("dojang actors", p.count)


try:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tex = import_textures()
    meshes = import_meshes()
    mi = build_materials(tex)
    if which in ("all", "arena"):
        build_arena(Placer(meshes, mi))
    if which in ("all", "dojang"):
        build_dojang(Placer(meshes, mi))
    log("DONE")
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    _log.close()
