import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/UniformRebuild')
def curves(a):
 if hasattr(a,'fcurves'):return list(a.fcurves)
 return [fc for layer in a.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
def log(s):
 with (OUT/'package.log').open('a') as f:f.write(str(s)+'\n')
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Uniform_Corrected.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];names=json.loads((OUT/'cloth_objects.json').read_text())
 if 'Sample_Demo' not in bpy.data.actions:
  with bpy.data.libraries.load(str(OUT.parent/'Medium_Sparring_Samples.blend'),link=False) as (source,target):target.actions=['Sample_Demo']
 bpy.data.actions['Sample_Demo'].use_fake_user=True
 keys=[bpy.data.objects[n].data.shape_keys for n in names];actions=[k.animation_data.action for k in keys]
 for k in keys:
  k.animation_data.action=None
  for block in k.key_blocks:block.value=1 if block.name=='ClothBake_01' else 0
 for clip in ['Guard_Idle','Straight_Punches']:
  r.animation_data.action=bpy.data.actions['Sample_'+clip];scene.frame_set(1);build.export(r,OUT/(clip+'.fbx'),True)
 for k,a in zip(keys,actions):
  k.animation_data.action=a
  for fc in curves(a):
   for p in fc.keyframe_points:p.co.x+=144;p.handle_left.x+=144;p.handle_right.x+=144
  key=k.key_blocks['ClothBake_01'];key.value=1;key.keyframe_insert('value',frame=1);key.keyframe_insert('value',frame=144)
 r.animation_data.action=bpy.data.actions['Sample_Demo'];scene.frame_end=216;scene.frame_set(1)
 build.view.camera(scene,(2.5,-4,2.0),(0,-.15,.94),2.3)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 report={'body_bones':341,'files':{}}
 for filename in ['Guard_Idle.fbx','Straight_Punches.fbx','Front_Kick_Corrected.fbx']:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/filename))
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
  assert rigs[0].animation_data.action and rigs[0].animation_data.action.frame_range[1]>=72
  cloth=[]
  for name in names:
   o=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(name));assert o.data.shape_keys and len(o.data.shape_keys.key_blocks)==73;cloth.append(name)
   if filename.startswith('Front'):
    for f in [1,26,35,72]:
     bpy.context.scene.frame_set(f);bpy.context.view_layer.update();assert abs(sum(k.value for k in o.data.shape_keys.key_blocks if k.name.startswith('ClothBake_'))-1)<.01
  for tex in ['Cotton_BaseColor','Belt_BaseColor','Cotton_Normal','Cotton_Roughness']:
   assert any(tex in im.name and im.size[0]==512 for im in bpy.data.images),tex
  report['files'][filename]={'reimport_passed':True,'cloth_parts':cloth,'texture_maps':4,'sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest()}
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));log('EXPORTS VERIFIED')
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'));scene=bpy.context.scene
 frames=OUT/'Frames';side=OUT/'SideFrames';frames.mkdir(exist_ok=True);side.mkdir(exist_ok=True)
 for f in range(1,217,2):
  scene.frame_set(f);scene.render.filepath=str(frames/f'{(f-1)//2:04d}.png');bpy.ops.render.render(write_still=True)
  if f>=145:
   build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25);scene.render.filepath=str(side/f'{(f-145)//2:04d}.png');bpy.ops.render.render(write_still=True)
   build.view.camera(scene,(2.5,-4,2.0),(0,-.15,.94),2.3)
  if f%24==1:log('RENDER '+str(f))
 log('COMPLETE')
except:log(traceback.format_exc());raise
