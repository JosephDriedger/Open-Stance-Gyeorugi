import bpy,sys,json,hashlib,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
import rebuild_updated_characters as build
OUT=build.ROOT/'Resources/Models/HairExportFinish'
def wait(p):
 deadline=time.monotonic()+7200
 while not p.exists():
  if time.monotonic()>deadline:raise RuntimeError('Timeout '+str(p))
  time.sleep(5)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def log(s):
 with (OUT/'delivery.log').open('a') as f:f.write(str(s)+'\n')
try:
 mb=[]
 for kind in build.PRESETS:
  for style in ['WhiteWrap','WhiteVNeck']:
   for suffix in ['','_Sparring']:
    name='OpenStance_'+kind+suffix;d=OUT/'MotionBuilder'/kind/style;check=d/('validation_'+name+'.json');wait(check);report=json.loads(check.read_text());path=d/(name+'.fbx')
    assert report['source_sha256']==sha(build.ROOT/report['source']);assert report['characterized'] and report['control_rig'] and report['reopened_successfully']
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    head=next(o for o in meshes if o.name.split('.')[0].split(':')[-1]=='Head');assert len({p.material_index for p in head.data.polygons})>=3
    names={o.name.split('.')[0].split(':')[-1] for o in meshes};expected='Jacket' if style=='WhiteWrap' else 'Jacket_WhiteVNeck';assert expected in names
    for part in ['Pants']+repair.PANELS:
     o=next(o for o in meshes if o.name.split('.')[0].split(':')[-1]==part);assert o.data.shape_keys and any(k.name.startswith('Squat_') for k in o.data.shape_keys.key_blocks)
    mb.append({'file':str(path.relative_to(OUT)),'sha256':sha(path),'garment_style':style,'characterization_and_control_rig_verified':True})
  log(kind+' MotionBuilder verified')
 (OUT/'motionbuilder_validation.json').write_text(json.dumps({'passed':True,'files':mb},indent=2));log('COMPLETE')
except:log(traceback.format_exc());raise
