import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi');out=root/'Resources/Models/CollarEarRepair';out.mkdir(exist_ok=True)
rows={}
for level in ['Preview','Gameplay_High','Crowd_Far']:
 bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite/Stocky'/(level+'.blend')))
 rows[level]={}
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and (o.name.startswith(('Jacket','Collar','Helmet','Vented','Open','Closed')) or 'Ear' in o.name):
   ps=[o.matrix_world@v.co for v in o.data.vertices]
   rows[level][o.name]={'vertices':len(ps),'keys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'modifiers':[(m.name,m.type) for m in o.modifiers],'bounds':[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)]}
(out/'inventory.json').write_text(json.dumps(rows,indent=2))
