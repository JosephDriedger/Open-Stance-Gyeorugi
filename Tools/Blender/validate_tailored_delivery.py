import bpy,sys,json,hashlib,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
import rebuild_updated_characters as build
OUT=repair.OUT
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
 for kind in build.PRESETS:
  for level in repair.LEVELS:wait(OUT/kind/(level+'_validation.json'))
 rows=[]
 for kind in build.PRESETS:
  for level in repair.LEVELS:
   check=OUT/kind/(level+'_validation.json');wait(check);report=json.loads(check.read_text());path=OUT/kind/report['file'];assert sha(path)==report['sha256']
   bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['RIG_Body_'+kind];s=bpy.context.scene;full=level in ['Preview','Animation'];crowd=level.startswith('Crowd')
   assert len(r.data.bones)==(25 if crowd else 341)
   if full:
    assert len(bpy.data.objects['RIG_Face_'+kind].data.bones)==874
    assert sum(bool(o.get('MarkerLabel')) for o in s.objects)==41
   original=r['JacketStyle'];wear=r['Wear_Jacket'];counts={}
   for style in [0,1]:
    r['JacketStyle']=style;r['Wear_Jacket']=True;build.refresh(r)
    assert bpy.data.objects['Jacket'].hide_render==(style!=0)
    assert bpy.data.objects['Jacket_WhiteVNeck'].hide_render==(style!=1)
    assert all(not bpy.data.objects[n].hide_render for n in repair.PANELS)
    for name in repair.PARTS:
     o=bpy.data.objects.get(name)
     if not o:continue
     for owner in [o,o.data.shape_keys]:
      if owner and owner.animation_data:assert all(d.is_valid for d in owner.animation_data.drivers),(kind,level,name)
    deps=bpy.context.evaluated_depsgraph_get();total=0
    for o in build.meshes():
     if not o.hide_render:
      ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();total+=len(me.loop_triangles);ev.to_mesh_clear()
    counts[str(style)]=total
   rows.append({'preset':kind,'profile':level,'file':str(path.relative_to(OUT)),'sha256':sha(path),'style_triangle_counts':counts,'body_unchanged':report['body_unchanged'],'rest_hierarchy_unchanged':report['rest_hierarchy_unchanged'],'animation_keyframes_unchanged':report['animation_keyframes_unchanged'],'drivers_valid':True})
  log(kind+' native verified')
 (OUT/'delivery_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2));log('NATIVE COMPLETE')
 mb=[]
 for kind in build.PRESETS:
  for style in ['WhiteWrap','WhiteVNeck']:
   for suffix in ['','_Sparring']:
    name='OpenStance_'+kind+suffix;d=OUT/'MotionBuilder'/kind/style;check=d/('validation_'+name+'.json');wait(check);report=json.loads(check.read_text());path=d/(name+'.fbx')
    assert report['source_sha256']==sha(build.ROOT/report['source']);assert report['characterized'] and report['control_rig'] and report['reopened_successfully']
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    names={o.name.split('.')[0].split(':')[-1] for o in meshes};expected='Jacket' if style=='WhiteWrap' else 'Jacket_WhiteVNeck';assert expected in names
    for part in ['Pants']+repair.PANELS:
     o=next(o for o in meshes if o.name.split('.')[0].split(':')[-1]==part);assert o.data.shape_keys and any(k.name.startswith('Squat_') for k in o.data.shape_keys.key_blocks)
    mb.append({'file':str(path.relative_to(OUT)),'sha256':sha(path),'garment_style':style,'characterization_and_control_rig_verified':True})
  log(kind+' MotionBuilder verified')
 (OUT/'motionbuilder_validation.json').write_text(json.dumps({'passed':True,'files':mb},indent=2));log('COMPLETE')
except:log(traceback.format_exc());raise
