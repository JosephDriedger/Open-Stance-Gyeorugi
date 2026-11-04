import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from refine_pants_cloth import configure
p=Path('D:/Open-Stance-Gyeorugi')
bpy.ops.wm.open_mainfile(filepath=str(p/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Medium_Wrap.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;s.frame_set(1);bpy.context.view_layer.update();configure(s)
o=bpy.data.objects['Pants'];c=next(m for m in o.modifiers if m.type=='CLOTH')
print('CLOTH_GROUP',c.settings.vertex_group_mass,c.settings.pin_stiffness)
for i in [1429,1430,779,2306]:
 v=o.data.vertices[i];print('VERTEX',i,list(o.matrix_world@v.co),[(o.vertex_groups[g.group].name,g.weight) for g in v.groups])
print('KNEE',list(r.matrix_world@r.data.bones['calf_l'].head_local))
print('MODS',[(m.name,m.type,m.show_viewport) for m in o.modifiers])
print('CLOTH_DRIVERS',[(d.data_path,d.driver.expression) for d in o.animation_data.drivers])
