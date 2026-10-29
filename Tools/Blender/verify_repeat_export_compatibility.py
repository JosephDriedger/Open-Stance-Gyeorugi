import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
rows=[]
for kind in build.PRESETS:
 p=build.ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High_Dobok.fbx'
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p))
 rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
 images=[]
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and o.name.startswith('Hair_'):
   for m in o.data.materials:
    if m and m.use_nodes:
     for n in m.node_tree.nodes:
      if n.type=='TEX_IMAGE':
       assert n.extension=='REPEAT';images.append(n.image.name if n.image else None)
 assert images,(kind,'No hair textures found')
 rows.append({'preset':kind,'file':str(p.relative_to(build.ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bone_count':341,'hair_images_use_repeat':True})
 print('EXPORT_REPEAT_VERIFIED '+kind,flush=True)
out=build.ROOT/'Resources/Models/FinalRefinement/HairRepeat/export_compatibility.json';out.write_text(json.dumps({'passed':True,'files':rows},indent=2))
