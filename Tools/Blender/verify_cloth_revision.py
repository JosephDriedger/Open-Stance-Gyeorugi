import bpy,json,hashlib
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p/'Front_Kick_Cloth_Baked.fbx'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');assert len(r.data.bones)==341
report={'body_bones':341,'cloth_objects':{},'textures':{},'fbx_sha256':hashlib.sha256((p/'Front_Kick_Cloth_Baked.fbx').read_bytes()).hexdigest()}
for name in ['Uniform_Wrap_Skirt','Belt_Tail_Left','Belt_Tail_Right']:
 o=next(o for o in bpy.context.scene.objects if o.name.startswith(name));keys=o.data.shape_keys;assert len(keys.key_blocks)==73
 bpy.context.scene.frame_set(26);bpy.context.view_layer.update();assert abs(sum(k.value for k in keys.key_blocks if k.name.startswith('ClothBake_'))-1)<.01
 report['cloth_objects'][name]={'shapes':72,'animation_reimport_passed':True}
for name in ['Cotton_BaseColor','Belt_BaseColor','Cotton_Normal','Cotton_Roughness']:
 imgs=[im for im in bpy.data.images if name in im.name];assert imgs and all(im.size[0]==512 for im in imgs),name
 report['textures'][name]={'loaded':True,'resolution':512}
(p/'validation.json').write_text(json.dumps(report,indent=2))
