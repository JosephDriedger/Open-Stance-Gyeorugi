"""Select fabric UVs without changing native geometry; clean export-only body faces."""
import bmesh

def fabric_uv(obj):
    if obj.type!='MESH' or not obj.data.uv_layers.get('UVWeave'):
        return False
    if not any(m and 'Dobok_White_Cotton' in m.name for m in obj.data.materials):
        return False
    layer=obj.data.uv_layers['UVWeave']
    if len({tuple(d.uv) for d in layer.data})<3:
        return False
    changed=obj.get('ExportUV')!='UVWeave' or obj.data.uv_layers.active!=layer or not layer.active_render
    obj['ExportUV']='UVWeave'
    obj.data.uv_layers.active_index=list(obj.data.uv_layers).index(layer)
    layer.active_render=True
    return changed

def clean_export_body(obj):
    if obj.name.split('.')[0]!='Body' or obj.data.shape_keys:
        return 0
    bm=bmesh.new();bm.from_mesh(obj.data)
    dead=[face for face in bm.faces if face.calc_area()<1e-14]
    if dead:
        bmesh.ops.delete(bm,geom=dead,context='FACES_ONLY');bm.to_mesh(obj.data);obj.data.update()
    count=len(dead);bm.free();return count
