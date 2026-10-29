import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_alternate_jackets as repair
import rebuild_updated_characters as build
OUT=repair.OUT;d=OUT/'Medium';samples=build.ROOT/'Resources/Models/Animation/Samples'
try:
 for level,name in [('Sample_Demo','Medium_Sparring_Samples.blend'),('Sample_Kick','Front_Kick.blend')]:repair.run('Medium',level,samples/name)
 paths=[]
 for clip in ['Guard_Idle','Straight_Punches','Front_Kick']:
  bpy.ops.wm.open_mainfile(filepath=str(d/('Front_Kick.blend' if clip=='Front_Kick' else 'Medium_Sparring_Samples.blend')));r=bpy.data.objects['RIG_Body_Medium'];r['JacketStyle']=1;build.refresh(r);s=bpy.context.scene
  if clip!='Front_Kick':
   r.animation_data.action=bpy.data.actions['Sample_'+clip]
   for name in repair.PANELS+['Belt_Tail_Left','Belt_Tail_Right']:
    keys=bpy.data.objects[name].data.shape_keys
    if keys:
     keys.animation_data.action=None
     for k in keys.key_blocks:
      if k.name.startswith('ClothBake'):k.value=0
  s.frame_start=1;s.frame_end=72;s.frame_set(1);p=d/(clip+'.fbx');build.export(r,p,True);paths.append(p)
 results=[]
 for path in paths:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert any(o.name.split('.')[0]=='Jacket_WhiteVNeck' for o in meshes);assert not any(o.name.split('.')[0]=='Jacket' for o in meshes)
  assert rigs[0].animation_data.action.frame_range[1]>=72
  if path.stem=='Front_Kick':
   for f in [1,26,35,72]:
    bpy.context.scene.frame_set(f)
    for name in repair.PANELS:
     o=next(o for o in meshes if o.name.split('.')[0]==name);assert abs(sum(k.value for k in o.data.shape_keys.key_blocks if k.name.startswith('ClothBake'))-1)<.02
  results.append({'file':str(path.relative_to(OUT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bones':341,'reimport_passed':True})
 (OUT/'sample_export_validation.json').write_text(json.dumps({'passed':True,'files':results},indent=2));repair.log('SAMPLES VERIFIED')
except:repair.log(traceback.format_exc());raise
