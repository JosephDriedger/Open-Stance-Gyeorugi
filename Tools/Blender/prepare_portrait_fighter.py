"""Start file for a menu portrait fighter: one body type as a man or a woman, in the traditional dobok, no sparring gear.

    blender.exe -b <TraditionalDobok/<Kind>/Work.blend> -P prepare_portrait_fighter.py -- <Male|Female> <out Work.blend>

The body types (Compact, LeanTall, Stocky, Tall) share one base body and face. The suite's Male_* and Female_* presets
are Medium with a width warp (shoulders, waist, hips, jaw, and for men a firmer brow and nose bridge) and their own hair
and eyebrows (build_character_variations.py); this applies the same warp, scaled to the body type's height, and picks
the hair and eyebrows through the rig's selectors. Every skinned mesh is warped together, so the dobok layers built on
top afterwards (build_traditional_dobok.py --upto=5: trousers, jacket, skirt, collar, belt) fit the warped body. The
protector, headgear, gloves and foot guards are switched off: the menu shows the fighter in uniform.
"""
import json
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index('--') + 1:]
SEX, OUT = args[0], args[1]
assert SEX in ('Male', 'Female'), SEX

# (shoulders, waist, hips, jaw) from build_character_variations.PRESETS: Male_Athletic and Female_Athletic
WARP = {'Male': (.15, .02, -.02, .19), 'Female': (.015, -.06, .075, -.045)}[SEX]
# hair and eyebrows: indices into build_character_variations.STYLES / EYEBROW_STYLES
LOOK = {'Male': dict(HairStyle=0, EyebrowStyle=2), 'Female': dict(HairStyle=4, EyebrowStyle=3)}[SEX]
MEDIUM_HIP_Z = .915  # the warp's heights are written for the Medium body (hip height 0.915 m)

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
for key, value in {'Wear_Helmet': False, 'Wear_Protector': False, 'Wear_Gloves': False, 'Wear_FootGuards': False,
                   'Wear_Jacket': True, 'Wear_Pants': True, 'Wear_Belt': True, 'Wear_Hair': True, 'Wear_Eyebrows': True,
                   **LOOK}.items():
    rig[key] = value
rig['PortraitSex'] = SEX
rig.update_tag()

k = (rig.matrix_world @ rig.data.bones['pelvis'].head_local).z / MEDIUM_HIP_Z
shoulders, waist, hips, jaw = WARP


def warp(collection, mw, inv):
    co = np.empty(len(collection) * 3, dtype=np.float32)
    collection.foreach_get('co', co)
    co = co.reshape(-1, 3)
    w = co @ mw[:3, :3].T + mw[:3, 3]
    x, y, z = w.T.copy()
    zn = z / k  # heights as on the Medium body
    chest = np.exp(-((zn - 1.31) / .135) ** 2)
    mid = np.exp(-((zn - 1.10) / .11) ** 2)
    hip = np.exp(-((zn - .88) / .14) ** 2)
    torso = np.exp(-(np.abs(x / k) / .31) ** 6)
    width = 1 + torso * (shoulders * chest + waist * mid + hips * hip)
    face = np.exp(-((zn - 1.575) / .042) ** 2) * np.clip((-y / k - .015) / .07, 0, 1)
    w[:, 0] = x * width * (1 + jaw * face)
    w[:, 1] = y * (1 + torso * (.35 * shoulders * chest + .40 * waist * mid + .30 * hips * hip))
    if SEX == 'Male':
        w[:, 1] -= k * .005 * np.exp(-((zn - 1.674) / .016) ** 2) * np.exp(-(x / k / .065) ** 4) * np.clip((-y / k - .06) / .04, 0, 1)
        w[:, 1] -= k * .007 * np.exp(-((zn - 1.550) / .025) ** 2) * np.exp(-(x / k / .040) ** 4) * np.clip((-y / k - .06) / .04, 0, 1)
    local = w @ inv[:3, :3].T + inv[:3, 3]
    collection.foreach_set('co', local.astype(np.float32).ravel())


warped = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH' or not any(m.type == 'ARMATURE' for m in o.modifiers):
        continue
    mw = np.array(o.matrix_world)
    inv = np.linalg.inv(mw)
    if o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks:
            warp(key.data, mw, inv)
        for vertex, point in zip(o.data.vertices, o.data.shape_keys.key_blocks[0].data):
            vertex.co = point.co
    else:
        warp(o.data.vertices, mw, inv)
    o.data.update()
    warped.append(o.name)

bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('PORTRAIT START DONE', json.dumps({'sex': SEX, 'height_scale': round(k, 3), 'warped': len(warped), **LOOK}), flush=True)
