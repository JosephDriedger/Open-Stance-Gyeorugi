import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi');out=root/'Resources/Models/CollarEarRepair/Prepared';out.mkdir(parents=True,exist_ok=True)
for kind in ['Stocky','Tall','Medium','Compact','LeanTall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']:
 bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite'/kind/'Preview.blend'));rows={}
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and ('__Foam_Ear_' in o.name or '__Ear_Pad_Piping' in o.name):
   rows[o.name]={'points':[list(o.matrix_world@v.co) for v in o.data.vertices],'faces':[list(p.vertices) for p in o.data.polygons]}
 (out/(kind+'.json')).write_text(json.dumps(rows))
(out/'complete.txt').write_text('Complete')
