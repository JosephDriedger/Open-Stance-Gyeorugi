import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
repair.OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairClothRevision')
p=Path(__file__).with_name('validate_tailored_delivery.py');code=p.read_text()
needle="   assert len(r.data.bones)==(25 if crowd else 341)"
extra='''
   assert 'BlenderCloth' in r and not r['BlenderCloth']
   cloth_parts=[]
   for obj in s.objects:
    for mod in obj.modifiers:
     if mod.type=='CLOTH':
      assert mod.settings.vertex_group_mass=='LiveCloth_Pin'
      assert mod.collision_settings.collection and not mod.show_render
      cloth_parts.append(obj.name)
   assert len(cloth_parts)==8,(kind,level,cloth_parts)
   scalp=next(obj for obj in s.objects if 'Hair_Crew_Cut__Scalp_Coverage' in obj.name)
   assert scalp.data.uv_layers.get('HairCoverageUV') and scalp.data.shape_keys.key_blocks.get('HelmetFit')
   bs=next(n for n in scalp.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
   assert bs.inputs['Alpha'].is_linked and bs.inputs['Alpha'].links[0].from_node.image.packed_file
   r['BlenderCloth']=True;r.update_tag();bpy.context.view_layer.update()
   assert all(m.show_render for obj in s.objects for m in obj.modifiers if m.type=='CLOTH')
   r['BlenderCloth']=False;r.update_tag();bpy.context.view_layer.update()
'''
assert needle in code;code=code.replace(needle,needle+extra)
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
