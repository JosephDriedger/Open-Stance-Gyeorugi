"""Install only the completed, validated mesh/UV repair; archive every replaced file first."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/FinalRefinement/UniformGeometryDelivery'
CURRENT=OUT.parent/'current_assets.json';ARCHIVE=ROOT/'Resources/Models/Archive/Before_Uniform_Geometry_20261029'
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert not (OUT/'published.json').exists() and not ARCHIVE.exists()
baseline=read(CURRENT);by_file={r['file']:r for r in baseline['files']}
native=[read(p) for p in OUT.glob('native_*.json')];exports=[read(p) for p in OUT.glob('fbx_*.json')]
assert len(native)==102
assert {r['file'] for r in exports}==set(read(OUT/'export_inputs.json'))
assert all(not r['changes'] or r.get('reopened_preservation_passed') for r in native)
assert all(r['non_geometry_nodes_preserved'] for r in exports)
validation=read(OUT/'reimport_validation.json');assert validation['passed'] and len(validation['files'])==9
controls=[read(p) for p in (OUT/'MotionBuilderChecks').glob('*.json')];assert len(controls)==12
for c in controls:
 assert c['characterized'] and c['control_rig'] and c['wrist_movement_cm']>5
 assert c['sha256']==sha(OUT/'Files'/c['file']),c['file']
engine=read(OUT/'unreal_import.json')
assert len(engine)==4 and all('error' not in r and r['chain_parents_ok'] and r['bones']==358 for r in engine)
assert 'DONE 4 targets' in (OUT/'unreal_import.txt').read_text()
assert (OUT/'visual_review.json').exists() and read(OUT/'visual_review.json')['reviewed']
rows=native+exports;changes=[r for r in rows if r['changes']]
for r in rows:
 assert sha(ROOT/r['file'])==r['before_sha256'],r['file']
 if r['changes']:assert sha(OUT/'Files'/r['file'])==r['sha256'],r['file']
hashes={r['file']:r['sha256'] for r in changes};sidecar_paths={ROOT/p for p in by_file if p.endswith('.json') and 'MotionBuilder' in p}
for folder in ('MotionBuilder','MotionBuilder_BeltChain'):
 sidecar_paths.update((ROOT/'Resources/Models/Animation'/folder).rglob('validation_*.json'))
sidecars=[]
for p in sorted(sidecar_paths):
 data=read(p);source=data.get('source');source_rel=None
 if source:
  try:source_rel=(ROOT/source).resolve().relative_to(ROOT).as_posix()
  except ValueError:pass
 target=p.with_name(p.stem.removeprefix('validation_')+'.fbx');target_rel=target.relative_to(ROOT).as_posix()
 if source_rel not in hashes and target_rel not in hashes:continue
 if source_rel in hashes:
  data['source_sha256_before_uniform_geometry']=data.get('source_sha256');data['source_sha256']=hashes[source_rel]
 if target_rel in hashes:data['uniform_geometry_target_sha256']=hashes[target_rel]
 data['uniform_geometry_revision']='2026-10-29'
 data['uniform_geometry_note']='Mesh-only repair; FBX controls, skinning, takes and non-geometry nodes preserved. No captured take applied.'
 rel=p.relative_to(ROOT).as_posix();dst=OUT/'Files'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(data,indent=2))
 sidecars.append({'file':rel,'before_sha256':sha(p),'sha256':sha(dst),'source_metadata_only':True})
changes+=sidecars
assert shutil.disk_usage(ROOT).free>sum((ROOT/r['file']).stat().st_size for r in changes)+1024**3
ARCHIVE.mkdir(parents=True);shutil.copy2(CURRENT,ARCHIVE/'current_assets_before.json')
for r in changes:
 dst=ARCHIVE/r['file'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/r['file'],dst)
 assert sha(dst)==r['before_sha256']
for r in changes:
 dst=ROOT/r['file'];assert sha(dst)==r['before_sha256'];shutil.copy2(OUT/'Files'/r['file'],dst)
 assert sha(dst)==r['sha256'];print('UNIFORM_GEOMETRY_INSTALLED',r['file'],flush=True)
for r in rows+sidecars:
 by_file[r['file']]={'file':r['file'],'sha256':r['sha256'],'revision_manifest':'Resources/Models/FinalRefinement/UniformGeometryDelivery/published.json'}
result={'passed':True,'native_changed':sum(bool(r['changes']) for r in native),'fbx_changed':sum(bool(r['changes']) for r in exports),
 'fbx_checked':len(exports),'sidecars_updated':len(sidecars),'archive':str(ARCHIVE),'files':changes,
 'limitations':'UV and zero-area body-face repair. Root wrapper differences, bind-pose/shading warnings and unfinished cloth physics remain separate.'}
(OUT/'published.json').write_text(json.dumps(result,indent=2))
pending=CURRENT.with_suffix('.pending.json');pending.write_text(json.dumps({'passed':True,'files':list(by_file.values())},indent=2));pending.replace(CURRENT)
(OUT/'installation_complete.txt').write_text(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
print('UNIFORM_GEOMETRY_INSTALL_COMPLETE',result['native_changed'],result['fbx_changed'],len(sidecars),flush=True)
