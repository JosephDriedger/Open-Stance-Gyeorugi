"""Export a menu portrait fighter (prepare_portrait_fighter.py, then build_traditional_dobok.py --upto=5) for Unreal.

    blender.exe -b <Portrait/<Kind>_<Sex>/Candidate.blend> -P export_portrait_fighter.py -- <out.fbx> [SkinTone=N ...]

Body, head, hair, eyebrows and the dobok with its belt; no sparring gear and no animation. The belt tails' Solidify is
baked into the mesh first (single-sided strips are back-face culled in Unreal, see add_belt_chain_layer.py). The
armature is exported as `root` for import onto the production fighter skeleton, which the placeholder clips use. With
look arguments (a premade fighter from portrait_roster.json) the rig selectors are set first and the chosen skin tone
and hair colour are baked into what the export carries.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import rebuild_updated_characters as build

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
out.parent.mkdir(parents=True, exist_ok=True)
# Optional look for one premade fighter (portrait_roster.json): SkinTone=, HairStyle=, HairColor=, EyeColor=, EyebrowStyle=, HeadStyle=
LOOK = {a.split('=')[0]: int(a.split('=')[1]) for a in args[1:] if '=' in a}
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
for key in ('Wear_Helmet', 'Wear_Protector', 'Wear_Gloves', 'Wear_FootGuards'):
    rig[key] = False
rig['BlenderCloth'] = False
for key, value in LOOK.items():
    rig[key] = value
build.refresh(rig)
bpy.context.view_layer.update()


def srgb_to_linear(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


# Hair and eyebrow colour is a driven multiply node in front of the shader, which the export's simple materials do not
# carry (they take the shader's own colour): bake the chosen colour into the shader.
for mat in bpy.data.materials:
    name = mat.name.lower()
    if not mat.use_nodes or not ('hair' in name or 'brow' in name):
        continue
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None or not bsdf.inputs['Base Color'].is_linked:
        continue
    tint = bsdf.inputs['Base Color'].links[0].from_node
    if tint.type not in ('MIX_RGB', 'MIX') or tint.inputs[1].is_linked:
        continue
    base, factor = tint.inputs[1].default_value, tint.inputs[2].default_value
    links.remove(bsdf.inputs['Base Color'].links[0])
    bsdf.inputs['Base Color'].default_value = (base[0] * factor[0], base[1] * factor[1], base[2] * factor[2], 1.0)

# Skin tone: the export uses the suite's baked skin textures (tone 5). Write tinted copies with the rig's own chart
# multipliers (build_character_suite.palette: chart colour over the tone-5 reference, per linear channel) and point the
# export at them.
SKIN_CHART = ['F6EDE4', 'F3E7DB', 'F7EAD0', 'EADABA', 'D7BD96', 'A07E56', '825C43', '604134', '3A312A', '292420']
# Natural iris colours (build_character_suite.palette): dark brown, brown, amber, hazel, green, blue, grey
EYE_CHART = ['25180F', '573620', '9B6B25', '787038', '426344', '426B85', '7B8588']
tone = LOOK.get('SkinTone', 5)
eyes = LOOK.get('EyeColor')  # any roster fighter: the eye texture is rebuilt (the baked one has near-black irises)
if tone != 5 or eyes is not None:
    import shutil
    import numpy as np

    def linear_rgb(hex_colour):
        return np.array([srgb_to_linear(int(hex_colour[i:i + 2], 16) / 255) for i in (0, 2, 4)])

    def to_linear(rgb):
        return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)

    def to_srgb(linear):
        linear = np.clip(linear, 0, 1)
        return np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)

    def eye_texture(target):
        # M_Eye: the sclera image, with the iris image (scaled 4.7619 about the centre, clipped) times the eye colour
        # inside a circle of radius 0.1008-0.1092 UV round the centre; mixed in linear light, as the shader does.
        sclera_image, iris_image = bpy.data.images['T_TF_Eye_Sclera'], bpy.data.images['T_TF_Eye_Iris']
        w, h = sclera_image.size
        sclera = to_linear(np.array(sclera_image.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3])
        iw, ih = iris_image.size
        iris = to_linear(np.array(iris_image.pixels[:], dtype=np.float32).reshape(ih, iw, 4)[:, :, :3])
        v, u = np.mgrid[0:h, 0:w]
        u, v = (u + .5) / w - .5, (v + .5) / h - .5
        r = np.hypot(u, v)
        fac = np.clip((r - .1092) / (.1008 - .1092), 0, 1)[:, :, None]
        iu, iv = u * 4.7619 + .5, v * 4.7619 + .5
        inside = (iu >= 0) & (iu < 1) & (iv >= 0) & (iv < 1)
        sample = iris[np.clip((iv * ih).astype(int), 0, ih - 1), np.clip((iu * iw).astype(int), 0, iw - 1)]
        sample = np.where(inside[:, :, None], sample, 0)
        # The suite's iris image is nearly black, so the shader's multiply leaves every chart colour reading as black
        # at portrait size. Use it as detail instead: scaled so the iris ring's typical brightness (70th percentile,
        # pupil excluded) comes out at the chart colour, keeping the pupil and the fibre pattern.
        luminance = sample @ np.array([.2126, .7152, .0722])
        ring = (r > .045) & (r < .1)
        reference = max(float(np.percentile(luminance[ring], 70)), 1e-4)
        sample = np.clip(luminance / reference, 0, 1.6)[:, :, None] * linear_rgb(EYE_CHART[eyes])
        out_rgb = to_srgb(sclera * (1 - fac) + sample * fac)
        image = bpy.data.images.new('EyeExport', w, h, alpha=True)
        image.pixels = np.concatenate([out_rgb, np.ones((h, w, 1), dtype=np.float32)], axis=2).ravel()
        image.filepath_raw = str(target)
        image.file_format = 'PNG'
        image.save()
        bpy.data.images.remove(image)

    gain = linear_rgb(SKIN_CHART[tone]) / linear_rgb(SKIN_CHART[5])
    textures = out.parent / 'ExportTextures'
    (textures / 'Textures').mkdir(parents=True, exist_ok=True)
    for png in (build.OUT / 'Textures').glob('*.png'):
        target = textures / 'Textures' / png.name
        if png.stem == 'M_Eye' and eyes is not None:
            eye_texture(target)
        elif png.stem.startswith('M_Skin') and tone != 5:
            image = bpy.data.images.load(str(png))
            pixels = np.array(image.pixels[:], dtype=np.float32).reshape(-1, 4)
            rgb = pixels[:, :3]
            linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4) * gain
            linear = np.clip(linear, 0, 1)
            pixels[:, :3] = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
            image.pixels = pixels.ravel()
            image.filepath_raw = str(target)
            image.file_format = 'PNG'
            image.save()
            bpy.data.images.remove(image)
        else:
            shutil.copyfile(png, target)
    build.OUT = textures
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    tail = bpy.data.objects.get(name)
    solidify = next((m for m in tail.modifiers if m.type == 'SOLIDIFY'), None) if tail else None
    if solidify is not None:
        with bpy.context.temp_override(object=tail, active_object=tail):
            bpy.ops.object.modifier_apply(modifier=solidify.name)
# The jacket is one garment: its lower part (built as Jacket_Skirt so the game can simulate it as cloth) joins the
# jacket body here, where nothing simulates it.
jacket, skirt = bpy.data.objects.get('Jacket'), bpy.data.objects.get('Jacket_Skirt')
if jacket and skirt:
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (jacket, skirt))
    bpy.context.view_layer.objects.active = jacket
    with bpy.context.temp_override(active_object=jacket, selected_editable_objects=[jacket, skirt]):
        bpy.ops.object.join()
# The belt tails hang from the knot: skinned partly to the thighs they swung out sideways in the stance. With no chain
# physics here, they follow the pelvis alone.
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    tail = bpy.data.objects.get(name)
    if tail is None:
        continue
    tail.vertex_groups.clear()
    group = tail.vertex_groups.new(name='pelvis')
    group.add([v.index for v in tail.data.vertices], 1.0, 'REPLACE')
rig.data.pose_position = pose_position
rig.name = 'root'
build.export(rig, out, False)
print('PORTRAIT EXPORTED', out, [o.name for o in build.meshes() if not o.hide_render], flush=True)
