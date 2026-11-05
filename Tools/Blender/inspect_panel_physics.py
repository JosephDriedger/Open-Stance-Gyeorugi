import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi')
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/FinalRefinement/WorldUniformClothSurface/Candidate.blend'))
s=bpy.context.scene;s.frame_set(1);rows=[]
for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
 o=bpy.data.objects[name];c=next(m for m in o.modifiers if m.type=='CLOTH');v=[o.matrix_world@x.co for x in o.data.vertices]
 rows.append({'name':name,'bbox':[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)],'mass':c.settings.mass,'time':c.settings.time_scale,'pin':c.settings.vertex_group_mass,'scale':list(o.matrix_world.to_scale()),'thickness':[(m.name,m.thickness) for m in o.modifiers if m.type=='SOLIDIFY'],'keys':[(k.name,k.value) for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []})
print(json.dumps(rows,indent=2))

