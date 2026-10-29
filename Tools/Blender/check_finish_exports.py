import bpy,sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import refine_character_finish as fix
out=fix.OUT/'ExportDiagnostics';out.mkdir(exist_ok=True)
try:
 source=fix.OUT/'Medium/Gameplay_High.blend'
 while not (source.parent/'Gameplay_High_validation.json').exists():time.sleep(5)
 reports=[]
 for style in [1,4]:
  bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['RIG_Body_Medium'];r['HairStyle']=style;r['Wear_Helmet']=False;build.refresh(r)
  path=out/f'HairStyle{style}.fbx';build.export(r,path)
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path))
  o=next(o for o in bpy.context.scene.objects if 'Scalp_Coverage' in o.name and o.type=='MESH')
  bs=next(n for n in o.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  assert bs.inputs['Alpha'].is_linked
  uv=list(o.data.uv_layers[0].data);assert len(uv)>0
  core=any('Ponytail_Core' in o.name for o in bpy.context.scene.objects)
  assert core==(style==4)
  mats={m.name:next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value for m in bpy.data.materials if m.use_nodes and any(n.type=='BSDF_PRINCIPLED' for n in m.node_tree.nodes)}
  reports.append({'hairstyle':style,'alpha_linked':True,'ponytail_core':core,'roughness':mats})
 (out/'validation.json').write_text(json.dumps({'passed':True,'files':reports},indent=2))
except:(out/'error.log').write_text(traceback.format_exc());raise
