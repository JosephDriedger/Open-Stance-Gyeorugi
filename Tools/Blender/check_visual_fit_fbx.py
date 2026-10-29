import bpy,json,traceback
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/VisualFitRepair')
try:
 rows=[]
 for kind,file in [('Medium','Gameplay_High_Dobok.fbx'),('Compact','Crowd_Far.fbx')]:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(out/kind/'WhiteWrap'/file))
  assert not any(o.get('SimulationOnly') or o.name.startswith('SIM_') for o in bpy.data.objects)
  scalp=next(o for o in bpy.data.objects if 'Hair_Crew_Cut__Scalp_Coverage' in o.name)
  bs=next(n for n in scalp.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert bs.inputs['Alpha'].is_linked
  tex=bs.inputs['Alpha'].links[0].from_node;assert tex.type=='TEX_IMAGE' and tex.image and tex.image.size[0]>0
  rows.append({'file':str(Path(kind)/'WhiteWrap'/file),'alpha_image':tex.image.name,'scalp_vertices':len(scalp.data.vertices),'simulation_proxies_exported':False})
 (out/'fbx_hair_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
except:(out/'fbx_hair_error.log').write_text(traceback.format_exc());raise
