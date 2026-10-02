"""Build the Career venues (GDD 6.2), one level per tournament tier. Environments only: no gameplay logic.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/build_venues.py"                 all six
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/build_venues.py" club gym        just those

    club         /Game/Maps/L_ClubDojang         tier 1  club sparring night
    gym          /Game/Maps/L_SchoolGym          tier 2  city open
    provincial   /Game/Maps/L_ProvincialHall     tier 3  provincial championship
    national     /Game/Maps/L_NationalArena      tier 4  national championship
    continental  /Game/Maps/L_ContinentalArena   tier 5  continental open
    world        /Game/Maps/L_WorldFinalStage    tier 6  world series final

Prerequisites: py Tools/Environment/make_env_textures.py, run("build_environment_meshes") and
run("build_venue_meshes") in Blender, and build_arenas.py once (it creates the M_Env_* parent materials and
the shared MI_* instances these levels reuse).

Only new or writable assets are (re)imported or saved: anything synced read-only from Perforce is loaded as
is, so the script runs without checking out the competition arena's assets.

Every venue shares the contest area at the origin (8 m octagon in a 12 m square, officials' tables, coach
chairs) so gameplay can treat them alike; they differ in set dressing, crowd and lighting.
"""
import importlib
import math
import os
import random
import sys
import traceback

import unreal

sys.path.insert(0, "D:/Open-Stance-Gyeorugi/Tools/Unreal")
import env_common

importlib.reload(env_common)
from env_common import (ENV, EAL, MESH_SRC, TEX_SRC, M, Placer, actors, crowd_overrides, face_yaw, grey, import_task,
                        instance, is_locked, levels, light, new_level, post_process, set_light, srgb, vec)

log = env_common.open_log("build_venues")
LU = unreal.LightUnits.LUMENS


# ------------------------------------------------------------------ assets
SIGNAGE = ("T_Ad_", "T_Banner_", "T_Ribbon_", "T_Screen_", "T_Club", "T_TeamPhoto", "T_Flag_", "T_CourtNumber_",
           "T_Podium", "T_GymScoreboard", "T_EntranceScreen")


def import_new_textures():
    tex = {}
    for fn in sorted(os.listdir(TEX_SRC)):
        if not fn.endswith(".png"):
            continue
        name = fn[:-4]
        path = f"{ENV}/Textures/{name}"
        if EAL.does_asset_exist(path) and is_locked(path):
            tex[name] = EAL.load_asset(path)
            continue
        t = import_task(f"{TEX_SRC}/{fn}", f"{ENV}/Textures", name)
        if name.endswith("_N"):
            t.set_editor_property("srgb", False)
            t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        elif name.endswith("_H"):
            t.set_editor_property("srgb", False)
        if name.startswith(SIGNAGE):
            t.set_editor_property("never_stream", True)   # text stays sharp at the camera distances we use
        EAL.save_asset(t.get_path_name())
        tex[name] = t
        log("imported texture", name)
    return tex


NANITE = ("SM_SeatBlock_", "SM_Bleacher_")


def import_new_meshes():
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX false")
    meshes = {}
    for fn in sorted(os.listdir(MESH_SRC)):
        if not fn.endswith(".fbx"):
            continue
        name = fn[:-4]
        path = f"{ENV}/Meshes/{name}"
        if EAL.does_asset_exist(path) and is_locked(path):
            meshes[name] = EAL.load_asset(path)
            continue
        ui = unreal.FbxImportUI()
        ui.import_mesh, ui.import_as_skeletal = True, False
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        ui.import_materials, ui.import_textures, ui.import_animations = False, False, False
        data = ui.static_mesh_import_data
        data.set_editor_property("combine_meshes", True)
        data.set_editor_property("auto_generate_collision", not name.startswith(NANITE))
        if name.startswith(NANITE):
            try:
                data.set_editor_property("build_nanite", True)   # crowds: many small triangles
            except Exception as e:
                log("nanite flag unavailable", e)
        meshes[name] = import_task(f"{MESH_SRC}/{fn}", f"{ENV}/Meshes", name, ui)
        log("imported mesh", name)
    return meshes


def load_materials():
    mi = {}
    for path in EAL.list_assets(f"{ENV}/Materials", recursive=False):
        a = EAL.load_asset(path.split(".")[0])
        if isinstance(a, unreal.MaterialInterface):
            mi[a.get_name()] = a
    return mi


SHIRTS = [(18, 18, 20), (190, 190, 192), (176, 30, 36), (34, 72, 160), (40, 110, 60), (214, 170, 40), (62, 64, 70),
          (110, 40, 90)]
PANTS = [(16, 16, 20), (44, 60, 92), (120, 104, 82)]
# natural skin tones (Monk scale range) and natural hair only, per Docs/Character_Customization.md
SKINS = [(236, 200, 172), (214, 164, 128), (178, 124, 88), (132, 86, 58), (84, 56, 40)]
HAIRS = [(18, 14, 12), (52, 36, 24), (96, 66, 40), (140, 136, 130)]
BELTS = {"Yellow": (220, 180, 30), "Green": (40, 120, 50), "Blue": (30, 70, 170), "Red": (180, 24, 32), "Black": (12, 12, 12)}
TIERS = ("City", "Provincial", "National", "Continental", "World")
FLAG_CODES = ["KOR", "FRA", "ITA", "DEU", "NLD", "BEL", "IRL", "AUT", "POL", "SWE", "DNK", "FIN", "NOR", "NGA",
              "THA", "COL", "JPN"]


def build_venue_materials(tex, mi):
    surf = EAL.load_asset(f"{ENV}/Materials/M_Env_Surface")
    textured = EAL.load_asset(f"{ENV}/Materials/M_Env_Textured")
    emissive = EAL.load_asset(f"{ENV}/Materials/M_Env_Emissive")
    new = {}

    def put(name, fn):
        if is_locked(f"{ENV}/Materials/{name}"):
            return
        new[name] = fn()

    def S(name, color, rough=0.6, metal=0.0, detail=None, size=100.0, strength=0.0):
        t = {"DetailTex": tex[detail]} if detail else None
        put(name, lambda: instance(name, surf, {"Roughness": rough, "Metallic": metal, "DetailSizeCm": size,
                                                "DetailStrength": strength}, {"Color": color}, t))

    def T(name, texture, rough=0.8):
        put(name, lambda: instance(name, textured, {"Roughness": rough}, None, {"Texture": tex[texture]}))

    def E(name, intensity, texture=None, color=None):
        put(name, lambda: instance(name, emissive, {"Intensity": intensity}, {"Color": color} if color else None,
                                   {"Texture": tex[texture]} if texture else None))

    for i, c in enumerate(SHIRTS):
        S(f"MI_CrowdShirt{i}", srgb(*c), 0.85)
    for i, c in enumerate(PANTS):
        S(f"MI_CrowdPants{i}", srgb(*c), 0.85)
    for i, c in enumerate(SKINS):
        S(f"MI_CrowdSkin{i}", srgb(*c), 0.55)
    for i, c in enumerate(HAIRS):
        S(f"MI_CrowdHair{i}", srgb(*c), 0.7)
    for k, c in BELTS.items():
        S(f"MI_Belt{k}", srgb(*c), 0.8)
    S("MI_SeatNavy", srgb(18, 30, 64), 0.5)
    S("MI_SeatBlue", srgb(24, 56, 128), 0.5)
    S("MI_SeatRed", srgb(120, 20, 28), 0.5)
    S("MI_BleacherDeck", srgb(120, 120, 116), 0.6, detail="T_Concrete_D", size=200, strength=0.5)
    S("MI_BleacherWood", srgb(204, 160, 108), 0.45, detail="T_Wood_D", size=80, strength=0.8)
    S("MI_LineWhite", grey(0.85), 0.5)
    S("MI_RimOrange", srgb(226, 88, 20), 0.4, 0.3)
    S("MI_GymWall", srgb(222, 216, 200), 0.85, detail="T_Concrete_D", size=120, strength=0.35)
    S("MI_PadGreen", srgb(28, 84, 58), 0.45)
    S("MI_HallFloor", srgb(70, 92, 112), 0.4, detail="T_Concrete_D", size=300, strength=0.3)
    S("MI_HallWall", srgb(200, 202, 204), 0.8, detail="T_Concrete_D", size=300, strength=0.4)
    S("MI_StageTop", grey(0.015), 0.25)
    S("MI_StageSkirt", grey(0.01), 0.9)
    S("MI_CarpetBlack", grey(0.012), 0.95)
    S("MI_PodiumWhite", grey(0.8), 0.4)
    S("MI_WarmupMat", srgb(38, 98, 214), 0.6)
    T("MI_GymCourt", "T_GymCourt", 0.35)
    T("MI_ClubBanner", "T_ClubBanner", 0.9)
    T("MI_TeamPhoto", "T_TeamPhoto", 0.4)
    T("MI_ClubTenets", "T_ClubTenets", 0.7)
    for n in (1, 2, 3):
        T(f"MI_CourtNumber{n}", f"T_CourtNumber_{n}", 0.6)
        T(f"MI_PodiumNumber{n}", f"T_Podium{n}", 0.4)
    for code in FLAG_CODES:
        T(f"MI_Flag_{code}", f"T_Flag_{code}", 0.9)
    for tier in TIERS:
        T(f"MI_Ad_{tier}", f"T_Ad_{tier}", 0.6)                 # printed boards
        T(f"MI_Banner_{tier}", f"T_Banner_{tier}", 0.9)         # fabric banners
        E(f"MI_AdLed_{tier}", 1500.0, f"T_Ad_{tier}")            # LED perimeter boards (~hundreds of nits)
        E(f"MI_Ribbon_{tier}", 1500.0, f"T_Ribbon_{tier}")
        E(f"MI_ScreenEvent_{tier}", 1800.0, f"T_Screen_{tier}")
    E("MI_ScreenGym", 12.0, "T_GymScoreboard")
    E("MI_WindowNight", 4.0, "T_WindowNight")
    E("MI_EntranceScreen", 1800.0, "T_EntranceScreen")
    E("MI_StageLed", 1500.0, color=unreal.LinearColor(0.75, 0.85, 1.0, 1))
    E("MI_StageLedBlue", 2000.0, color=unreal.LinearColor(0.1, 0.3, 1.0, 1))
    E("MI_StageLedRed", 2000.0, color=unreal.LinearColor(1.0, 0.06, 0.08, 1))
    E("MI_StageLedGold", 1500.0, color=unreal.LinearColor(1.0, 0.7, 0.3, 1))
    mi.update(new)
    # slot defaults: canvases default to something sensible when a placement gives no override
    for slot, default in (("MI_Banner", "MI_Banner_City"), ("MI_Ad", "MI_Ad_Provincial"), ("MI_Ribbon", "MI_Ribbon_National"),
                          ("MI_ScreenEvent", "MI_ScreenEvent_National"), ("MI_CourtNumber", "MI_CourtNumber1"),
                          ("MI_Flag", "MI_Flag_KOR"), ("MI_Podium1", "MI_PodiumNumber1"), ("MI_Podium2", "MI_PodiumNumber2"),
                          ("MI_Podium3", "MI_PodiumNumber3")):
        mi.setdefault(slot, mi[default])
    log("venue materials", len(new), "total", len(mi))
    return mi


# ------------------------------------------------------------------ shared building blocks
SIDES = {"N": (0, 1, 180), "S": (0, -1, 0), "E": (1, 0, 90), "W": (-1, 0, -90)}   # direction out, prop yaw facing in
STEP_D, STEP_H = 0.85, 0.42
BL_D = 0.76                       # gym bleacher row depth (build_venue_meshes.py)


def stands(p, tag, specs, rows, first_top, occupancy, rng, seat_mat="MI_SeatDark", riser_mat="MI_ArenaRiser",
           barrier=True):
    """Stepped seating. specs: [(side, edge, half_along)], edge = distance from the centre to the front of the
    first row, half_along = half the floor edge length (seat blocks stay within it, so corners show bare risers
    like aisles). Seat blocks are 6 rows deep; occupancy(band, i) -> "Empty"/"Sparse"/"Half"/"Full"."""
    for side, edge, half_along in specs:
        dx, dy, yaw = SIDES[side]
        folder = f"Stands/{tag}_{side}"
        if barrier:
            h = max(first_top - 0.1, 1.0)
            if dy:
                p.box(f"{tag}_Barrier_{side}", 2 * half_along + 2, 0.2, h, 0, dy * (edge - 0.1), h / 2, "MI_ArenaWall", folder)
            else:
                p.box(f"{tag}_Barrier_{side}", 0.2, 2 * half_along + 2, h, dx * (edge - 0.1), 0, h / 2, "MI_ArenaWall", folder)
        for r in range(rows):
            d = edge + r * STEP_D
            z = first_top + r * STEP_H
            along = 2 * (half_along + d - edge + 1.0)
            c = d + STEP_D / 2
            if dy:
                p.box(f"{tag}_Riser_{side}_{r}", along, STEP_D, z, 0, dy * c, z / 2, riser_mat, folder)
            else:
                p.box(f"{tag}_Riser_{side}_{r}", STEP_D, along, z, dx * c, 0, z / 2, riser_mat, folder)
        n = int(2 * half_along // 5.0)
        for band in range(rows // 6):
            c = edge + 6 * band * STEP_D + STEP_D / 2 + 0.1
            z0 = first_top + 6 * band * STEP_H
            for i in range(n):
                kind = occupancy(band, i)
                name = "SM_SeatBlock_Empty" if kind == "Empty" else f"SM_SeatBlock_{kind}{rng.choice('AB')}"
                off = (i - (n - 1) / 2) * 5.0
                x, y = (off, dy * c) if dy else (dx * c, off)
                a = p.prop(name, x, y, z0, yaw=yaw, folder=folder, overrides=crowd_overrides(rng, seat_mat),
                           label=f"{tag}_Seats_{side}_{band}_{i}")
                if kind != "Empty" and rng.random() < 0.5:
                    a.set_actor_scale3d(unreal.Vector(-1, 1, 1))   # mirrored copy for variety
    return edge + rows * STEP_D


def ring(p, tag, specs, prop, spacing, z, inset, overrides=None, cycle=None, folder=None):
    """A row of props along each side, facing the centre: specs [(side, distance, half_along)]."""
    k = 0
    for side, dist, half_along in specs:
        dx, dy, yaw = SIDES[side]
        n = max(1, int(2 * half_along // spacing))
        for i in range(n):
            off = (i - (n - 1) / 2) * spacing
            x, y = (off, dy * (dist - inset)) if dy else (dx * (dist - inset), off)
            o = dict(overrides or {})
            if cycle:
                o.update(cycle[k % len(cycle)])
            p.prop(prop, x, y, z, yaw=yaw, folder=folder or f"Dressing/{tag}", overrides=o, label=f"{tag}_{side}_{i}")
            k += 1


def table_group(p, label, cx, cy, n_tables, folder, monitors=True):
    """Officials' tables facing the mat (same layout rules as build_arenas.py)."""
    yaw_deg = face_yaw(cx, cy)
    yaw = math.radians(yaw_deg)
    fx, fy = -math.sin(yaw), math.cos(yaw)
    rx, ry = math.cos(yaw), math.sin(yaw)
    for t in range(n_tables):
        off = (t - (n_tables - 1) / 2) * 1.85
        tx, ty = cx + rx * off, cy + ry * off
        p.prop("SM_JudgeTable", tx, ty, 0, yaw=yaw_deg, folder=f"{folder}/{label}", label=f"{label}_Table{t}")
        for k in (-0.45, 0.45):
            sx, sy = tx + rx * k, ty + ry * k
            p.prop("SM_ChairOffice", sx - fx * 0.75, sy - fy * 0.75, 0, yaw=yaw_deg, folder=f"{folder}/{label}",
                   label=f"{label}_Chair{t}_{k}")
            if monitors and k < 0:
                p.prop("SM_Monitor", sx - fx * 0.1, sy - fy * 0.1, 0.76, yaw=yaw_deg + 180, folder=f"{folder}/{label}",
                       label=f"{label}_Monitor{t}")
            p.prop("SM_DeskMic", sx + rx * 0.35 + fx * 0.1, sy + ry * 0.35 + fy * 0.1, 0.76, yaw=yaw_deg + 180,
                   folder=f"{folder}/{label}", label=f"{label}_Mic{t}_{k}")


def coach_corners(p, cx=0.0, x=8.2, y=5.8, folder="ContestArea/CoachCorner"):
    for side, colour, sx in (("Chung", "Blue", -1), ("Hong", "Red", 1)):
        px = cx + sx * x
        for k in (-0.35, 0.35):
            p.prop(f"SM_ChairStack{colour}", px, y + k, 0, yaw=-90 * sx, folder=folder, label=f"{side}_Chair_{k}")
        p.prop("SM_TowelFolded", px, y - 0.35, 0.47, folder=folder, label=f"{side}_Towel")
        p.prop("SM_Bucket", px - sx * 0.5, y + 0.1, 0, folder=folder,
               overrides={"MI_PlasticRed": "MI_PlasticBlue" if colour == "Blue" else "MI_PlasticRed"}, label=f"{side}_Bucket")


def contest_area(p, z=0.0, cx=0.0, officials="full", folder="ContestArea"):
    p.prop("SM_MatOctagon", cx, 0, z, folder=f"{folder}/Mat", label=f"MatOctagon_{cx:g}")
    p.prop("SM_MatSquareBorder", cx, 0, z, folder=f"{folder}/Mat", label=f"MatBorder_{cx:g}")
    if officials == "full":
        table_group(p, "FarLeft", cx - 7.0, 9.5, 2, folder)
        table_group(p, "FarCentre", cx, 9.5, 1, folder)
        table_group(p, "FarRight", cx + 7.0, 9.5, 3, folder)
        table_group(p, "NearLeft", cx - 9.8, -7.0, 3, folder)
        table_group(p, "NearRight", cx + 9.8, -7.0, 3, folder)
        coach_corners(p, cx, folder=f"{folder}/CoachCorner")


def shell(p, x0, x1, y0, y1, h, floor_mat, wall_mat, ceil_mat, t=0.4, floor=True):
    cx, cy, w, d = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if floor:
        p.box("Floor", w + 2 * t, d + 2 * t, 0.2, cx, cy, -0.1, floor_mat)
    p.box("Wall_N", w + 2 * t, t, h, cx, y1 + t / 2, h / 2, wall_mat)
    p.box("Wall_S", w + 2 * t, t, h, cx, y0 - t / 2, h / 2, wall_mat)
    p.box("Wall_E", t, d, h, x1 + t / 2, cy, h / 2, wall_mat)
    p.box("Wall_W", t, d, h, x0 - t / 2, cy, h / 2, wall_mat)
    p.box("Ceiling", w + 2 * t, d + 2 * t, t, cx, cy, h + t / 2, ceil_mat)


def spot_grid(p, tag, xs, ys, z, lumens, cone=(16.0, 32.0), color=(1.0, 0.96, 0.9), fixture="SM_SpotFixture",
              shadow_radius=4.0, scatter=0.6, cx=0.0):
    for x in xs:
        for y in ys:
            if fixture:
                p.prop(fixture, cx + x, y, z, folder=f"Rig/{tag}", label=f"{tag}_Fixture_{x}_{y}")
            sp = light(unreal.SpotLight, f"{tag}_Spot_{x}_{y}", cx + x, y, z - 0.7, pitch=-90)
            set_light(sp.spot_light_component, lumens, color, radius=40.0,
                      cast_shadows=abs(x) < shadow_radius and abs(y) < shadow_radius, units=LU,
                      inner_cone_angle=cone[0], outer_cone_angle=cone[1], volumetric_scattering_intensity=scatter)


def truss_grid(p, tag, half, z, step=4.0):
    n = int(round(2 * half / step))
    for i in range(n + 1):
        c = -half + i * step
        for j in range(n):
            a = -half + j * step + step / 2
            p.prop("SM_Truss4m", a, c, z, yaw=0, folder=f"Rig/{tag}", label=f"{tag}_Truss_x_{i}_{j}")
            p.prop("SM_Truss4m", c, a, z, yaw=90, folder=f"Rig/{tag}", label=f"{tag}_Truss_y_{i}_{j}")


def stand_fill(p, floor_half, outer, z, lumens, color=(0.92, 0.94, 1.0)):
    """Soft downlight over the seating on every side (the spill a real house gets from its own lighting), one
    rect light per side over each half of the stand depth."""
    depth = (outer - floor_half) / 2
    for band in range(2):
        d = floor_half + depth * (band + 0.5)
        span = 2 * (floor_half + depth * (band + 1))
        for side in "NSEW":
            dx, dy, _ = SIDES[side]
            rl = light(unreal.RectLight, f"StandFill_{side}_{band}", dx * d, dy * d, z, pitch=-90, yaw=90 if dy else 0)
            set_light(rl.rect_light_component, lumens, color, radius=60.0, cast_shadows=False, units=LU,
                      source_width=M(span), source_height=M(depth), barn_door_angle=60.0)


def haze(density, inscatter, volumetric=True):
    fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, vec(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog.set_actor_label("HazeFog")
    fog.set_folder_path("Lighting")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", density)
    fc.set_editor_property("fog_inscattering_luminance", inscatter)
    fc.set_editor_property("enable_volumetric_fog", volumetric)
    return fog


def sky_light(intensity, realtime=False):
    sky = light(unreal.SkyLight, "SkyLight", 0, 0, 5)
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("intensity", intensity)
    if realtime:
        sky.light_component.set_editor_property("real_time_capture", True)
    return sky


def sun(pitch, yaw, lux, color=(1.0, 0.92, 0.82)):
    s = light(unreal.DirectionalLight, "Sun", 0, 0, 20, pitch=pitch, yaw=yaw)
    set_light(s.get_component_by_class(unreal.DirectionalLightComponent), lux, color, atmosphere_sun_light=True)
    atm = actors.spawn_actor_from_class(unreal.SkyAtmosphere, vec(0, 0, 0), unreal.Rotator(0, 0, 0))
    atm.set_folder_path("Lighting")


LED_PROPS = ("SM_LedRibbon", "SM_AdBoard", "SM_VideoCube", "SM_EventScreen", "SM_EntranceArch", "SM_Scoreboard",
             "SM_ScoreboardPortable", "SM_ScoreboardGymWall")


def finish_level(view_loc, view_rot):
    # LED boards and screens are hundreds of nits; left in Lumen they tint the mat with blue/red bounce light
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.StaticMeshActor):
            mesh = a.static_mesh_component.static_mesh
            if mesh and mesh.get_name() in LED_PROPS:
                a.static_mesh_component.set_editor_property("affect_dynamic_indirect_lighting", False)
    ps = actors.spawn_actor_from_class(unreal.PlayerStart, vec(0, -3.0, 0.1), unreal.Rotator(0, 0, 90))
    ps.set_folder_path("Gameplay")
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(vec(*view_loc), unreal.Rotator(*view_rot))
    levels.save_current_level()


def windows_wall(p, tag, axis, pos, span, z0, wall_h, wall_mat, view_mat, sill, win_ys, view_offset=5.0, scale=1.0):
    """Wall along `axis` ('x' wall at constant x, 'y' at constant y) with SM_Window units (1.8 x 2.6 m * scale),
    piers between them and an emissive view plane outside."""
    ww, wh = 1.8 * scale, 2.6 * scale
    lo, hi = span
    t = 0.3
    out = 1 if pos > 0 else -1

    def wall_box(label, a0, a1, z_lo, z_hi):
        if a1 - a0 < 0.01 or z_hi - z_lo < 0.01:
            return
        if axis == "x":
            p.box(label, t, a1 - a0, z_hi - z_lo, pos + out * t / 2, (a0 + a1) / 2, (z_lo + z_hi) / 2, wall_mat, f"Windows/{tag}")
        else:
            p.box(label, a1 - a0, t, z_hi - z_lo, (a0 + a1) / 2, pos + out * t / 2, (z_lo + z_hi) / 2, wall_mat, f"Windows/{tag}")

    wall_box(f"{tag}_Below", lo, hi, z0, sill)
    wall_box(f"{tag}_Above", lo, hi, sill + wh, wall_h)
    edges = [lo] + [e for c in win_ys for e in (c - ww / 2, c + ww / 2)] + [hi]
    for i in range(0, len(edges), 2):
        wall_box(f"{tag}_Pier_{i}", edges[i], edges[i + 1], sill, sill + wh)
    for i, c in enumerate(win_ys):
        if axis == "x":
            p.prop("SM_Window", pos, c, sill, yaw=90 * out, folder=f"Windows/{tag}", label=f"{tag}_Window_{i}", scale=scale)
        else:
            p.prop("SM_Window", c, pos, sill, yaw=0 if out > 0 else 180, folder=f"Windows/{tag}", label=f"{tag}_Window_{i}",
                   scale=scale)
    vh = wh + 6
    if axis == "x":
        v = p.box(f"{tag}_View", 0.05, hi - lo + 10, vh, pos + out * view_offset, (lo + hi) / 2, sill + wh / 2, view_mat, f"Windows/{tag}")
    else:
        v = p.box(f"{tag}_View", hi - lo + 10, 0.05, vh, (lo + hi) / 2, pos + out * view_offset, sill + wh / 2, view_mat, f"Windows/{tag}")
    v.static_mesh_component.set_cast_shadow(False)


# ------------------------------------------------------------------ tier 1: club dojang (club sparring night)
def build_club(p):
    new_level("/Game/Maps/L_ClubDojang")
    RX, RY, RZ = 10.0, 8.0, 4.6
    p.box("Floor", 2 * RX + 1, 2 * RY + 1, 0.2, 0, 0, -0.1, "MI_WoodFloor")
    p.box("Ceiling", 2 * RX + 1, 2 * RY + 1, 0.2, 0, 0, RZ + 0.1, "MI_CeilingWhite")
    p.box("Wall_Far", 2 * RX, 0.2, RZ, 0, RY + 0.1, RZ / 2, "MI_Plaster")
    p.box("Wall_Near", 2 * RX, 0.2, RZ, 0, -RY - 0.1, RZ / 2, "MI_Plaster")
    p.box("Wall_Mirror", 0.2, 2 * RY, RZ, -RX - 0.1, 0, RZ / 2, "MI_Plaster")
    p.box("Skirting_Far", 2 * RX, 0.04, 0.15, 0, RY - 0.02, 0.075, "MI_WoodWall")

    # contest mat, with training mats filling the rest of the floor
    contest_area(p, officials="none")
    MT = 0.04
    for label, sx, sy, cx, cy in (("N", 18, 1.5, 0, 6.75), ("S", 18, 1.5, 0, -6.75), ("E", 3, 12, 7.5, 0), ("W", 3, 12, -7.5, 0)):
        p.box(f"TrainingMat_{label}", sx, sy, MT, cx, cy, MT / 2, "MI_MatBlue", "ContestArea/Mat")
    coach_corners(p, x=8.0, y=5.3)

    # recorder table on the window side, the club's one portable scoreboard in the far corner
    table_group(p, "Recorder", 8.9, 0.0, 1, "ContestArea")
    p.prop("SM_ScoreboardPortable", 7.6, 7.1, 0, yaw=face_yaw(7.6, 7.1, 0, -2), folder="ContestArea", label="Scoreboard_Portable")

    # far wall: capstone club banner and the volunteers' team photo (GDD easter egg "Capstone Club")
    FW = RY - 0.03
    p.prop("SM_Banner3x1", 0, FW, 2.85, yaw=180, folder="FarWall", overrides={"MI_Banner": "MI_ClubBanner"},
           label="Banner_CapstoneClub", scale=1.35)
    p.prop("SM_FrameFlag", -4.6, FW, 2.45, yaw=180, folder="FarWall", overrides={"MI_Canvas": "MI_TeamPhoto"}, label="TeamPhoto")
    p.prop("SM_FramePortrait", 4.4, FW, 2.4, yaw=180, folder="FarWall", overrides={"MI_Canvas": "MI_ClubTenets"},
           label="Poster_Tenets", scale=1.3)
    p.prop("SM_FrameFlag", -7.9, FW, 2.6, yaw=180, folder="FarWall", label="Flag_Taegukgi", scale=0.8)
    p.prop("SM_Door", 9.0, FW, 0, yaw=180, folder="FarWall")
    p.prop("SM_ExitSign", 9.0, FW - 0.02, 2.35, yaw=180, folder="FarWall")
    # club mates on benches along the walls, watching
    for i, (x, var) in enumerate(((-3.3, "B"), (1.6, "A"))):
        p.prop(f"SM_BenchClubMates_{var}", x, RY - 0.55, 0, yaw=180, folder="ClubMates", label=f"ClubMates_Far_{i}")
    for i, (y, var) in enumerate(((-3.4, "A"), (3.4, "B"))):
        p.prop(f"SM_BenchClubMates_{var}", RX - 0.55, y, 0, yaw=90, folder="ClubMates", label=f"ClubMates_Window_{i}")
    # equipment corner
    p.prop("SM_WallRack", -6.2, FW, 0.5, yaw=180, folder="Equipment", scale=0.9)
    for col in range(5):
        p.prop("SM_KickPaddle", -6.2 - 0.5 + col * 0.25, FW - 0.1, 0.5 + 0.95 - 0.34, yaw=180, folder="Equipment",
               label=f"Paddle_{col}")
    p.prop("SM_ShoeCubby", -8.9, FW - 0.2, 0, yaw=180, folder="Equipment", scale=0.9)
    for i, (x, y) in enumerate(((-9.3, 6.0), (-9.3, -6.2))):
        p.prop("SM_HeavyBagStanding", x, y, 0, folder="Equipment", label=f"HeavyBag_{i}")

    # mirror wall (-X): pads at the base, mirror above
    for i in range(16):
        p.prop("SM_WallPad", -RX + 0.05, -RY + 0.5 + i * 1.0, 0, yaw=-90, folder="MirrorWall", label=f"WallPad_{i}")
    p.box("Mirror", 0.02, 2 * RY - 0.8, 2.3, -RX + 0.02, 0, 0.6 + 1.25, "MI_Mirror", "MirrorWall")
    p.box("MirrorTrim_Top", 0.06, 2 * RY - 0.8, 0.08, -RX + 0.03, 0, 3.0, "MI_WoodWall", "MirrorWall")
    p.prop("SM_FrameLandscape", -RX + 0.03, 0, 3.75, yaw=-90, folder="MirrorWall", overrides={"MI_Canvas": "MI_Canvas_Kicker"},
           label="Banner_Kicker", scale=0.75)

    # window wall (+X): night outside
    windows_wall(p, "East", "x", RX, (-RY, RY), 0, RZ, "MI_Plaster", "MI_WindowNight", 1.0, [-5.4, -1.8, 1.8, 5.4], scale=0.95)

    # ceiling: linear LEDs and the light they give
    for x in range(-8, 9, 4):
        for y in (-5.4, -1.8, 1.8, 5.4):
            p.prop("SM_LedLinear", x, y, RZ, folder="Ceiling", label=f"Led_{x}_{y}")
    for x in (-6, 0, 6):
        for y in (-4, 0, 4):
            rl = light(unreal.RectLight, f"CeilingLight_{x}_{y}", x, y, RZ - 0.1, pitch=-90)
            set_light(rl.rect_light_component, 20000.0, (0.97, 0.98, 1.0), radius=14.0, cast_shadows=(x == 0 and y == 0),
                      units=LU, source_width=M(4), source_height=M(2))
    sky_light(0.25)
    post_process("PostProcess", bias=0.3, min_b=3.0, max_b=10.0, bloom=0.35, vignette=0.25)
    finish_level((0.0, -7.6, 1.8), (0, -6, 90))
    log("club actors", p.count)


# ------------------------------------------------------------------ tier 2: school gym (city open)
def build_gym(p):
    new_level("/Game/Maps/L_SchoolGym")
    HX, HY, HZ = 18.0, 17.0, 9.0
    rng = random.Random(2)
    p.box("FloorBase", 2 * HX + 1, 2 * HY + 1, 0.2, 0, 0, -0.1, "MI_WoodFloor")
    p.prop("SM_FloorDecal36", 0, 0, 0.003, folder="Architecture", label="CourtFloor")
    p.box("Wall_E", 0.4, 2 * HY, HZ, HX + 0.2, 0, HZ / 2, "MI_GymWall")
    p.box("Wall_W", 0.4, 2 * HY, HZ, -HX - 0.2, 0, HZ / 2, "MI_GymWall")
    p.box("Ceiling", 2 * HX + 1, 2 * HY + 1, 0.3, 0, 0, HZ + 0.15, "MI_DuctMetal")
    # long walls with clerestory windows above the bleachers
    win = [-15.0, -9.0, -3.0, 3.0, 9.0, 15.0]
    windows_wall(p, "North", "y", HY, (-HX, HX), 0, HZ, "MI_GymWall", "MI_WindowView", 5.9, win, view_offset=6.0)
    windows_wall(p, "South", "y", -HY, (-HX, HX), 0, HZ, "MI_GymWall", "MI_WindowView", 5.9, win, view_offset=6.0)
    for label, y in (("N", HY), ("S", -HY)):
        p.box(f"WallBand_{label}", 2 * HX, 0.05, 0.3, 0, y - math.copysign(0.03, y), 2.6, "MI_PadGreen", "Architecture")

    # taekwondo contest area laid over the basketball court
    contest_area(p, z=0.004)
    # basketball hoops (raised) and wall padding on the end walls
    for sx in (-1, 1):
        p.prop("SM_BasketballHoop", sx * HX, 0, 0, yaw=90 * sx, folder="Gym", label=f"Hoop_{sx}")
        p.box(f"EndPads_{sx}", 0.1, 14.0, 2.0, sx * (HX - 0.05), 0, 1.0, "MI_PadGreen", "Gym")
        p.prop("SM_Door", sx * (HX - 0.02), -HY + 2.0, 0, yaw=90 * sx, folder="Gym", label=f"Door_{sx}")
        p.prop("SM_ExitSign", sx * (HX - 0.04), -HY + 2.0, 2.35, yaw=90 * sx, folder="Gym", label=f"Exit_{sx}")
    p.prop("SM_ScoreboardGymWall", 0, HY - 0.02, 4.0, yaw=180, folder="Gym", label="GymScoreboard")
    for sx in (-1, 1):
        p.prop("SM_Banner3x1", sx * 10.5, HY - 0.05, 4.3, yaw=180, folder="Gym", overrides={"MI_Banner": "MI_Banner_City"},
               label=f"Banner_CityOpen_{sx}", scale=1.2)
        p.prop("SM_ScoreboardPortable", sx * 11.0, 8.2, 0, yaw=face_yaw(sx * 11.0, 8.2), folder="ContestArea",
               label=f"Scoreboard_Portable_{sx}")

    # pulled-out bleachers along both long walls (a few hundred spectators)
    back = 7.5 * BL_D + BL_D / 2
    for side, sy, yaw in (("N", 1, 180), ("S", -1, 0)):
        for i, x in enumerate((-12.0, -4.0, 4.0, 12.0)):
            occ = "Half" if (i + (side == "S")) % 2 == 0 else "Sparse"
            a = p.prop(f"SM_Bleacher_{occ}", x, sy * (HY - 0.3 - back), 0, yaw=yaw, folder=f"Bleachers/{side}",
                       overrides=crowd_overrides(rng, "MI_SeatDark"), label=f"Bleacher_{side}_{i}")
            if rng.random() < 0.5:
                a.set_actor_scale3d(unreal.Vector(-1, 1, 1))

    # roof trusses and high-bay lights
    for i, x in enumerate(range(-16, 17, 4)):
        for j in range(8):
            p.prop("SM_Truss4m", x, -14 + j * 4, HZ - 0.6, yaw=90, folder="Roof", label=f"Truss_{i}_{j}")
    for x in (-12, -4, 4, 12):
        for y in (-8, 0, 8):
            p.prop("SM_HighBay", x, y, HZ - 0.4, folder="Roof", label=f"HighBay_{x}_{y}")
            sp = light(unreal.SpotLight, f"HighBay_{x}_{y}", x, y, HZ - 1.45, pitch=-90)
            set_light(sp.spot_light_component, 32000.0, (1.0, 0.97, 0.9), radius=30.0, cast_shadows=abs(x) < 5 and y == 0,
                      units=LU, inner_cone_angle=30.0, outer_cone_angle=60.0)
    sun(-38, 30, 6.0)
    sky_light(0.8, realtime=True)
    post_process("PostProcess", bias=-0.2, min_b=4.0, max_b=11.0, bloom=0.4, vignette=0.25)
    finish_level((0.0, -10.0, 3.2), (0, -10, 90))
    log("gym actors", p.count)



# ------------------------------------------------------------------ tier 3: provincial hall (several mats at once)
def build_provincial(p):
    new_level("/Game/Maps/L_ProvincialHall")
    rng = random.Random(3)
    HX, HZ = 38.0, 13.0
    COURTS = (-18.0, 0.0, 18.0)
    NEAR, WARM0, WARM1, FAR = 12.0, 12.6, 20.0, 21.0
    p.box("Floor", 2 * HX + 1, 70, 0.2, 0, 4, -0.1, "MI_HallFloor")
    south = stands(p, "Lower", [("S", NEAR, HX - 4)], 12, 1.0, lambda b, i: "Half" if (b + i) % 3 else "Sparse", rng,
                   seat_mat="MI_SeatBlue", riser_mat="MI_HallWall")
    north = stands(p, "Far", [("N", FAR, HX - 4)], 12, 1.4, lambda b, i: "Half" if (b * 3 + i) % 4 else "Sparse", rng,
                   seat_mat="MI_SeatBlue", riser_mat="MI_HallWall")
    shell(p, -HX, HX, -south - 0.5, north + 0.5, HZ, "MI_HallFloor", "MI_HallWall", "MI_DuctMetal", floor=False)

    # three contest areas side by side, each with its own officials, coaches, scoreboards and court sign
    for n, cx in enumerate(COURTS, 1):
        f = f"Court{n}"
        p.prop("SM_MatOctagon", cx, 0, 0, folder=f"{f}/Mat", label=f"{f}_MatOctagon")
        p.prop("SM_MatSquareBorder", cx, 0, 0, folder=f"{f}/Mat", label=f"{f}_MatBorder")
        table_group(p, f"{f}_Far", cx, 9.0, 2, f)
        table_group(p, f"{f}_Near", cx, -9.0, 1, f)
        coach_corners(p, cx, x=7.4, y=5.6, folder=f"{f}/CoachCorner")
        for sx in (-1, 1):
            p.prop("SM_ScoreboardPortable", cx + sx * 7.4, 8.4, 0, yaw=face_yaw(cx + sx * 7.4, 8.4, cx, 0), folder=f,
                   label=f"{f}_Scoreboard_{sx}")
        p.prop("SM_CourtSign", cx - 7.6, -7.6, 0, yaw=face_yaw(cx - 7.6, -7.6, cx, -30), folder=f,
               overrides={"MI_CourtNumber": f"MI_CourtNumber{n}"}, label=f"{f}_Sign")
    # printed boards: dividers between courts, and the line between the courts and the warm-up area
    for gx in (-9.0, 9.0):
        for i in range(5):
            y = -6.4 + i * 3.2
            p.prop("SM_AdBoard", gx - 0.06, y, 0, yaw=90, folder="Boards", overrides={"MI_Ad": "MI_Ad_Provincial"}, label=f"Div_{gx}_{i}_a")
            p.prop("SM_AdBoard", gx + 0.06, y, 0, yaw=-90, folder="Boards", overrides={"MI_Ad": "MI_Ad_Provincial"}, label=f"Div_{gx}_{i}_b")
    for i in range(21):
        p.prop("SM_AdBoard", -32.0 + i * 3.2, 11.6, 0, yaw=180, folder="Boards", overrides={"MI_Ad": "MI_Ad_Provincial"},
               label=f"WarmupLine_{i}")

    # busy warm-up area behind the courts
    p.box("WarmupMats", 2 * HX - 6, WARM1 - WARM0, 0.03, 0, (WARM0 + WARM1) / 2, 0.015, "MI_WarmupMat", "Warmup")
    spots = [(-31.0, 15.8), (-24.5, 17.6), (-17.0, 15.2), (-10.5, 17.9), (-3.0, 15.5), (4.0, 17.4), (10.5, 15.0),
             (17.5, 17.6), (24.0, 15.3), (31.0, 17.2)]
    for i, (x, y) in enumerate(spots):
        p.prop(f"SM_WarmupGroup_{'AB'[i % 2]}", x, y, 0.03, yaw=rng.uniform(-40, 40) + (180 if i % 3 == 0 else 0),
               folder="Warmup", label=f"WarmupGroup_{i}")
    for i, x in enumerate((-28.0, -14.0, 7.5, 21.0, 34.0)):
        p.prop("SM_HeavyBagStanding", x, 19.0, 0.03, folder="Warmup", label=f"HeavyBag_{i}")
    for i, x in enumerate((-35.5, -20.5, -6.5, 0.6, 13.5, 27.5)):
        p.prop(f"SM_BenchClubMates_{'AB'[i % 2]}", x, 20.4, 0, yaw=180, folder="Warmup", label=f"WaitingAthletes_{i}")
    for i, x in enumerate((-36.5, 36.5)):
        for k in range(3):
            p.prop("SM_ChairStackBlack", x, 14.0 + k * 0.6, 0.03, yaw=-90 if x < 0 else 90, folder="Warmup", label=f"WarmupChair_{i}_{k}")

    # event banners on the end walls and above the far stand
    for sx in (-1, 1):
        p.prop("SM_Banner3x1", sx * (HX - 0.05), 0, 4.5, yaw=90 * sx, folder="Banners",
               overrides={"MI_Banner": "MI_Banner_Provincial"}, label=f"Banner_End_{sx}", scale=2.6)
    for i, x in enumerate((-20.0, 0.0, 20.0)):
        p.prop("SM_Banner3x1", x, north + 0.45, 8.6, yaw=180, folder="Banners", overrides={"MI_Banner": "MI_Banner_Provincial"},
               label=f"Banner_Far_{i}", scale=1.6)

    # roof: trusses and high bays over the whole floor, brighter over the courts
    for i, x in enumerate(range(-36, 37, 6)):
        for j in range(9):
            p.prop("SM_Truss4m", x, -14 + j * 4 + 2, HZ - 1.0, yaw=90, folder="Roof", label=f"Truss_{i}_{j}")
    for x in range(-30, 31, 10):
        for y in (-16.0, 16.0):
            p.prop("SM_HighBay", x, y, HZ - 0.8, folder="Roof", label=f"HighBay_{x}_{y}")
            sp = light(unreal.SpotLight, f"HighBay_{x}_{y}", x, y, HZ - 1.85, pitch=-90)
            set_light(sp.spot_light_component, 40000.0, (1.0, 0.98, 0.95), radius=30.0, cast_shadows=False, units=LU,
                      inner_cone_angle=35.0, outer_cone_angle=65.0)
    for cx in COURTS:
        for x in (-4.0, 4.0):
            for y in (-4.0, 4.0):
                p.prop("SM_HighBay", cx + x, y, HZ - 0.8, folder="Roof", label=f"CourtBay_{cx}_{x}_{y}")
                sp = light(unreal.SpotLight, f"CourtLight_{cx}_{x}_{y}", cx + x, y, HZ - 1.85, pitch=-90)
                set_light(sp.spot_light_component, 55000.0, (1.0, 0.98, 0.95), radius=30.0, cast_shadows=cx == 0,
                          units=LU, inner_cone_angle=25.0, outer_cone_angle=45.0)
    sky_light(0.35)
    post_process("PostProcess", bias=0.2, min_b=4.0, max_b=10.0, bloom=0.4, vignette=0.25)
    finish_level((0.0, -16.0, 4.5), (0, -11, 90))
    log("provincial actors", p.count)


# ------------------------------------------------------------------ arena bowls (tiers 4-6)
def bowl(p, rng, floor_half, lower_rows, upper_rows, lower_occ, upper_occ, seat_mat, ribbon_mi, concourse=2.5):
    """Lower and upper tiers on all four sides, a concourse between them with an LED ribbon on the upper
    tier's fascia. Returns the outer wall distance."""
    first = 1.2
    specs = [(s, floor_half + 1.0, floor_half) for s in "NSEW"]
    lower_end = stands(p, "Lower", specs, lower_rows, first, lower_occ, rng, seat_mat=seat_mat)
    lower_top = first + (lower_rows - 1) * STEP_H
    up_edge = lower_end + concourse
    up_first = lower_top + 2.6
    for side in "NSEW":
        dx, dy, yaw = SIDES[side]
        c = lower_end + concourse / 2
        along = 2 * (floor_half + lower_end - floor_half + concourse)
        if dy:
            p.box(f"Concourse_{side}", along, concourse, 0.3, 0, dy * c, lower_top - 0.15, "MI_ArenaRiser", "Stands/Concourse")
        else:
            p.box(f"Concourse_{side}", concourse, along, 0.3, dx * c, 0, lower_top - 0.15, "MI_ArenaRiser", "Stands/Concourse")
    upper_specs = [(s, up_edge, floor_half + (up_edge - floor_half) * 0.5) for s in "NSEW"]
    outer = stands(p, "Upper", upper_specs, upper_rows, up_first, upper_occ, rng, seat_mat=seat_mat, barrier=False)
    # LED ribbon along the upper tier's fascia, facing the floor
    ring(p, "Ribbon", [(s, up_edge, up_edge - 2.0) for s in "NSEW"], "SM_LedRibbon", 8.0, lower_top + 0.6, 0.02,
         overrides={"MI_Ribbon": ribbon_mi}, folder="Stands/Ribbon")
    return outer, lower_top, up_first


def arena_room(p, outer, height):
    W = outer + 0.6
    p.box("Floor", 2 * W, 2 * W, 0.2, 0, 0, -0.1, "MI_ArenaFloor")
    shell(p, -W, W, -W, W, height, "MI_ArenaFloor", "MI_ArenaWall", "MI_ArenaCeiling", floor=False)
    return W


def raised_stage(p, steps=("W", "E"), led=None):
    o = {"MI_StageLed": led} if led else None
    p.prop("SM_RaisedStage", 0, 0, 0, folder="ContestArea/Stage", overrides=o, label="RaisedStage")
    for s in steps:
        dx, dy, _ = SIDES[s]
        yaw = {"W": 90, "E": -90, "N": 180, "S": 0}[s]   # steps' front faces away from the stage
        p.prop("SM_StageSteps", dx * 7.0, dy * 7.0, 0, yaw=yaw, folder="ContestArea/Stage", label=f"Steps_{s}")


def perimeter_boards(p, floor_half, mi_name):
    ring(p, "Boards", [(s, floor_half + 0.6, floor_half - 1.0) for s in "NSEW"], "SM_AdBoard", 3.2, 0, 0.0,
         overrides={"MI_Ad": mi_name}, folder="Boards")


def broadcast_cameras(p, spots):
    for i, (x, y, platform) in enumerate(spots):
        z = 0.0
        if platform:
            p.box(f"CameraRiser_{i}", 1.6, 1.6, 0.5, x, y, 0.25, "MI_BlackFabric", "Broadcast")
            z = 0.5
        p.prop("SM_BroadcastCamera", x, y, z, yaw=face_yaw(x, y) + 180, folder="Broadcast", label=f"Camera_{i}")


def build_national(p):
    new_level("/Game/Maps/L_NationalArena")
    rng = random.Random(4)
    FLOOR = 16.0
    outer, lower_top, up_first = bowl(p, rng, FLOOR, 12, 12, lambda b, i: "Full",
                                      lambda b, i: ("Sparse", "Empty", "Sparse", "Half")[(b + i) % 4], "MI_SeatNavy",
                                      "MI_Ribbon_National")
    arena_room(p, outer, 28.0)
    raised_stage(p)
    contest_area(p, z=0.6, officials="none")
    for label, cx, cy, n in (("FarLeft", -7.0, 9.5, 2), ("FarCentre", 0.0, 9.5, 1), ("FarRight", 7.0, 9.5, 3),
                             ("NearLeft", -9.8, -7.4, 3), ("NearRight", 9.8, -7.4, 3)):
        table_group(p, label, cx, cy, n, "ContestArea")
    coach_corners(p, x=8.4, y=5.6)
    perimeter_boards(p, FLOOR, "MI_AdLed_National")
    broadcast_cameras(p, [(-12.5, -12.5, True), (13.0, 12.5, False)])
    # centre-hung video cube and wall screens
    p.prop("SM_VideoCube", 0, 0, 18.0, folder="Screens", overrides={"MI_ScreenEvent": "MI_ScreenEvent_National"}, label="VideoCube")
    for sy in (-1, 1):
        p.prop("SM_Scoreboard", 0, sy * (outer + 0.2), 17.0, yaw=0 if sy < 0 else 180, folder="Screens", scale=2.0,
               label=f"WallScoreboard_{sy}")
    # rig and light: bright, even key over the stage; the bowl falls off into the dark
    truss_grid(p, "Main", 8.0, 15.0)
    spot_grid(p, "Key", (-6, -2, 2, 6), (-6, -2, 2, 6), 15.0 - 0.15, 350000.0)    # ~1500 lux on the mat (Unreal spot lumens are over 4 pi sr)
    stand_fill(p, FLOOR, outer, 25.0, 4000000.0)      # house ~600 lux, about 1/3 of the mat, as broadcast lighting
    haze(0.004, unreal.LinearColor(0.02, 0.022, 0.03, 1))
    sky_light(0.12)
    post_process("PostProcess", bias=0.0, min_b=10.8, max_b=10.8, bloom=0.5, vignette=0.35)
    finish_level((0.0, -19.0, 6.0), (0, -13, 90))
    log("national actors", p.count)


def build_continental(p):
    new_level("/Game/Maps/L_ContinentalArena")
    rng = random.Random(5)
    FLOOR = 18.0
    outer, lower_top, up_first = bowl(p, rng, FLOOR, 18, 12, lambda b, i: "Full",
                                      lambda b, i: "Full" if (b + i) % 3 else "Half", "MI_SeatBlue",
                                      "MI_Ribbon_Continental")
    arena_room(p, outer, 32.0)
    raised_stage(p)
    contest_area(p, z=0.6, officials="none")
    for label, cx, cy, n in (("FarLeft", -7.0, 9.5, 2), ("FarCentre", 0.0, 9.5, 1), ("FarRight", 7.0, 9.5, 3),
                             ("NearLeft", -9.8, -7.4, 3), ("NearRight", 9.8, -7.4, 3)):
        table_group(p, label, cx, cy, n, "ContestArea")
    coach_corners(p, x=8.4, y=5.6)
    perimeter_boards(p, FLOOR, "MI_AdLed_Continental")
    # broadcast: cameras on risers in every corner and behind the far tables, a jib on the near side
    broadcast_cameras(p, [(-14.0, -14.0, True), (14.0, -14.0, True), (-14.0, 14.0, True), (14.0, 14.0, True),
                          (0.0, 14.5, True), (-15.5, 0.0, False), (15.5, 0.0, False)])
    p.prop("SM_CameraJib", -12.5, -10.5, 0, yaw=face_yaw(-12.5, -10.5) + 180, folder="Broadcast", label="CameraJib")
    # competing nations' flags hung above the lower tier
    codes = FLAG_CODES[:]
    rng.shuffle(codes)
    ring(p, "Flags", [(s, FLOOR + 7.0, FLOOR + 4.0) for s in "NSEW"], "SM_FlagHanging", 2.6, 13.0, 0.0,
         cycle=[{"MI_Flag": f"MI_Flag_{c}"} for c in codes], folder="Flags")
    p.prop("SM_VideoCube", 0, 0, 20.0, folder="Screens", overrides={"MI_ScreenEvent": "MI_ScreenEvent_Continental"},
           label="VideoCube", scale=1.3)
    for side in "NSEW":
        dx, dy, yaw = SIDES[side]
        p.prop("SM_EventScreen", dx * (outer + 0.25), dy * (outer + 0.25), 19.0, yaw=yaw, folder="Screens",
               overrides={"MI_ScreenEvent": "MI_ScreenEvent_Continental"}, label=f"WallScreen_{side}")
    truss_grid(p, "Main", 8.0, 16.0)
    spot_grid(p, "Key", (-6, -2, 2, 6), (-6, -2, 2, 6), 16.0 - 0.15, 400000.0)    # ~1500 lux on the mat
    stand_fill(p, FLOOR, outer, 28.0, 5000000.0)                                       # louder, brighter house
    haze(0.004, unreal.LinearColor(0.02, 0.022, 0.03, 1))
    sky_light(0.15)
    post_process("PostProcess", bias=0.0, min_b=10.8, max_b=10.8, bloom=0.5, vignette=0.35)
    finish_level((0.0, -21.0, 6.5), (0, -13, 90))
    log("continental actors", p.count)


def build_world(p):
    new_level("/Game/Maps/L_WorldFinalStage")
    rng = random.Random(6)
    FLOOR = 20.0
    outer, lower_top, up_first = bowl(p, rng, FLOOR, 18, 12, lambda b, i: "Full", lambda b, i: "Full", "MI_SeatDark",
                                      "MI_Ribbon_World")
    arena_room(p, outer, 34.0)
    raised_stage(p, led="MI_StageLedGold")
    contest_area(p, z=0.6, officials="none")
    for label, cx, cy, n in (("FarLeft", -7.0, 9.5, 2), ("FarCentre", 0.0, 9.5, 1), ("FarRight", 7.0, 9.5, 3),
                             ("NearLeft", -9.8, -7.4, 3), ("NearRight", 9.8, -7.4, 3)):
        table_group(p, label, cx, cy, n, "ContestArea")
    coach_corners(p, x=8.4, y=5.6)
    perimeter_boards(p, FLOOR, "MI_AdLed_World")
    broadcast_cameras(p, [(-15.0, -15.0, True), (15.0, -15.0, True), (0.0, 16.0, True), (15.0, 15.0, True)])
    p.prop("SM_CameraJib", 13.0, -11.0, 0, yaw=face_yaw(13.0, -11.0) + 180, folder="Broadcast", label="CameraJib")

    # entrance walk: arch at the west end of the floor, runway to the stage steps
    p.prop("SM_EntranceArch", -(FLOOR - 0.9), 0, 0, yaw=-90, folder="Entrance", label="EntranceArch")
    p.box("Entrance_Backdrop", 0.3, 7.0, 7.0, -(FLOOR - 0.3), 0, 3.5, "MI_StageSkirt", "Entrance")
    p.prop("SM_Runway", -(FLOOR - 0.9 + 7.5) / 2, 0, 0, yaw=90, folder="Entrance", label="Runway", scale=(1.0, 1.08, 1.0))
    for i, x in enumerate(range(-17, -8, 3)):
        for sy in (-1, 1):
            p.prop("SM_MovingHead", x, sy * 1.6, 0.5, pitch=180, folder="Entrance", label=f"RunwayUplight_{i}_{sy}", scale=0.8)
            up = light(unreal.SpotLight, f"RunwayBeam_{i}_{sy}", x, sy * 1.6, 0.6, pitch=80)
            set_light(up.spot_light_component, 120000.0, (0.25, 0.45, 1.0) if sy < 0 else (1.0, 0.2, 0.15), radius=25.0,
                      cast_shadows=False, units=LU, inner_cone_angle=3.0, outer_cone_angle=6.0, volumetric_scattering_intensity=4.0)
    # podium beside the far tables, ready for the medal ceremony
    p.prop("SM_Podium", 13.5, 13.0, 0, yaw=180, folder="Ceremony", label="Podium")
    p.prop("SM_VideoCube", 0, 0, 21.0, folder="Screens", overrides={"MI_ScreenEvent": "MI_ScreenEvent_World", "MI_StageLed": "MI_StageLedGold"},
           label="VideoCube", scale=1.4)
    for side in "NS":
        dx, dy, yaw = SIDES[side]
        p.prop("SM_EventScreen", 0, dy * (outer + 0.25), 20.0, yaw=yaw, folder="Screens",
               overrides={"MI_ScreenEvent": "MI_ScreenEvent_World"}, label=f"WallScreen_{side}", scale=1.3)

    # darkened arena: tight white key on the stage, blue and red beams from the rig, the crowd barely lit
    truss_grid(p, "Main", 8.0, 14.0)
    spot_grid(p, "Key", (-4.5, 0, 4.5), (-4.5, 0, 4.5), 14.0 - 0.15, 500000.0, cone=(14.0, 24.0), shadow_radius=5.0,
              scatter=1.5)
    for i, (x, y) in enumerate([(x, y) for x in (-8, 8) for y in (-6, -2, 2, 6)] + [(x, y) for y in (-8, 8) for x in (-4, 0, 4)]):
        blue = x < 0 or (x == 0 and y < 0)
        p.prop("SM_MovingHead", x, y, 14.0 - 0.3, folder="Rig/MovingHeads", label=f"MovingHead_{i}")
        # beams sweep out over the crowd through the haze, so they colour the air, not the mat
        ang = math.atan2(y, x) + rng.uniform(-0.5, 0.5)
        reach = FLOOR + rng.uniform(4.0, 14.0)
        aim_x, aim_y = reach * math.cos(ang), reach * math.sin(ang)
        dist = math.hypot(aim_x - x, aim_y - y)
        pitch = -math.degrees(math.atan2(13.0 - rng.uniform(2.0, 7.0), dist))
        yaw = math.degrees(math.atan2(aim_y - y, aim_x - x))
        sp = light(unreal.SpotLight, f"Beam_{i}", x, y, 13.1, pitch=pitch, yaw=yaw)
        set_light(sp.spot_light_component, 50000.0, (0.15, 0.35, 1.0) if blue else (1.0, 0.12, 0.1), radius=40.0,
                  cast_shadows=False, units=LU, inner_cone_angle=4.0, outer_cone_angle=8.0, volumetric_scattering_intensity=3.0)
    stand_fill(p, FLOOR, outer, 30.0, 1600000.0, color=(0.6, 0.66, 1.0))   # darkened house: silhouettes only
    haze(0.012, unreal.LinearColor(0.004, 0.005, 0.01, 1))
    sky_light(0.03)
    post_process("PostProcess", bias=0.0, min_b=10.6, max_b=10.6, bloom=0.8, vignette=0.45)
    finish_level((0.0, -22.0, 6.0), (0, -12, 90))
    log("world actors", p.count)


BUILDERS = {"club": build_club, "gym": build_gym, "provincial": build_provincial, "national": build_national,
            "continental": build_continental, "world": build_world}

try:
    which = [a for a in sys.argv[1:] if a in BUILDERS] or list(BUILDERS)
    tex = import_new_textures()
    meshes = import_new_meshes()
    mi = build_venue_materials(tex, load_materials())
    for name in which:
        BUILDERS[name](Placer(meshes, mi))
    log("DONE", which)
except Exception:
    log("ERROR\n" + traceback.format_exc())
finally:
    env_common.close_log()
