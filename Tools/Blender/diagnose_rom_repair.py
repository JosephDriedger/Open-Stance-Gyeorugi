import bpy,json,sys
from pathlib import Path
ROOT=Path('D:/Open-Stance-Gyeorugi');out=ROOT/'Resources/Models/ROMRepair';out.mkdir(exist_ok=True)
report={}
for kind in ['Sample','Medium','Stocky','Female_Strong']:
 path=ROOT/'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend' if kind=='Sample' else ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
 bpy.ops.wm.open_mainfile(filepath=str(path));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));r.data.pose_position='REST';bpy.context.view_layer.update()
 row={'bones':{n:list(r.matrix_world@r.data.bones[n].head_local) for n in ['pelvis','spine_03','head','upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l']},'objects':{}}
 for name in ['Body','Jacket','Pants','Belt','Jacket_Front_Left','Jacket_Back']:
  o=bpy.data.objects.get(name)
  if not o:continue
  ps=[o.matrix_world@v.co for v in o.data.vertices];mods=[]
  for m in o.modifiers:
   item={'name':m.name,'type':m.type}
   for a in ['thickness','offset','vertex_group','invert_vertex_group']: 
    if hasattr(m,a):item[a]=getattr(m,a)
   mods.append(item)
  row['objects'][name]={'n':len(ps),'bounds':[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)],'world_scale':list(o.matrix_world.to_scale()),'mods':mods,'keys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'groups':[g.name for g in o.vertex_groups]}
 report[kind]=row
(out/'diagnostics.json').write_text(json.dumps(report,indent=2))
