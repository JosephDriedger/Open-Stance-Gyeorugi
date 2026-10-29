"""Configure total garment masses; Blender's cloth mass is per vertex."""
import bpy

DEFAULT_TOTAL_KG={'Pants':.55,'Jacket':.30,'Jacket_WhiteVNeck':.30,
                  'Jacket_Front_Left':.08,'Jacket_Front_Right':.08,'Jacket_Back':.12}

def configure(scene):
    rows=[]
    for o in list(scene.objects):
        raw=o.name.split('.')[0]
        name=next((part for part in sorted(DEFAULT_TOTAL_KG,key=len,reverse=True) if raw==part or raw.endswith('_'+part)),None)
        if o.type!='MESH' or o.get('SimulationOnly') or name is None:continue
        total=DEFAULT_TOTAL_KG[name]
        cloth=next((m for m in o.modifiers if m.type=='CLOTH'),None)
        if cloth is None:continue
        probe=o.copy();probe.animation_data_clear();scene.collection.objects.link(probe)
        probe.hide_viewport=False;probe.hide_render=True;probe.hide_set(False)
        index=list(o.modifiers).index(cloth)
        for modifier in list(probe.modifiers)[index:]:probe.modifiers.remove(modifier)
        bpy.context.view_layer.update()
        evaluated=probe.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        count=len(mesh.vertices);evaluated.to_mesh_clear();bpy.data.objects.remove(probe,do_unlink=True)
        assert count
        before=cloth.settings.mass
        o['GarmentMassKg']=float(o.get('GarmentMassKg',total))
        o.id_properties_ui('GarmentMassKg').update(description='Approximate total garment-part mass in kilograms; editable material parameter.',min=.001,max=10)
        # Use the point count entering the cloth modifier, not rendered subdivision.
        cloth.settings.mass=o['GarmentMassKg']/count
        cloth.settings.driver_remove('mass')
        curve=cloth.settings.driver_add('mass')
        # New drivers include 0–1 keyframes. Very small mass values snap to
        # the zero key even with linear interpolation; use an identity generator.
        curve.keyframe_points.clear()
        for modifier in list(curve.modifiers):curve.modifiers.remove(modifier)
        mapping=curve.modifiers.new('GENERATOR');mapping.poly_order=1;mapping.coefficients=(0,1)
        curve.extrapolation='LINEAR';driver=curve.driver
        variable=driver.variables.new();variable.name='total';variable.targets[0].id=o;variable.targets[0].data_path='["GarmentMassKg"]'
        driver.expression='total/'+str(count)
        rows.append({'object':o.name,'vertices':count,'old_vertex_mass_kg':before,'total_mass_kg':o['GarmentMassKg'],'vertex_mass_kg':cloth.settings.mass})
    return rows
