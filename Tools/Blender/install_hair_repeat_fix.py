"""Apply the verified UV wrap repair, preserving geometry, rigs and actions."""
import bpy, sys, json, hashlib, shutil
from array import array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
ROOT=base.ROOT
OUT=ROOT/'Resources/Models/FinalRefinement/HairRepeat'
OUT.mkdir(parents=True,exist_ok=True)
archive=ROOT/'Resources/Models/Archive/Before_Hair_Repeat_20261023'
manifest=json.loads((ROOT/'Resources/Models/HairExportFinish/published.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
def geometry():
 h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o.type!='MESH':continue
  h.update(o.name.encode())
  coords=array('f',[0.0])*(len(o.data.vertices)*3)
  o.data.vertices.foreach_get('co',coords);h.update(coords.tobytes())
  if o.data.shape_keys:
   for k in o.data.shape_keys.key_blocks:
    h.update(k.name.encode())
    coords=array('f',[0.0])*(len(k.data)*3)
    k.data.foreach_get('co',coords);h.update(coords.tobytes())
 return h.hexdigest()
rows=[]
for row in manifest['files']:
 if not row['file'].endswith('.blend'):continue
 src=ROOT/row['file'];report=OUT/(hashlib.sha256(row['file'].encode()).hexdigest()[:16]+'.json')
 if report.exists():
  old=json.loads(report.read_text());assert sha(src)==old['sha256'];rows.append(old);continue
 assert sha(src)==row['sha256'],('Source changed',src)
 bpy.ops.wm.open_mainfile(filepath=str(src))
 rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'};actions=base.actions();geo=geometry();changed=[]
 mats={m for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Hair_') for m in o.data.materials if m}
 for mat in mats:
  if not mat.use_nodes:continue
  for n in mat.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.extension!='REPEAT':
    changed.append([mat.name,n.name,n.extension]);n.extension='REPEAT'
 if changed:
  backup=archive/row['file'];backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(src,backup)
  assert sha(backup)==row['sha256']
  staged=OUT/'pending.blend';bpy.context.preferences.filepaths.save_version=0
  bpy.ops.wm.save_as_mainfile(filepath=str(staged),compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(staged))
  assert geo==geometry() and actions==base.actions()
  assert rigs=={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
  assert sha(src)==row['sha256']
  shutil.copy2(staged,src);assert sha(src)==sha(staged)
 result={'file':row['file'],'sha256':sha(src),'before_sha256':row['sha256'],'changed_nodes':changed,'geometry_actions_rigs_preserved':True}
 report.write_text(json.dumps(result,indent=2));rows.append(result)
 print('HAIR_REPEAT_VERIFIED '+row['file'],flush=True)
(OUT/'published.json').write_text(json.dumps({'passed':True,'files':rows,'archive':str(archive)},indent=2))
print('HAIR_REPEAT_COMPLETE '+str(len(rows)),flush=True)
