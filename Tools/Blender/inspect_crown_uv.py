import bpy
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/CharacterSuite/Medium/Crowd_Near.blend');o=bpy.data.objects['Head'];uv=o.data.uv_layers['DiffuseUV'];rows=[]
for f in o.data.polygons:
 if min((o.matrix_world@o.data.vertices[i].co).z for i in f.vertices)>1.72:
  coords=[tuple(uv.data[i].uv) for i in f.loop_indices];span=max(max(c[j] for c in coords)-min(c[j] for c in coords) for j in [0,1]);rows.append((span,f.index,coords))
print(sorted(rows,reverse=True)[:10])
