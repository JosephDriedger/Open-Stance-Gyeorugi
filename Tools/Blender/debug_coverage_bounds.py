import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/OpeningRepair/Medium/Gameplay_High.blend')
r=bpy.data.objects['RIG_Body_Medium'];o=bpy.data.objects['Body'];a=r.matrix_world@r.data.bones['lowerarm_l'].head_local;b=r.matrix_world@r.data.bones['hand_l'].head_local;axis=(b-a).normalized();rows=[]
names={g.index:g.name for g in o.vertex_groups}
for v in o.data.vertices:
 w={names[g.group]:g.weight for g in v.groups};p=o.matrix_world@v.co
 if any(('lowerarm' in n or 'hand_l' in n) and value>.1 for n,value in w.items()):
  t=(p-b).dot(axis);rad=(p-b-axis*t).length
  rows.append({'p':list(p),'t':t,'rad':rad,'jacket':w.get('CoveredBy_Jacket',0),'pants':w.get('CoveredBy_Pants',0)})
Path('D:/Open-Stance-Gyeorugi/Resources/Models/OpeningRepair/bounds.json').write_text(json.dumps({'elbow':list(a),'wrist':list(b),'vertices':rows}))
