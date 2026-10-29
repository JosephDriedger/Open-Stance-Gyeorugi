import bpy,json
from pathlib import Path
root=Path('D:/Open-Stance-Gyeorugi')
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'))
rows={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not (o.name in ['Pants','Jacket_Front_Left','Jacket_Back'] or o.name.startswith(('Quilted_Lace_Back__','Hair_Bob','Open_Face'))):continue
 keys=o.data.shape_keys
 rows[o.name]={'vertices':len(o.data.vertices),'groups':[g.name for g in o.vertex_groups],'modifiers':[(m.name,m.type) for m in o.modifiers],'keys':[k.name for k in keys.key_blocks] if keys else [],'drivers':[(d.data_path,d.driver.expression) for d in keys.animation_data.drivers] if keys and keys.animation_data else [],'sample_weights':[(tuple(v.co),[(o.vertex_groups[g.group].name,round(g.weight,3)) for g in v.groups]) for v in list(o.data.vertices)[::max(1,len(o.data.vertices)//8)]]}
out=root/'Resources/Models/FollowupFix';out.mkdir(exist_ok=True)
(out/'inspection.json').write_text(json.dumps(rows,indent=2))

