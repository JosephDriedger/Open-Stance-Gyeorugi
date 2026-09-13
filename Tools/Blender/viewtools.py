"""Viewport helpers for inspecting the rig from the Python console (loaded via run("viewtools"))."""
import math
import bpy
from mathutils import Quaternion, Vector

VIEWS = {
    'FRONT': Quaternion((math.sqrt(0.5), math.sqrt(0.5), 0, 0)),   # looking along +Y
    'BACK': Quaternion((0, 0, math.sqrt(0.5), math.sqrt(0.5))),
    'RIGHT': Quaternion((0.5, 0.5, 0.5, 0.5)),                      # looking along -X
    'LEFT': Quaternion((0.5, 0.5, -0.5, -0.5)),
    'TOP': Quaternion((1, 0, 0, 0)),
    'THREE_QUARTER': Quaternion((0.78, 0.53, -0.2, -0.26)),
}
PART_NAMES = ["Head", "BodySkin", "Helmet", "Protector", "Jacket", "Pants", "Belt", "Gloves", "FootGuards"]


def view3d_area():
    """The largest 3D viewport in the window."""
    areas = [a for win in bpy.context.window_manager.windows for a in win.screen.areas if a.type == 'VIEW_3D']
    return max(areas, key=lambda a: a.width * a.height) if areas else None


def look(center=(0, 0, 0.85), dist=2.2, view='FRONT', ortho=True):
    """Point the viewport at center. view is a VIEWS key or a Quaternion."""
    area = view3d_area()
    r3d = area.spaces.active.region_3d
    r3d.view_rotation = VIEWS[view] if isinstance(view, str) else view
    r3d.view_location = Vector(center)
    r3d.view_distance = dist
    r3d.view_perspective = 'ORTHO' if ortho else 'PERSP'
    area.tag_redraw()


def material_preview():
    view3d_area().spaces.active.shading.type = 'MATERIAL'


def xray(on=True, alpha=0.35):
    shading = view3d_area().spaces.active.shading
    shading.show_xray = on
    shading.xray_alpha = alpha


def bones_in_front(on=True):
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            o.show_in_front = on
            o.data.display_type = 'OCTAHEDRAL'


def show_bone_names(on=True):
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            o.data.show_names = on


def part(name):
    return bpy.data.objects[f"SK_Fighter_{name}"]


def show_parts(*names, hide_others=False):
    """Unhide the named parts (all parts if none given)."""
    for n in PART_NAMES:
        o = bpy.data.objects.get(f"SK_Fighter_{n}")
        if o:
            o.hide_set(False if (not names or n in names) else hide_others)


def show_colour_attribute(name):
    """Solid shading coloured by a colour attribute (e.g. viz_part, viz_patch) on every mesh that has it."""
    for o in bpy.data.objects:
        if o.type == 'MESH' and name in o.data.color_attributes:
            o.data.color_attributes.active_color = o.data.color_attributes[name]
    shading = view3d_area().spaces.active.shading
    shading.type = 'SOLID'
    shading.light = 'FLAT'
    shading.color_type = 'VERTEX'


def set_body(heavy=0.0, muscular=0.0, slim=0.0):
    """Set body-type shape keys on every mesh that has them."""
    for o in bpy.data.objects:
        keys = o.data.shape_keys.key_blocks if o.type == 'MESH' and o.data.shape_keys else None
        if not keys:
            continue
        for kname, val in (("BodyHeavy", heavy), ("BodyMuscular", muscular), ("BodySlim", slim)):
            if kname in keys:
                keys[kname].value = val
