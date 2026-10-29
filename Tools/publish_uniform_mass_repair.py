"""Install validated mass-only native repairs, with complete rollback copies."""
from pathlib import Path
import json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/FinalRefinement/UniformMassDelivery'
CURRENT=OUT.parent/'current_assets.json';ARCHIVE=ROOT/'Resources/Models/Archive/Before_Uniform_Mass_20261026'
def read(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8388608),b''):h.update(block)
    return h.hexdigest()
assert not (OUT/'published.json').exists() and not ARCHIVE.exists()
baseline=read(CURRENT);by_file={r['file']:dict(r) for r in baseline['files']}
native={r['file'] for r in baseline['files'] if r['file'].endswith('.blend')}
rows=[read(p) for p in OUT.glob('*.json') if re.fullmatch('[0-9a-f]{16}',p.stem)]
assert {r['file'] for r in rows}==native
checks=[read(OUT/('reopen_validation_'+str(i)+'.json')) for i in [0,1]]
assert all(c['passed'] for c in checks)
assert {r['file'] for c in checks for r in c['files']}==native
physical=read(OUT.parent/'MassVerifiedBeltPresets/Medium/validation.json')
assert physical['frames']==288 and physical['rig_actions_preserved'] and physical['original_belt_geometry_preserved']
changed=[r for r in rows if r['changes']]
for r in rows:
    assert sha(ROOT/r['file'])==r['before_sha256']==by_file[r['file']]['sha256'],r['file']
    assert r['geometry_shape_keys_rigs_actions_preserved']
    if r['changes']:assert sha(OUT/'Files'/r['file'])==r['sha256'],r['file']
new_hashes={r['file']:r['sha256'] for r in changed};sidecars=[]
for rel,row in by_file.items():
    if 'MotionBuilder' not in rel or not rel.endswith('.json'):continue
    data=read(ROOT/rel);source=data.get('source')
    if not isinstance(source,str):continue
    path=Path(source);path=path if path.is_absolute() else ROOT/path
    try:source_rel=path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:continue
    if source_rel not in new_hashes or 'source_sha256' not in data:continue
    assert sha(ROOT/rel)==row['sha256']
    data['source_sha256_before_uniform_mass']=data['source_sha256'];data['source_sha256']=new_hashes[source_rel]
    data['uniform_mass_revision']='2026-10-26'
    data['uniform_mass_note']='Native cloth settings only; source mesh/shape-key coordinates, rigs and actions preserved. FBX unchanged.'
    staged=OUT/'Files'/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_text(json.dumps(data,indent=2))
    sidecars.append({'file':rel,'before_sha256':row['sha256'],'sha256':sha(staged),'source_metadata_only':True})
changes=changed+sidecars
required=sum((ROOT/r['file']).stat().st_size for r in changes)
assert shutil.disk_usage(ROOT).free>required+1024**3,'Insufficient room for complete rollback archive'
ARCHIVE.mkdir(parents=True);shutil.copy2(CURRENT,ARCHIVE/'current_assets_before.json')
for row in changes:
    src=ROOT/row['file'];dst=ARCHIVE/row['file'];dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst);assert sha(dst)==row['before_sha256']
for row in changes:
    target=ROOT/row['file'];assert sha(target)==row['before_sha256']
    shutil.copy2(OUT/'Files'/row['file'],target);assert sha(target)==row['sha256']
    by_file[row['file']]={'file':row['file'],'sha256':row['sha256'],'revision_manifest':'Resources/Models/FinalRefinement/UniformMassDelivery/published.json'}
    print('MASS_INSTALLED',row['file'],flush=True)
result={'passed':True,'native_files_changed':len(changed),'native_files_checked':len(rows),'validation_sidecars_updated':len(sidecars),'archive':str(ARCHIVE),'files':changes,
        'limitations':'Mass configuration only. Belt-contact and unrestricted cloth-motion studies remain experimental. No FBX or Unreal physics change.'}
(OUT/'published.json').write_text(json.dumps(result,indent=2))
pending=CURRENT.with_suffix('.pending.json');pending.write_text(json.dumps({'passed':True,'files':list(by_file.values())},indent=2));pending.replace(CURRENT)
(OUT/'installation_complete.txt').write_text(f"{len(changed)} native files and {len(sidecars)} sidecars updated. Originals archived. See published.json.\n")
print('UNIFORM_MASS_INSTALL_COMPLETE',len(changed),len(sidecars),flush=True)
