"""Shared helpers for the venue level scripts (build_arenas.py, build_venues.py).

Layout units are metres; Unreal is centimetres (M() converts). Blender props face -Y in Blender, which is
+Y in Unreal; a prop's front after a yaw is (-sin yaw, cos yaw).
"""
import math
import os

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
TEX_SRC = f"{REPO}/Resources/Environment/Textures"
MESH_SRC = f"{REPO}/Resources/Environment/Meshes"
ENV = "/Game/Environment"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

_log = {"file": None, "tag": "env"}


def open_log(name):
    """Logs go to Saved/Logs/<name>.txt and the Output Log."""
    _log["file"] = open(f"{REPO}/Saved/Logs/{name}.txt", "w", encoding="utf-8")
    _log["tag"] = name
    return log


def close_log():
    if _log["file"]:
        _log["file"].close()
        _log["file"] = None


def log(*a):
    msg = " ".join(str(x) for x in a)
    if _log["file"]:
        _log["file"].write(msg + "\n")
        _log["file"].flush()
    unreal.log(f"[{_log['tag']}] {msg}")


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


def face_yaw(x, y, tx=0.0, ty=0.0):
    """Yaw (degrees) that turns a prop at (x, y) to face the point (tx, ty)."""
    return math.degrees(math.atan2(-(tx - x), ty - y))


# ------------------------------------------------------------------ assets
def import_task(filename, dest, name, options=None):
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = filename, dest, name
    t.automated, t.replace_existing, t.save = True, True, True
    if options:
        t.options = options
    tools.import_asset_tasks([t])
    return EAL.load_asset(f"{dest}/{name}")


def asset_file(path):
    """/Game/X/Y -> Content/X/Y.uasset on disk."""
    return f"{REPO}/Content/{path[len('/Game/'):]}.uasset"


def is_locked(path):
    """True for an existing asset whose file is read-only (Perforce: synced, not checked out)."""
    f = asset_file(path)
    return os.path.exists(f) and not os.access(f, os.W_OK)


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


def instance(name, parent, scalars=None, vectors=None, textures=None):
    path = f"{ENV}/Materials/{name}"
    if is_locked(path):   # synced read-only from Perforce: use as is
        return EAL.load_asset(path)
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


# ------------------------------------------------------------------ crowds
# colour slots on the crowd meshes (Tools/Blender/build_venue_meshes.py); materials made by build_venues.py
CROWD_SLOTS = (("MI_CrowdShirt", 8), ("MI_CrowdPants", 3), ("MI_CrowdSkin", 5), ("MI_CrowdHair", 4))


def crowd_overrides(rng, seat_mat):
    """Shuffle the crowd colour slots per block so neighbouring blocks never look copied."""
    o = {"MI_SeatDark": seat_mat}
    for prefix, n in CROWD_SLOTS:
        order = list(range(n))
        rng.shuffle(order)
        for i, j in enumerate(order):
            o[f"{prefix}{i}"] = f"{prefix}{j}"
    return o


# ------------------------------------------------------------------ placement
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
            a.set_actor_scale3d(unreal.Vector(scale, scale, scale) if not isinstance(scale, tuple) else unreal.Vector(*scale))
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
    """Start an empty level at `path`. An existing map is opened and cleared rather than deleted: deleting a map
    can fail (references, headless editor), and new_level refuses a path that still holds an asset."""
    if EAL.does_asset_exist(path):
        levels.load_level(path)
        actors.destroy_actors([a for a in actors.get_all_level_actors()
                               if not isinstance(a, (unreal.WorldSettings, unreal.Brush))])
        log("cleared level", path)
    else:
        levels.new_level(path)
        log("new level", path)
