import bpy,json
from collections import Counter
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairExportFinish')
bpy.ops.import_scene.fbx(filepath=str(p/'Crowd_Near_Pilot.fbx'))
o=next(o for o in bpy.context.scene.objects if o.name.split('.')[0]=='Head');print('MATERIALS',[(i,m.name) for i,m in enumerate(o.data.materials)])
print('CROWN',Counter(f.material_index for f in o.data.polygons if sum((o.matrix_world@o.data.vertices[i].co).z for i in f.vertices)/len(f.vertices)>1.72))
for f in o.data.polygons:
 z=sum((o.matrix_world@o.data.vertices[i].co).z for i in f.vertices)/len(f.vertices)
 if z>1.72 and f.material_index!=0:print('BAD?',f.index,f.material_index,z)
