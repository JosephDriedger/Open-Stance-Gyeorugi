import bpy,sys,json,hashlib,time,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_alternate_jackets as repair
import rebuild_updated_characters as build
OUT=repair.OUT
def wait(path):
 deadline=time.monotonic()+3600
 while not path.exists():
  if time.monotonic()>deadline:raise RuntimeError('Timeout '+str(path))
  time.sleep(5)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def log(s):
 with (OUT/'delivery.log').open('a') as f:f.write(str(s)+'\n')
try:
 mb=[]
 for kind in build.PRESETS:
  for suffix in ['','_Sparring']:
   name='OpenStance_'+kind+suffix;directory=OUT/'MotionBuilder'/kind;check=directory/('validation_'+name+'.json');wait(check)
   report=json.loads(check.read_text());path=directory/(name+'.fbx');assert report['source_sha256']==sha(build.ROOT/report['source']);assert report['reopened_successfully'] and report['characterized'] and report['control_rig']
   bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];morphs={}
   for part in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
    o=next(o for o in meshes if o.name.split('.')[0].split(':')[-1]==part);assert o.data.shape_keys
    morphs[part]=[k.name for k in o.data.shape_keys.key_blocks if k.name.startswith('Squat_')];assert morphs[part]
   assert any(o.name.split('.')[0].split(':')[-1]=='Belt_Waistband' for o in meshes)
   assert any(o.name.split('.')[0].split(':')[-1]=='Jacket_WhiteVNeck' for o in meshes)
   assert not any(o.name.split('.')[0].split(':')[-1]=='Jacket' for o in meshes)
   mb.append({'file':str(path.relative_to(OUT)),'sha256':sha(path),'corrective_morphs':morphs,'characterization_and_controls_reopened':True})
  log(kind+' MotionBuilder geometry verified')
 (OUT/'motionbuilder_validation.json').write_text(json.dumps({'passed':True,'files':mb},indent=2))
 rows=[]
 for kind in build.PRESETS:
  for level in repair.LEVELS:
   check=OUT/kind/(level+'_validation.json');wait(check);report=json.loads(check.read_text());path=OUT/kind/report['file'];assert sha(path)==report['sha256']
   bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['RIG_Body_'+kind];s=bpy.context.scene;parts=[bpy.data.objects[n] for n in (repair.PANELS+['Jacket','Jacket_WhiteVNeck','Pants'])]
   bpy.context.view_layer.update()
   for o in parts:
    assert all(m.object==r for m in o.modifiers if m.type=='ARMATURE')
    for owner in [o,o.data.shape_keys]:
     if owner and owner.animation_data:assert all(d.is_valid for d in owner.animation_data.drivers),(kind,level,o.name)
   counts={};deps=bpy.context.evaluated_depsgraph_get()
   for o in build.meshes():
    if not o.hide_render:
     ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();counts[o.name]=len(me.loop_triangles);ev.to_mesh_clear()
   rows.append({'preset':kind,'profile':level,'visible_evaluated_triangles':sum(counts.values()),'parts':counts,'file':str(path.relative_to(OUT)),'sha256':sha(path),'garment_drivers_valid':True})
  log(kind+' native delivery verified')
 (OUT/'delivery_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2));log('COMPLETE')
except:log(traceback.format_exc());raise
