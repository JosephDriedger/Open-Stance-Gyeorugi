import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from repair_uniform_export_data import fabric_uv,clean_export_body
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('BodyTest')
mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,0,1),(2,0,1)],[],[(0,1,2),(3,4,5)])
obj=bpy.data.objects.new('Body',mesh);bpy.context.scene.collection.objects.link(obj)
obj.vertex_groups.new(name='pelvis').add(list(range(6)),1,'REPLACE')
before=[tuple(v.co) for v in mesh.vertices]
assert clean_export_body(obj)==1
assert [tuple(v.co) for v in mesh.vertices]==before and len(mesh.polygons)==1
assert all(len(v.groups)==1 and v.groups[0].weight==1 for v in mesh.vertices)
obj.shape_key_add(name='Basis');obj.shape_key_add(name='BodyVariation')
assert clean_export_body(obj)==0 and len(mesh.shape_keys.key_blocks)==2
garment=bpy.data.objects.new('Jacket',mesh.copy());bpy.context.scene.collection.objects.link(garment)
mat=bpy.data.materials.new('Dobok_White_Cotton');garment.data.materials.append(mat)
garment.data.uv_layers.new(name='UVMap');weave=garment.data.uv_layers.new(name='UVWeave')
for data,uv in zip(weave.data,[(0,0),(1,0),(0,1)]):data.uv=uv
garment.data.uv_layers.active_index=0
assert fabric_uv(garment) and garment['ExportUV']=='UVWeave' and weave.active_render
assert garment.data.uv_layers.active.name=='UVWeave'
assert not fabric_uv(garment)
out=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement/UniformGeometryDelivery/exporter_regression.json'
out.write_text(json.dumps({'passed':True,'checks':['zero-area faces removed from export copy','vertices and weights preserved','shape-key body excluded','fabric UV selected and idempotent']},indent=2))
print('UNIFORM_EXPORTER_REGRESSION_PASSED',flush=True)
