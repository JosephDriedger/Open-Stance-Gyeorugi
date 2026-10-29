import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/TPose/OpenStance_Medium_Tpose.blend')
rows=[]
for n in ['Body','Jacket','Jacket_WhiteVNeck','Pants']:
 o=bpy.data.objects[n];row={'name':n,'scale':list(o.matrix_world.to_scale()),'modifiers':[]}
 for m in o.modifiers:
  d={'name':m.name,'type':m.type}
  if m.type=='SOLIDIFY':d.update(thickness=m.thickness,offset=m.offset)
  if m.type=='MASK':d.update(group=m.vertex_group,invert=m.invert_vertex_group)
  row['modifiers'].append(d)
 rows.append(row)
Path('D:/Open-Stance-Gyeorugi/Resources/Models/TPose/opening_inspection.json').write_text(json.dumps(rows,indent=2))
