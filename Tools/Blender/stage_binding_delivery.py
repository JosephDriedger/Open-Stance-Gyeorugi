"""Stage edge clearance changes with rig/action and geometry round-trip checks."""
import bpy,sys,json,hashlib
from array import array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from repair_protector_binding import repair
ROOT=base.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/BindingDelivery';OUT.mkdir(exist_ok=True)
sources=json.loads((OUT.parent/'HairRepeat/published.json').read_text())['files']
sources+=json.loads((OUT.parent/'BodyPhysics/delivery.json').read_text())['files']
sources+=json.loads((OUT.parent/'fitted_belt_delivery.json').read_text())['files']
batch=int(sys.argv[-1]);rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry():
 h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  if o.type!='MESH':continue
  h.update(o.name.encode());co=array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',co);h.update(co.tobytes())
  if o.data.shape_keys:
   for k in o.data.shape_keys.key_blocks:
    co=array('f',[0])*(len(k.data)*3);k.data.foreach_get('co',co);h.update(k.name.encode());h.update(co.tobytes())
 return h.hexdigest()
for index,row in enumerate(sources):
 if index%3!=batch:continue
 source=ROOT/row['file'];assert sha(source)==row['sha256'],source
 report=OUT/(hashlib.sha256(row['file'].encode()).hexdigest()[:16]+'.json')
 if report.exists():continue
 bpy.ops.wm.open_mainfile(filepath=str(source));rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'};actions=base.actions();changes=[]
 for scene in bpy.data.scenes:changes+=repair(scene)
 assert rigs=={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'} and actions==base.actions()
 result={'file':row['file'],'before_sha256':row['sha256'],'changed':changes,'rigs_actions_preserved':True}
 if changes:
  expected=geometry()
  for im in bpy.data.images:
   if im.source=='FILE' and im.filepath and not im.packed_file:im.pack()
  staged=OUT/'Files'/row['file'];staged.parent.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0
  bpy.ops.wm.save_as_mainfile(filepath=str(staged),compress=True);bpy.ops.wm.open_mainfile(filepath=str(staged))
  assert geometry()==expected and base.actions()==actions
  assert rigs=={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
  result['sha256']=sha(staged)
 else:result['sha256']=row['sha256']
 report.write_text(json.dumps(result,indent=2));print('BINDING_STAGED '+row['file'],flush=True)
print('BATCH_COMPLETE',batch,flush=True)
