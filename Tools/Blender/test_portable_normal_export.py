"""Verify tangent normal textures survive material simplification and FBX roundtrip."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
out=build.ROOT/'Resources/Models/FinalRefinement/NormalExportCheck';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add();o=bpy.context.object
mat=bpy.data.materials.new('NormalExportRegression');mat.use_nodes=True;o.data.materials.append(mat)
image=bpy.data.images.new('Regression_TangentNormal',width=4,height=4)
image.colorspace_settings.name='Non-Color';image.pixels[:]=[.6,.5,.99,1]*16
image.filepath_raw=str(out/'normal.png');image.file_format='PNG';image.save();image.pack()
nodes=mat.node_tree.nodes;links=mat.node_tree.links
tex=nodes.new('ShaderNodeTexImage');tex.image=image
normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45
links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
originals=build.portable_materials()
export_mat=o.data.materials[0];bs=next(n for n in export_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert bs.inputs['Normal'].is_linked
normal=bs.inputs['Normal'].links[0].from_node
assert normal.type=='NORMAL_MAP' and abs(normal.inputs['Strength'].default_value-.45)<1e-5
assert normal.inputs['Color'].links[0].from_node.image==image
path=out/'Normal_Roundtrip.fbx'
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False)
build.restore_materials(originals);assert o.data.materials[0]==mat
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bs=next(n for n in o.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert bs.inputs['Normal'].is_linked, 'FBX lost normal input'
normal=bs.inputs['Normal'].links[0].from_node
assert normal.type=='NORMAL_MAP' and normal.inputs['Color'].is_linked
texture=normal.inputs['Color'].links[0].from_node
assert texture.type=='TEX_IMAGE' and texture.image and texture.image.size[0]==4
(out/'validation.json').write_text(json.dumps({'normal_map_roundtrip':True,'source_material_restored':True,'texture_width':texture.image.size[0]},indent=2))
print('NORMAL_EXPORT_ROUNDTRIP_PASSED',flush=True)
