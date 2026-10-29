import bpy,sys,json,hashlib,traceback,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
import rebuild_updated_characters as build
OUT=repair.OUT=build.ROOT/'Resources/Models/HairExportFinish'
def log(s):
 with (OUT/'exports.log').open('a') as f:f.write(str(s)+'\n')
def run(kind,style):
 native=OUT/kind;d=native/('WhiteVNeck' if style else 'WhiteWrap');d.mkdir(parents=True,exist_ok=True);deadline=time.monotonic()+3600
 while not all((native/(p+'_validation.json')).exists() for p in repair.LEVELS):
  if time.monotonic()>deadline:raise RuntimeError('Native build timeout '+kind)
  time.sleep(5)
 files=[]
 for level in ['Crowd_Near','Crowd_Far']:
  bpy.ops.wm.open_mainfile(filepath=str(native/(level+'.blend')));r=bpy.data.objects['RIG_Body_'+kind];r.animation_data.action=None;r['JacketStyle']=style;build.refresh(r)
  for tr in r.animation_data.nla_tracks:tr.mute=True
  if level.startswith('Crowd'):
   name=level+'.fbx';build.export(r,d/name);files.append(name)
   if level=='Crowd_Near':
    for clip in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
     r.animation_data.action=bpy.data.actions['Crowd_'+clip];bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=61;bpy.context.scene.frame_set(1)
     name='Crowd_'+clip+'.fbx';build.export(r,d/name,True);files.append(name)
  else:
   for outfit in ['Sparring','Dobok']:
    for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[key]=outfit=='Sparring'
    build.refresh(r);name=level+'_'+outfit+'.fbx';build.export(r,d/name);files.append(name)
  log(kind+' '+level+' exported')
 rows=[row for row in json.loads((d/'export_validation.json').read_text())['files'] if not row['file'].startswith('Crowd')]
 for name in files:
  path=d/name;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1
  r=rigs[0];assert len(r.data.bones)==(25 if name.startswith('Crowd') else 341)
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert meshes
  for o in meshes:
   assert any(m.type=='ARMATURE' and m.object==r for m in o.modifiers),o.name
   assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.003 for v in o.data.vertices),o.name
  corrected={}
  for part in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
   o=next(o for o in meshes if o.name.split('.')[0]==part);assert o.data.shape_keys
   k=next(k for k in o.data.shape_keys.key_blocks if k.name.startswith('Squat_'));corrected[part]=k.name
  clip=name.startswith('Crowd') and name not in ['Crowd_Near.fbx','Crowd_Far.fbx']
  if clip:
   assert r.animation_data.action and r.animation_data.action.frame_range[1]>=60
   bpy.context.scene.frame_set(16);bpy.context.view_layer.update()
   if 'Seated' in name:
    pants=next(o for o in meshes if o.name.split('.')[0]=='Pants')
    assert pants.data.shape_keys.key_blocks['Squat_Fold_Soften'].value>.5,'Missing baked seated correction'
  rows.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bones':len(r.data.bones),'normalized_weights':True,'corrective_morphs':corrected,'animation':clip})
 (d/'export_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2));log(kind+' EXPORTS VERIFIED')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else build.PRESETS
  for kind in args:
   for style in [0,1]:run(kind,style)
  log('COMPLETE')
 except:log(traceback.format_exc());raise
