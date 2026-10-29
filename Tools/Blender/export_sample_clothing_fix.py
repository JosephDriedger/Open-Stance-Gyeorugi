import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
def curves(action):
 if hasattr(action,'fcurves'):return list(action.fcurves)
 return [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
def shift(action,amount):
 for fc in curves(action):
  for p in fc.keyframe_points:
   p.co.x+=amount;p.handle_left.x+=amount;p.handle_right.x+=amount
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium']
 shapes=[bpy.data.objects[n].data.shape_keys for n in ['Jacket','Belt']]
 scene.frame_start=1;scene.frame_end=72
 for name in ['Guard_Idle','Straight_Punches','Front_Kick']:
  r.animation_data.action=bpy.data.actions['Sample_'+name]
  if name=='Front_Kick':
   for keys in shapes:shift(keys.animation_data.action,-144)
  scene.frame_set(1);build.export(r,OUT/(name+'.fbx'),True)
  if name=='Front_Kick':
   for keys in shapes:shift(keys.animation_data.action,144)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/'Front_Kick.fbx'))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');assert len(rig.data.bones)==341
 report={'bones':341,'correctives':{}}
 for prefix in ['Jacket','Belt']:
  o=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix));keys=o.data.shape_keys
  assert keys and len(keys.key_blocks)>40 and keys.animation_data and keys.animation_data.action
  vals=[]
  for f in [1,26,35,45,72]:
   bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
   vals.append(sum(k.value for k in keys.key_blocks if k.name.startswith('KickContact_')))
  assert vals[0]<.01 and vals[1]>.99 and vals[2]>.99 and vals[-1]<.01,vals
  report['correctives'][prefix]={'shape_count':len(keys.key_blocks),'sample_values':vals}
 (OUT/'clothing_export_validation.json').write_text(json.dumps(report,indent=2))
 with (OUT/'build.log').open('a') as f:f.write('CLOTHING EXPORT PASSED\n')
except:
 with (OUT/'build.log').open('a') as f:f.write(traceback.format_exc())
 raise
