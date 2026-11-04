"""Publish the validated bind/normal repair with a complete rollback archive."""
from pathlib import Path
import json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Resources/Models/FinalRefinement/BindNormalsDelivery'
CURRENT=OUT.parent/'current_assets.json'
ARCHIVE=ROOT/'Resources/Models/Archive/Before_Bind_Normals_20261029'
def read(p): return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert not (OUT/'published.json').exists() and not ARCHIVE.exists()
 rows=[read(p) for p in OUT.glob('*.json') if len(p.stem)==16 and all(c in '0123456789abcdef' for c in p.stem)]
 assert len(rows)==375 and {r['file'] for r in rows}==set(read(OUT/'inputs.json'))
 assert all(r['joint_skin_control_animation_nodes_preserved'] and r['sdk_pose_candidate_passed'] and r['saved_pose_checks']>0 and r['saved_pose_failures']==0 for r in rows)
 checks=[read(p) for p in (OUT/'MotionBuilderChecks').glob('*.json')]
 assert len(checks)>=12
 for c in checks:
  assert c['characterized'] and c['control_rig'] and c['wrist_movement_cm']>5
  assert c['sha256']==sha(OUT/'Files'/c['file'])
 engine=read(OUT/'unreal_all.json')
 assert len(engine)==36 and all('error' not in r and r['chain_parents_ok'] and r['bones']==358 for r in engine)
 assert 'DONE 36 targets' in (OUT/'unreal_all.txt').read_text()
 assert read(OUT/'engine_warning_review.json')['passed']
 assert read(OUT/'visual_review.json')['reviewed']
 assert read(OUT/'reimport_validation.json')['passed']
 baseline=read(CURRENT);by_file={r['file']:r for r in baseline['files']}
 for r in rows:
  assert sha(ROOT/r['file'])==r['before_sha256'],r['file']
  assert sha(OUT/'Files'/r['file'])==r['sha256'],r['file']
 hashes={r['file']:r['sha256'] for r in rows};sidecars=[]
 for folder in ('MotionBuilder','MotionBuilder_BeltChain'):
  for p in (ROOT/'Resources/Models/Animation'/folder).rglob('validation_*.json'):
   data=read(p);src=data.get('source');rel_source=None
   if src:
    try: rel_source=(ROOT/src).resolve().relative_to(ROOT).as_posix()
    except ValueError: pass
   target=p.with_name(p.stem.removeprefix('validation_')+'.fbx').relative_to(ROOT).as_posix()
   if rel_source not in hashes and target not in hashes: continue
   if rel_source in hashes:
    data['source_sha256_before_bind_normals']=data.get('source_sha256');data['source_sha256']=hashes[rel_source]
   if target in hashes: data['bind_normals_target_sha256']=hashes[target]
   data['bind_normals_revision']='2026-10-29'
   data['bind_normals_note']='Bind-pose tables and zero normals repaired. Joint, skin, control and animation nodes unchanged. No recorded capture tested.'
   rel=p.relative_to(ROOT).as_posix();dst=OUT/'Files'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(data,indent=2))
   sidecars.append({'file':rel,'before_sha256':sha(p),'sha256':sha(dst)})
 changes=rows+sidecars
 assert shutil.disk_usage(ROOT).free>sum((ROOT/r['file']).stat().st_size for r in changes)+1024**3
 ARCHIVE.mkdir(parents=True);shutil.copy2(CURRENT,ARCHIVE/'current_assets_before.json')
 for r in changes:
  dst=ARCHIVE/r['file'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/r['file'],dst)
  assert sha(dst)==r['before_sha256']
 for r in changes:
  dst=ROOT/r['file'];assert sha(dst)==r['before_sha256'];shutil.copy2(OUT/'Files'/r['file'],dst)
  assert sha(dst)==r['sha256'];print('BIND_NORMALS_INSTALLED',r['file'],flush=True)
  by_file[r['file']]={'file':r['file'],'sha256':r['sha256'],'revision_manifest':'Resources/Models/FinalRefinement/BindNormalsDelivery/published.json'}
 result={'passed':True,'fbx_changed':len(rows),'sidecars_updated':len(sidecars),'archive':str(ARCHIVE),'files':changes,'limitations':'Cloth physics remains experimental; root-wrapper mapping unchanged. No recorded capture tested.'}
 (OUT/'published.json').write_text(json.dumps(result,indent=2))
 pending=CURRENT.with_suffix('.pending.json');pending.write_text(json.dumps({'passed':True,'files':list(by_file.values())},indent=2));pending.replace(CURRENT)
 (OUT/'installation_complete.txt').write_text(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
 print('BIND_NORMALS_INSTALL_COMPLETE',len(rows),len(sidecars),flush=True)
if __name__=='__main__': main()
