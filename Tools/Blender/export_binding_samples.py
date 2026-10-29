import bpy,sys,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/BindingDelivery'
old={x['file']:x['sha256'] for x in json.loads((ROOT/'Resources/Models/HairExportFinish/published.json').read_text())['files']};rows=[]
for style in [0,1]:
 for clip in ['Guard_Idle','Straight_Punches','Front_Kick']:
  rel=Path('Resources/Models/Animation/Samples')/('Front_Kick.blend' if clip=='Front_Kick' else 'Medium_Sparring_Samples.blend')
  ready=OUT/(hashlib.sha256(rel.as_posix().encode()).hexdigest()[:16]+'.json');deadline=time.monotonic()+1800
  while not ready.exists():
   assert time.monotonic()<deadline
   time.sleep(2)
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'Files'/rel));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['JacketStyle']=style;build.refresh(r)
  if clip!='Front_Kick':
   r.animation_data.action=bpy.data.actions['Sample_'+clip]
   for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back','Belt_Tail_Left','Belt_Tail_Right']:
    keys=bpy.data.objects[name].data.shape_keys
    if keys:
     if keys.animation_data:keys.animation_data.action=None
     for k in keys.key_blocks:
      if k.name.startswith('ClothBake'):k.value=0
  s.frame_start=1;s.frame_end=72;s.frame_set(1)
  relative=rel.parent/('WhiteVNeck' if style else '')/(clip+'.fbx');target=OUT/'Files'/relative;target.parent.mkdir(parents=True,exist_ok=True)
  build.export(r,target,True);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(target))
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341 and rigs[0].animation_data.action.frame_range[1]>=72
  rows.append({'file':relative.as_posix(),'before_sha256':old[relative.as_posix()],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'reimport_passed':True,'frames':72})
(OUT/'sample_exports.json').write_text(json.dumps({'files':rows},indent=2))
