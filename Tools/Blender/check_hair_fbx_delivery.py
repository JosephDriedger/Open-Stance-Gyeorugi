import bpy,json,traceback
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairClothRevision')
try:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(out/'Medium/WhiteWrap/Gameplay_High_Dobok.fbx'))
 assert not any(o.get('SimulationOnly') or o.name.startswith('SIM_') for o in bpy.data.objects)
 scalp=next(o for o in bpy.data.objects if 'Hair_Crew_Cut__Scalp_Coverage' in o.name)
 bs=next(n for n in scalp.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 assert bs.inputs['Alpha'].is_linked
 tex=bs.inputs['Alpha'].links[0].from_node
 assert tex.type=='TEX_IMAGE' and tex.image and tex.image.size[0]>0
 (out/'fbx_hair_validation.json').write_text(json.dumps({'passed':True,'object':scalp.name,'image':tex.image.name,'size':list(tex.image.size),'simulation_proxies_exported':False},indent=2))
except:
 (out/'fbx_hair_error.log').write_text(traceback.format_exc());raise
