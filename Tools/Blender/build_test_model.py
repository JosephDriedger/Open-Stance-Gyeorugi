"""Build the presentable mocap test fighter: MetaHuman body and head, clean sparring gear, textured, lit.

    blender --background --factory-startup --python Tools/Blender/build_test_model.py -- [Medium]

Inputs (all in Resources/):
    Models/MetaHuman/<asset>_Body.fbx, <asset>_Head.fbx        body and head (eyes, teeth, lashes) on their skeletons
    Models/Fitted/<asset>_Body/SK_Fighter_<Part>.fbx, T_HFM_*    clean gear and its hidden-face maps
    Models/Textures/T_Fighter_*.png                             gear atlas (make_gear_textures.py)
    Models/MetaHuman/Textures/Stock/*.png                       MetaHuman stock skin, eye and teeth maps
                                                                 (Tools/Unreal/export_stock_skin_textures.py)
    Saved/Exports/<type>_ROM_skeleton.fbx                        optional: range-of-motion take
                                                                 (Tools/Unreal/export_fighter_animation_fbx.py)

Everything ends up on ONE skeleton, the MetaHuman body skeleton (metahuman_base_skel, 341 bones), so motion solved
onto this model goes to Unreal unchanged. The head is moved from the face skeleton onto it (facial joints follow the
head bone; facial animation stays in Unreal). Body skin under the gear is removed with the same hidden-face maps
Unreal uses, so nothing pokes through. Helper and corrective bones are kept (Unreal needs them) but put in a hidden
bone collection; only the 72 animated bones show.

Writes Resources/Models/TestFighter/:
    OpenStance_TestFighter_MH.blend   lit scene (studio lights, mat floor, camera), Material Preview, ROM take loaded
    OpenStance_TestFighter_MH.fbx     rest pose, no animation, textures embedded: the MotionBuilder input
    Textures/                         the downsized maps the .blend and FBX use
and Resources/Previews/OpenStance_<type>_Gear_ROM.fbx (same model with the ROM take baked).
Check renders: Saved/Previews/test_model_*.png. Log: Saved/Logs/build_test_model.txt.
"""
import math
import os
import shutil
import sys
import traceback

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TYPE = ARGS[0] if ARGS else "Medium"
ASSET = "MH_FighterBase" if TYPE == "Medium" else f"MH_Fighter{TYPE}"
MH = f"{ROOT}/Resources/Models/MetaHuman"
FITTED = f"{ROOT}/Resources/Models/Fitted/{ASSET}_Body"
GEAR_TEX = f"{ROOT}/Resources/Models/Textures"
STOCK = f"{MH}/Textures/Stock"
ROM = f"{ROOT}/Saved/Exports/{TYPE}_ROM_skeleton.fbx"
OUT = f"{ROOT}/Resources/Models/TestFighter"
TEX_OUT = f"{OUT}/Textures"
NAME = "OpenStance_TestFighter_MH" if TYPE == "Medium" else f"OpenStance_TestFighter_MH_{TYPE}"
PREVIEW_FBX = f"{ROOT}/Resources/Previews/OpenStance_{TYPE}_Gear_ROM.fbx"
CHECK = f"{ROOT}/Saved/Previews"
LOG = f"{ROOT}/Saved/Logs/build_test_model.txt"
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
HFM_PARTS = ["Jacket", "Pants", "Gloves", "FootGuards"]
# head material slots: 0 skin, 1 teeth, 2 saliva, 3/4 eyes, 5 eye shell, 6 eyelashes, 7 eye edge, 8 cartilage
HEAD_KEEP = {0: "Skin_Head", 1: "Teeth", 3: "Eye", 4: "Eye", 6: "Eyelashes"}
SKIN_TARGET_SRGB = (184, 134, 106)        # medium skin tone, matched by both the body and the head maps
MAIN_BONES = (["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]
              + [f"{b}_{s}" for s in "lr" for b in ("clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "ball")]
              + [f"{f}_{j}_{s}" for s in "lr" for f in ("thumb", "index", "middle", "ring", "pinky") for j in ("01", "02", "03")]
              + [f"{f}_metacarpal_{s}" for s in "lr" for f in ("index", "middle", "ring", "pinky")])

os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG, "w").close()


def say(*a):
    with open(LOG, "a") as f:
        f.write(" ".join(str(x) for x in a) + "\n")


def import_fbx(path, anim=False):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=anim, ignore_leaf_bones=False, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


def bind(mesh, arm):
    for mod in list(mesh.modifiers):
        if mod.type == 'ARMATURE':
            mesh.modifiers.remove(mod)
    mw = mesh.matrix_world.copy()
    mesh.parent = arm
    mesh.matrix_world = mw
    mesh.modifiers.new("Armature", 'ARMATURE').object = arm


def drop_objects(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def delete_faces(obj, face_mask):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    doomed = [f for f, m in zip(bm.faces, face_mask) if m]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(doomed)


def face_uv_centres(me):
    uv = np.empty(len(me.loops) * 2, dtype=np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    starts = np.empty(len(me.polygons), dtype=np.int32)
    counts = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", counts)
    sums = np.add.reduceat(uv, starts, axis=0)
    return sums / counts[:, None]


def image_array(path):
    img = bpy.data.images.load(path, check_existing=True)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4), img


# --- textures ----------------------------------------------------------------------------------------------
def prepared(src, name, size, non_color=False):
    """Downsized copy of a texture in TestFighter/Textures (PNG), loaded as a Blender image."""
    os.makedirs(TEX_OUT, exist_ok=True)
    dst = f"{TEX_OUT}/{name}.png"
    img = bpy.data.images.load(src)
    if max(img.size) > size:
        img.scale(size, size * img.size[1] // img.size[0])
    img.filepath_raw = dst
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(dst)
    img.name = name
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img


def mean_skin_linear(img):
    """Mean linear colour of the skin pixels of an albedo (ignoring near-black padding)."""
    small = img.copy()
    small.scale(256, 256)
    px = np.empty(256 * 256 * 4, dtype=np.float32)
    small.pixels.foreach_get(px)
    bpy.data.images.remove(small)
    rgb = px.reshape(-1, 4)[:, :3]
    lum = rgb.mean(axis=1)
    keep = rgb[(lum > 0.04) & (lum < 0.95)]
    return keep.mean(axis=0) if len(keep) else np.array([0.5, 0.5, 0.5])


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# --- materials ---------------------------------------------------------------------------------------------
def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    return m, nt, bsdf


def tex_node(nt, img, uv_name=None, x=-700, y=0):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.location = (x, y)
    if uv_name:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = uv_name
        uvn.location = (x - 250, y)
        nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
    return t


def set_input(bsdf, names, value):
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return


def skin_material(name, albedo, gain, normal=None, roughness=0.5, uv_name=None):
    m, nt, bsdf = principled(name)
    t = tex_node(nt, albedo, uv_name, -900, 200)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.location = (-450, 200)
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(t.outputs["Color"], mul.inputs[6])
    mul.inputs[7].default_value = (*gain, 1.0)
    nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
    set_input(bsdf, ["Roughness"], roughness)
    set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.12)
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    set_input(bsdf, ["Subsurface Scale"], 0.004)
    if normal is not None:
        n = tex_node(nt, normal, uv_name, -900, -250)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-450, -250)
        nm.inputs["Strength"].default_value = 0.6
        if uv_name:
            nm.uv_map = uv_name
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def gear_material(base, surface, weave):
    m, nt, bsdf = principled("M_FighterGear_Chung")
    b = tex_node(nt, base, "UVMap", -900, 300)
    s = tex_node(nt, surface, "UVMap", -900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-600, 0)
    nt.links.new(b.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(s.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[0], bsdf.inputs["Roughness"])
    w = tex_node(nt, weave, "UVWeave", -900, -300)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (-400, -300)
    nm.uv_map = "UVWeave"
    nt.links.new(w.outputs["Color"], nm.inputs["Color"])
    nt.links.new(sep.outputs[1], nm.inputs["Strength"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    set_input(bsdf, ["Sheen Weight", "Sheen"], 0.15)
    return m


def eye_material(sclera, iris):
    """Sclera map with the iris composited at the centre of the eyeball UVs (MetaHuman layout: iris at (0.5, 0.5))."""
    m, nt, bsdf = principled("M_Eye")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.location = (-1500, 0)
    sc = tex_node(nt, sclera, None, -900, 300)
    nt.links.new(uvn.outputs["UV"], sc.inputs["Vector"])
    # iris: scale the UVs about the centre so the iris image fills the iris disc
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    sub.location = (-1300, -200)
    nt.links.new(uvn.outputs["UV"], sub.inputs[0])
    sc_up = nt.nodes.new("ShaderNodeVectorMath")
    sc_up.operation = 'SCALE'
    sc_up.inputs["Scale"].default_value = 1.0 / (2 * IRIS_RADIUS)
    sc_up.location = (-1100, -200)
    nt.links.new(sub.outputs[0], sc_up.inputs[0])
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = 'ADD'
    add.inputs[1].default_value = (0.5, 0.5, 0.0)
    add.location = (-900, -200)
    nt.links.new(sc_up.outputs[0], add.inputs[0])
    ir = nt.nodes.new("ShaderNodeTexImage")
    ir.image = iris
    ir.extension = 'CLIP'
    ir.location = (-700, -200)
    nt.links.new(add.outputs[0], ir.inputs["Vector"])
    # mask: inside the iris disc
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = 'LENGTH'
    length.location = (-1100, -450)
    nt.links.new(sub.outputs[0], length.inputs[0])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.location = (-900, -450)
    ramp.inputs["From Min"].default_value = IRIS_RADIUS * 0.96
    ramp.inputs["From Max"].default_value = IRIS_RADIUS * 1.04
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    nt.links.new(length.outputs["Value"], ramp.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.location = (-400, 100)
    nt.links.new(ramp.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(sc.outputs["Color"], mix.inputs[6])
    nt.links.new(ir.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    set_input(bsdf, ["Roughness"], 0.25)
    set_input(bsdf, ["Coat Weight", "Clearcoat"], 1.0)
    set_input(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.02)
    return m


def flat_material(name, rgb, roughness=0.5):
    m, nt, bsdf = principled(name)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    set_input(bsdf, ["Roughness"], roughness)
    m.diffuse_color = (*rgb, 1.0)
    return m


def textured_material(name, img, roughness=0.4):
    m, nt, bsdf = principled(name)
    t = tex_node(nt, img, None, -500, 200)
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    set_input(bsdf, ["Roughness"], roughness)
    return m


IRIS_RADIUS = 0.105


# --- animation retarget (template proportions -> this fighter), same rule as Tools/Unreal/animation_test.py --
def fcurves_of(obj):
    act = obj.animation_data.action
    if hasattr(act, "fcurves"):
        return act.fcurves
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    return action_get_channelbag_for_slot(act, obj.animation_data.action_slot).fcurves


def rest_rel(bone):
    return bone.parent.matrix_local.inverted() @ bone.matrix_local if bone.parent else bone.matrix_local.copy()


def load_rom(arm, meshes):
    if not os.path.exists(ROM):
        say("no ROM take at", ROM)
        return None
    scene = bpy.context.scene
    src_objs = import_fbx(ROM, anim=True)
    src = next(o for o in src_objs if o.type == 'ARMATURE')
    act = src.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for m in meshes:
        for mod in m.modifiers:
            mod.show_viewport = False
    names = [b.name for b in arm.data.bones if b.name in src.data.bones]
    R_src = {n: rest_rel(src.data.bones[n]) for n in names}
    R_dst = {n: rest_rel(arm.data.bones[n]) for n in names}
    R_inv = {n: R_dst[n].inverted() for n in names}
    # translations are retargeted in each armature's own space, so compare pelvis heights there too
    scale = arm.data.bones["pelvis"].head_local.z / src.data.bones["pelvis"].head_local.z
    samples = {n: ([], []) for n in names}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        for n in names:
            anim_rel = R_src[n] @ src.pose.bones[n].matrix_basis
            loc = R_dst[n].to_translation()
            if n in ("root", "pelvis"):
                loc = loc + (anim_rel.to_translation() - R_src[n].to_translation()) * scale
            basis = R_inv[n] @ (Matrix.Translation(loc) @ anim_rel.to_quaternion().to_matrix().to_4x4())
            q = basis.to_quaternion()
            qs = samples[n][0]
            if qs and qs[-1].dot(q) < 0:
                q.negate()
            qs.append(q)
            samples[n][1].append(basis.to_translation())
    for n in names:
        pb = arm.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.keyframe_insert("rotation_quaternion", frame=f0)
        pb.keyframe_insert("location", frame=f0)
    curves = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(arm)}
    frames = list(range(f0, f1 + 1))
    for n in names:
        qs, ls = samples[n]
        for path, vals, size in (("rotation_quaternion", qs, 4), ("location", ls, 3)):
            for i in range(size):
                fc = curves[(f'pose.bones["{n}"].{path}', i)]
                fc.keyframe_points.clear()
                fc.keyframe_points.add(len(frames))
                co = np.empty(len(frames) * 2, dtype=np.float32)
                co[0::2] = frames
                co[1::2] = [v[i] for v in vals]
                fc.keyframe_points.foreach_set("co", co)
                fc.keyframe_points.foreach_set("interpolation", [1] * len(frames))   # LINEAR
                fc.update()
    action = arm.animation_data.action
    action.name = "ROM_Test"
    action.use_fake_user = True
    drop_objects(src_objs)
    for m in meshes:
        for mod in m.modifiers:
            mod.show_viewport = True
    scene.frame_start, scene.frame_end = f0, f1
    say("ROM take", f0, f1, "bones", len(names), "pelvis ratio", round(scale, 4))
    return action


# --- scene dressing ----------------------------------------------------------------------------------------
def dress_scene(arm):
    scene = bpy.context.scene
    scene.render.fps = 30
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    try:
        scene.view_settings.view_transform = 'AgX'
    except TypeError:
        scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.exposure = -0.4
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.055, 0.06, 0.07, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world
    lights = [("Key", (2.4, -3.0, 3.2), 900, 2.5), ("Fill", (-3.2, -2.2, 1.8), 350, 3.0), ("Rim", (0.6, 3.2, 3.0), 700, 2.0),
              ("Top", (0.0, 0.0, 4.5), 250, 3.0)]
    target = Vector((0, 0, 1.0))
    for name, loc, power, size in lights:
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = (target - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    # competition mat: blue with a red border square, as in a dojang
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Mat"
    mat_m, nt, bsdf = principled("M_Mat")
    bsdf.inputs["Base Color"].default_value = (0.008, 0.03, 0.12, 1.0)
    set_input(bsdf, ["Roughness"], 0.75)
    floor.data.materials.append(mat_m)
    bpy.ops.mesh.primitive_plane_add(size=9.0, location=(0, 0, -0.002))
    border = bpy.context.active_object
    border.name = "MatBorder"
    b_m, nt, bsdf = principled("M_MatBorder")
    bsdf.inputs["Base Color"].default_value = (0.35, 0.02, 0.03, 1.0)
    set_input(bsdf, ["Roughness"], 0.75)
    border.data.materials.append(b_m)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    cam.data.lens = 50
    cam.location = (1.6, -4.6, 1.25)
    cam.rotation_euler = (Vector((0, 0, 0.95)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
    # viewports open in Material Preview lit by the scene lights
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.shading.use_scene_lights = True
                        space.shading.use_scene_world = True
                        space.overlay.show_floor = False
    # skeleton: main bones visible as thin sticks, helpers hidden in their own collection
    arm.data.display_type = 'STICK'
    arm.show_in_front = False
    if hasattr(arm.data, "collections"):
        main = arm.data.collections.new("Animated")
        helpers = arm.data.collections.new("Helpers_Correctives")
        for b in arm.data.bones:
            (main if b.name in MAIN_BONES else helpers).assign(b)
        for c in list(arm.data.collections):
            if c not in (main, helpers):
                arm.data.collections.remove(c)
        helpers.is_visible = False
    return cam


def check_renders(cam, action):
    scene = bpy.context.scene
    os.makedirs(CHECK, exist_ok=True)
    shots = [("front", (0.0, -4.4, 1.05), (0, 0, 0.95), 50, None),
             ("three_quarter", (1.6, -4.6, 1.25), (0, 0, 0.95), 50, None),
             ("face", (0.25, -1.0, 1.62), (0, 0, 1.6), 85, None),
             ("helmet", (0.55, -0.80, 1.74), (0, 0, 1.62), 50, None),
             ("protector", (0.35, -1.55, 1.30), (0, 0, 1.22), 50, None),
             ("back", (-0.6, 3.6, 1.30), (0, 0, 1.15), 50, None),
             ("waist", (0.30, -1.15, 1.00), (0, 0, 0.93), 50, None),
             ("feet", (0.35, -0.95, 0.30), (0, -0.04, 0.05), 50, None),
             ("hands", (-0.75, -0.80, 1.00), (-0.38, -0.02, 0.88), 70, None)]
    if action:
        f0, f1 = int(action.frame_range[0]), int(action.frame_range[1])
        for k, t in enumerate((0.3, 0.55, 0.62, 0.8)):
            shots.append((f"rom_{k}", (1.2, -4.6, 1.2), (0, 0, 0.95), 45, f0 + int((f1 - f0) * t)))
    rest = cam.location.copy(), cam.rotation_euler.copy(), cam.data.lens
    for name, loc, look, lens, frame in shots:
        scene.frame_set(frame if frame else scene.frame_start)
        if frame is None and action:
            arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
            arm.animation_data.action = None
            for pb in arm.pose.bones:
                pb.matrix_basis = Matrix()
        cam.location = loc
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        scene.render.filepath = f"{CHECK}/test_model_{name}.png"
        bpy.ops.render.render(write_still=True)
        if frame is None and action:
            arm.animation_data.action = action
    cam.location, cam.rotation_euler, cam.data.lens = rest
    say("check renders", [s[0] for s in shots])


def export_fbx(path, objs, anim):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = next(o for o in objs if o.type == 'ARMATURE')
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE',
        use_mesh_modifiers=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
        use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=anim, bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, path_mode='COPY', embed_textures=True)
    say("exported", path, round(os.path.getsize(path) / 1e6, 1), "MB", "anim" if anim else "rest pose")


def apply_body_coverage(body):
    # body skin hidden under the gear (same maps Unreal uses)
    centres = face_uv_centres(body.data) % 1.0
    hidden = np.zeros(len(centres), dtype=bool)
    for p in HFM_PARTS:
        path = f"{FITTED}/T_HFM_{p}.png"
        if not os.path.exists(path):
            continue
        px, img = image_array(path)
        h, w = px.shape[:2]
        xs = np.clip((centres[:, 0] * w).astype(int), 0, w - 1)
        ys = np.clip((centres[:, 1] * h).astype(int), 0, h - 1)
        hidden |= px[ys, xs, 0] < 0.5
        bpy.data.images.remove(img)
    say("body: hiding", int(hidden.sum()), "of", len(hidden), "faces under the gear")
    delete_faces(body, hidden)



# --- build -------------------------------------------------------------------------------------------------
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT, exist_ok=True)
    scene = bpy.context.scene

    body_objs = import_fbx(f"{MH}/{ASSET}_Body.fbx")
    arm = next(o for o in body_objs if o.type == 'ARMATURE')
    arm.name = "TestFighter_Skeleton"
    body = next(o for o in body_objs if o.type == 'MESH')
    body.name = "Body"
    # the FBX root empty carries the centimetre-to-metre scale: keep it on the armature before dropping the empty
    mw = arm.matrix_world.copy()
    arm.parent = None
    arm.matrix_world = mw
    drop_objects([o for o in body_objs if o.type not in ('ARMATURE', 'MESH')])
    bones = set(arm.data.bones.keys())
    say("skeleton", len(bones), "bones")

    # head: keep skin, teeth, eyes, lashes; move from the face skeleton onto the body skeleton
    head_objs = import_fbx(f"{MH}/{ASSET}_Head.fbx")
    head = next(o for o in head_objs if o.type == 'MESH')
    head.name = "Head"
    mi = np.empty(len(head.data.polygons), dtype=np.int32)
    head.data.polygons.foreach_get("material_index", mi)
    removed = delete_faces(head, [int(i) not in HEAD_KEEP for i in mi])
    say("head: removed", removed, "faces (saliva, eye shell, eye edge, cartilage)")
    hg = {g.index: g.name for g in head.vertex_groups}
    if "head" not in head.vertex_groups:
        head.vertex_groups.new(name="head")
    head_vg = head.vertex_groups["head"]
    moved = 0
    for v in head.data.vertices:
        extra = sum(g.weight for g in v.groups if hg.get(g.group) not in bones)
        if extra > 0:
            head_vg.add([v.index], extra, 'ADD')
            moved += 1
    foreign = [g for g in head.vertex_groups if g.name not in bones]
    for g in foreign:
        head.vertex_groups.remove(g)
    say("head: facial weights folded into 'head' on", moved, "vertices;", len(foreign), "face-only groups removed")
    bind(head, arm)
    drop_objects([o for o in head_objs if o is not head])

    apply_body_coverage(body)

    gear = []
    for p in PARTS:
        objs = import_fbx(f"{FITTED}/SK_Fighter_{p}.fbx")
        for m in (o for o in objs if o.type == 'MESH'):
            bind(m, arm)
            m.name = p
            gear.append(m)
        drop_objects([o for o in objs if o.type != 'MESH'])
    say("gear:", [g.name for g in gear])

    # materials
    # MetaHuman stores these skin maps linear (sRGB off) and tints them per character; same here
    body_bc = prepared(f"{STOCK}/T_Skin_V1_Body_BC.png", "T_TF_Body_BaseColor", 4096, non_color=True)
    body_n = prepared(f"{STOCK}/T_Chr0005_Body_N.png", "T_TF_Body_Normal", 4096, non_color=True)
    head_bc = prepared(f"{STOCK}/T_Skin_V1_Chest_BC.png", "T_TF_Head_BaseColor", 4096, non_color=True)
    teeth = prepared(f"{STOCK}/T_Teeth_BaseColor.png", "T_TF_Teeth_BaseColor", 1024)
    sclera = prepared(f"{STOCK}/T_EyeSclera_D.png", "T_TF_Eye_Sclera", 1024)
    iris = prepared(f"{STOCK}/T_Iris001_01_D.png", "T_TF_Eye_Iris", 1024)
    gear_bc = prepared(f"{GEAR_TEX}/T_Fighter_BaseColor.png", "T_TF_Gear_BaseColor", 4096)
    gear_s = prepared(f"{GEAR_TEX}/T_Fighter_Surface.png", "T_TF_Gear_Surface", 2048, non_color=True)
    gear_w = prepared(f"{GEAR_TEX}/T_Fighter_Weave_N.png", "T_TF_Gear_Weave_N", 1024, non_color=True)
    target = np.array([srgb_to_linear(c) for c in SKIN_TARGET_SRGB])
    gb = target / np.maximum(mean_skin_linear(body_bc), 1e-3)
    gh = target / np.maximum(mean_skin_linear(head_bc), 1e-3)
    say("skin gains body", np.round(gb, 3), "head", np.round(gh, 3))
    m_body = skin_material("M_Skin_Body", body_bc, tuple(gb), body_n, 0.5)
    m_head = skin_material("M_Skin_Head", head_bc, tuple(gh), None, 0.45)
    m_teeth = textured_material("M_Teeth", teeth, 0.3)
    m_eye = eye_material(sclera, iris)
    m_lash = flat_material("M_Eyelashes", (0.03, 0.02, 0.015), 0.6)
    # the lash cards carry no opacity map; keep them faint so they read as lashes, not strips
    set_input(m_lash.node_tree.nodes["Principled BSDF"], ["Alpha"], 0.3)
    if hasattr(m_lash, "surface_render_method"):
        m_lash.surface_render_method = 'BLENDED'
    elif hasattr(m_lash, "blend_method"):
        m_lash.blend_method = 'BLEND'
    m_gear = gear_material(gear_bc, gear_s, gear_w)
    body.data.materials.clear()
    body.data.materials.append(m_body)
    slot_mats = {"Skin_Head": m_head, "Teeth": m_teeth, "Eye": m_eye, "Eyelashes": m_lash}
    old = [HEAD_KEEP.get(i) for i in range(len(head.data.materials))]
    order = ["Skin_Head", "Teeth", "Eye", "Eyelashes"]
    remap = np.array([order.index(o) if o in order else 0 for o in old], dtype=np.int32)
    mi = np.empty(len(head.data.polygons), dtype=np.int32)
    head.data.polygons.foreach_get("material_index", mi)
    head.data.materials.clear()
    for o in order:
        head.data.materials.append(slot_mats[o])
    head.data.polygons.foreach_set("material_index", remap[mi])
    head.data.update()
    for g in gear:
        g.data.materials.clear()
        g.data.materials.append(m_gear)

    meshes = [body, head] + gear
    for m in meshes:
        for p in m.data.polygons:
            p.use_smooth = True

    # rest-pose FBX for MotionBuilder / other DCCs (before any animation exists). The armature object is the
    # skeleton's root joint in FBX (Blender folds the FBX "root" joint into it on import), so it must be named "root".
    cam = dress_scene(arm)
    arm.name = "root"
    export_fbx(f"{OUT}/{NAME}.fbx", [arm] + meshes, anim=False)

    action = load_rom(arm, meshes)
    if action:
        export_fbx(PREVIEW_FBX, [arm] + meshes, anim=True)
    check_renders(cam, action)
    scene.frame_set(scene.frame_start)
    for img in bpy.data.images:
        if img.filepath and img.filepath.replace("\\", "/").startswith(TEX_OUT):
            img.filepath = bpy.path.relpath(img.filepath, start=OUT)
    arm.hide_set(True)                       # skeleton hidden in the viewport by default (unhide in the outliner)
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/{NAME}.blend", relative_remap=True, compress=True)
    say("saved", f"{OUT}/{NAME}.blend")
    say("DONE")

if __name__ == "__main__":
    try:
        build()
    except Exception:
        say("ERROR", traceback.format_exc())
        raise
