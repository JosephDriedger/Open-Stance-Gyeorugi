import bpy,json
from pathlib import Path
ROOT=Path('D:/Open-Stance-Gyeorugi');OUT=ROOT/'Resources/Models/VisualFitRepair';OUT.mkdir(exist_ok=True)
rows={}
for kind,level in [('Tall','Gameplay_High'),('Compact','Crowd_Far'),('Medium','Gameplay_High')]:
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite'/kind/(level+'.blend')))
 r=bpy.data.objects['RIG_Body_'+kind]
 row={'bones':{},'objects':[],'rig_props':{k:r[k] for k in ['HairStyle','ProtectorStyle','HelmetStyle'] if k in r}}
 for n in ['upperarm_l','lowerarm_l','hand_l','pelvis','spine_03','head']:
  b=r.data.bones[n];row['bones'][n]={'head':list(r.matrix_world@b.head_local),'tail':list(r.matrix_world@b.tail_local)}
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and (o.name in ['Body','Head','Jacket','Jacket_WhiteVNeck','Belt_Knot'] or o.name.startswith(('Quilted','Smooth','Hair_Crew'))):
   pts=[o.matrix_world@v.co for v in o.data.vertices]
   row['objects'].append({'name':o.name,'count':len(pts),'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)],'modifiers':[(m.name,m.type) for m in o.modifiers],'keys':list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []})
 rows[kind]=row
(OUT/'inspection.json').write_text(json.dumps(rows,indent=2))
