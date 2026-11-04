import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi')
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite/Stocky/Gameplay_High.blend'))
for o in bpy.data.objects:
 if o.type=='MESH' and (o.name.startswith('Body') or 'Foot' in o.name):
  print(o.name,len(o.data.vertices),[(m.name,m.type,getattr(m,'vertex_group',''),getattr(m,'invert_vertex_group',False)) for m in o.modifiers],[(g.name,g.index) for g in o.vertex_groups if 'Cover' in g.name or 'Hide' in g.name])
