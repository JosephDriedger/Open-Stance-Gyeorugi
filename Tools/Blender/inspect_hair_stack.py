import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/HairClothRevision/Hair_Pilot.blend')
rows=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH' and ('Hair' in o.name or 'Scalp' in o.name):
  rows.append({'name':o.name,'hidden':o.hide_render,'vertices':len(o.data.vertices),'materials':[m.name for m in o.data.materials]})
Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairClothRevision/hair_stack.json').write_text(json.dumps(rows,indent=2))
