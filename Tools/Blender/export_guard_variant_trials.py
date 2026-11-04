import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import finish_character_suite as finish
ROOT=Path(__file__).resolve().parents[2]
smooth='--smooth' in sys.argv
OUT=ROOT/'Resources/Models/FinalRefinement'/('FootguardSmoothExportReview' if smooth else 'FootguardExportReview');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement'/('FootguardLocalROMSmooth' if smooth else 'FootguardVariantReview')/'Candidate.blend'))
r=bpy.data.objects['RIG_Body_Stocky'];r.animation_data.action=None;r.data.pose_position='REST'
source=bpy.data.materials['Footguard_Continuous_Instep'];image=next(n.image for n in source.node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
portable=bpy.data.materials.new('Footguard_Portable_BaseColor');portable.use_nodes=True;nodes=portable.node_tree.nodes;links=portable.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.62
tex=nodes.new('ShaderNodeTexImage');tex.image=image;uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UVInstepPanel';links.new(uv.outputs['UV'],tex.inputs['Vector']);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
rows=[]
for style,name in enumerate(('FootGuards','FootGuards_PaddedInstep')):
 r['FootGuardsStyle']=style;r.update_tag();bpy.context.view_layer.update();o=bpy.data.objects[name];assert not o.hide_render
 o.data.materials.clear();o.data.materials.append(portable);o['ExportUV']='UVInstepPanel'
 path=OUT/('Stocky_'+('Standard' if style==0 else 'Padded')+'_Guard.fbx');finish.export(r,[o],path,False)
 rows.append({'style':style,'object':name,'fbx':str(path),'scope':'Guard mesh plus existing full rig; static export, not a replacement mocap target'})
(OUT/'exports.json').write_text(json.dumps({'production_installed':False,'exports':rows,'material_limit':'Base color image and roughness only; fine procedural bump omitted in this portability trial'},indent=2))
