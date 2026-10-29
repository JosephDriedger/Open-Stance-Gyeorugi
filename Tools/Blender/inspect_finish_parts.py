import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi')
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite/Medium/Preview.blend'))
rows={}
for o in bpy.context.scene.objects:
 if o.type=='MESH' and (o.name.startswith('Belt') or 'Yoke' in o.name):
  ps=[o.matrix_world@v.co for v in o.data.vertices]
  rows[o.name]={'verts':len(ps),'bounds':[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)],'keys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'groups':[g.name for g in o.vertex_groups], 'modifiers':[(m.name,m.type) for m in o.modifiers]}
(root/'Resources/Models/FinishQuality/parts.json').write_text(json.dumps(rows,indent=2))
