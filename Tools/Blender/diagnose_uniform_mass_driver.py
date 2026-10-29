import bpy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from normalize_uniform_cloth_mass import configure
root=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/Animation/DummyMotionTests/Compact/DummyMotion_Compact.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Compact'];rows=configure(s)
o=bpy.data.objects['Jacket'];cloth=next(m for m in o.modifiers if m.type=='CLOTH')
print('PROPERTY',o.get('GarmentMassKg'),'RANGE',cloth.settings.bl_rna.properties['mass'].hard_min,cloth.settings.bl_rna.properties['mass'].hard_max,flush=True)
for live in [False,True]:
    r['BlenderCloth']=live;r.update_tag();o.update_tag();s.frame_set(2);s.frame_set(1);bpy.context.view_layer.update()
    print('LIVE',live,'MASS',cloth.settings.mass,flush=True)
    for curve in o.animation_data.drivers:
        if curve.data_path.endswith('.mass'):
            print('DRIVER',curve.data_path,curve.driver.expression,curve.driver.type,curve.driver.is_valid,[(v.name,v.type,v.targets[0].id.name if v.targets[0].id else None,v.targets[0].data_path) for v in curve.driver.variables],flush=True)
            print('CURVE',[(m.type,list(m.coefficients) if hasattr(m,'coefficients') else '') for m in curve.modifiers],[(list(k.co),k.interpolation) for k in curve.keyframe_points],flush=True)
