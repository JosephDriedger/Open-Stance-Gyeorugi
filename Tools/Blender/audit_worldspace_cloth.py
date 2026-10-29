"""Inspect physical settings and contact normals without modifying assets."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_SingleSurface/Candidate.blend'))
s=bpy.context.scene;s.frame_set(1);bpy.context.view_layer.update()
p=bpy.data.objects['SIM_Shared_Belt_Tails'];cloth=next(m for m in p.modifiers if m.type=='CLOTH')
def scalar_props(data):
    return {prop.identifier:getattr(data,prop.identifier) for prop in data.bl_rna.properties
            if prop.type in ['BOOLEAN','INT','FLOAT','STRING','ENUM'] and not getattr(prop,'is_array',False)}
report={'settings':scalar_props(cloth.settings),'collision':scalar_props(cloth.collision_settings),'contacts':[]}
report['other_cloth']={}
for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
    obj=bpy.data.objects[name];modifier=next(m for m in obj.modifiers if m.type=='CLOTH')
    report['other_cloth'][name]={'vertices':len(obj.data.vertices),'local_scale':list(obj.scale),'world_scale':list(obj.matrix_world.to_scale()),'settings':scalar_props(modifier.settings)}
deps=bpy.context.evaluated_depsgraph_get()
for o in cloth.collision_settings.collection.objects:
    ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
    # Front-facing surface should point toward -Y in this character convention.
    samples=[poly for poly in me.polygons if (o.matrix_world@poly.center).y<-.1 and .7<(o.matrix_world@poly.center).z<1.1]
    normal=o.matrix_world.to_3x3().inverted().transposed()
    report['contacts'].append({'name':o.name,'vertices':len(me.vertices),'front_sample_count':len(samples),
        'front_area_weighted_normal_y':sum((normal@poly.normal).y*poly.area for poly in samples)/max(1e-9,sum(poly.area for poly in samples)),
        'collision':scalar_props(o.collision)})
    ev.to_mesh_clear()
(root/'worldspace_cloth_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
