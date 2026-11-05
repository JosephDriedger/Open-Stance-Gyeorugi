"""Export a sparring fighter (any body type) with the kick animation for the Unreal cloth test.

Works on the old fitted uniform and on the layered traditional dobok (build_traditional_dobok.py). The jacket skirt
(`Jacket_Skirt`, or the old three panels) gets its own material ('Dobok_Skirt_Cloth') so it imports as its own mesh
section, which Tools/Unreal/skirt_cloth_test.py turns into Chaos cloth; the belt tails likewise get 'Belt_Tail_Cloth'. Shape keys that something in Blender drives (the
chest protector's hip-driven hem fold) are baked to keyframes over the scene's frames and exported with the mesh, so the
FBX carries them as morph targets with animation curves; other skirt and trouser keys are muted, since nothing drives
them in the engine. The armature is exported as `root` (production skeleton).

    blender.exe -b <Candidate.blend> -P export_skirt_cloth_test.py -- <out.fbx>
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import rebuild_updated_characters as build

out = Path(sys.argv[sys.argv.index('--') + 1])
out.parent.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
SKIRTS = [n for n in ('Jacket_Skirt', 'Jacket_Back', 'Jacket_Front_Left', 'Jacket_Front_Right') if bpy.data.objects.get(n)]
BAKED_KEYS = ('HipRetract_Protector_',)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
for key in ('Wear_Helmet', 'Wear_Protector', 'Wear_Gloves', 'Wear_FootGuards', 'Wear_Jacket', 'Wear_Pants'):
    rig[key] = True
rig['FootGuardsStyle'] = 0
rig['BlenderCloth'] = False
for name in ('FootGuards', 'FootGuards_PaddedInstep'):
    bpy.data.objects[name]['ExportUV'] = 'UVInstepPanel'
for name in SKIRTS + ['Pants']:
    obj = bpy.data.objects[name]
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.mute = True
skirt = None
for name in SKIRTS:
    obj = bpy.data.objects[name]
    if skirt is None:
        skirt = obj.data.materials[0].copy()
        skirt.name = 'Dobok_Skirt_Cloth'
    for i in range(len(obj.data.materials)):
        obj.data.materials[i] = skirt
# The belt tails get their own material too, so they import as their own section: the test hangs them as cloth from
# the knot, so a rising knee and thigh push them through the body physics capsules.
tail_material = None
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    obj = bpy.data.objects.get(name)
    if obj is None:
        continue
    if tail_material is None:
        tail_material = obj.data.materials[0].copy()
        tail_material.name = 'Belt_Tail_Cloth'
    for i in range(len(obj.data.materials)):
        obj.data.materials[i] = tail_material
build.refresh(rig)

# Bake driven keys to keyframes (drivers do not export), then keep those meshes' shape keys through the export copy.
baked = [o for o in scene.objects if o.type == 'MESH' and o.data.shape_keys and not o.hide_render
         and any(k.name.startswith(BAKED_KEYS) for k in o.data.shape_keys.key_blocks)]
values = {o.name: [] for o in baked}
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    for o in baked:
        values[o.name].append({k.name: k.value for k in o.data.shape_keys.key_blocks if k.name.startswith(BAKED_KEYS)})
for o in baked:
    shape_keys = o.data.shape_keys
    for fc in list(shape_keys.animation_data.drivers):
        if fc.data_path.split('"')[1].startswith(BAKED_KEYS):
            shape_keys.driver_remove(fc.data_path)
    for i, frame_values in enumerate(values[o.name]):
        for name, value in frame_values.items():
            block = shape_keys.key_blocks[name]
            block.value = value
            block.keyframe_insert('value', frame=scene.frame_start + i)
    o['PreserveExportShapeKeys'] = True
scene.frame_set(1)
# Collision capsule radii for the engine test, measured on this body's trousers (fixed Stocky sizes poked a slim body's
# hip capsule out through its skirt cloth and shredded it): per segment, the 30th-percentile distance of the trouser
# points along its middle to the bone line, less 5 mm, so each capsule sits just inside the trousers.
import json
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
pants = bpy.data.objects['Pants']
trouser_points = [pants.matrix_world @ v.co for v in pants.data.vertices]
capsules = {}
for bone, aim in (('pelvis', 'spine_01'), ('thigh_l', 'calf_l'), ('thigh_r', 'calf_r'), ('calf_l', 'foot_l'), ('calf_r', 'foot_r')):
    a = rig.matrix_world @ rig.data.bones[bone].head_local
    b = rig.matrix_world @ rig.data.bones[aim].head_local
    if bone == 'pelvis':  # the hips: the trouser seat below the pelvis, round the vertical axis
        b = a - (b - a).normalized() * .12
    d = b - a
    lo, hi = (.0, 1.0) if bone == 'pelvis' else (.2, .8)
    dists = []
    for p in trouser_points:
        t = (p - a).dot(d) / d.length_squared
        if lo <= t <= hi and (bone == 'pelvis' or (p.x > 0) == (bone.endswith('_l'))):
            dists.append((p - (a + d * t)).length)
    dists.sort()
    capsules[bone] = {'aim': aim, 'radius_cm': round((dists[int(len(dists) * .3)] - .005) * 100, 1) if dists else None}
rig.data.pose_position = pose_position
out.with_name(out.stem + '_capsules.json').write_text(json.dumps(capsules, indent=1))
rig.name = 'root'
if '--raw-bind' in sys.argv:  # debug: skip the bind-pose metadata rebuild after the FBX export
    import finalize_fbx_bind_normals
    finalize_fbx_bind_normals.finalize = lambda path: None
build.export(rig, out, True)
print('EXPORTED', out, 'baked shape keys on', len(baked), 'objects;', [o.name for o in build.meshes() if not o.hide_render], flush=True)
