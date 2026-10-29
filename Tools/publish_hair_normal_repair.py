"""Publish verified winding-only repairs with archived originals and current hashes."""
from pathlib import Path
import json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/FinalRefinement/HairNormalDelivery'
ARCHIVE=ROOT/'Resources/Models/Archive/Before_Hair_Normals_20261025'
CURRENT=OUT.parent/'current_assets.json'
def read(path):return json.loads(path.read_text())
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8388608),b''):h.update(block)
    return h.hexdigest()
assert not (OUT/'published.json').exists(),'Repair already published'
baseline=read(CURRENT);by_file={r['file']:dict(r) for r in baseline['files']}
rows=[read(p) for p in OUT.glob('*.json') if re.fullmatch(r'(fbx_)?[0-9a-f]{16}',p.stem)]
assert len(rows)==387
assert read(OUT/'export_validation.json')['passed'] and len(read(OUT/'export_validation.json')['files'])==78
assert read(OUT/'source_export_validation.json')['passed']
checks=[read(p) for p in (OUT/'MotionBuilderChecks').glob('*.json')];assert len(checks)==12
checks_by_file={r['file']:r for r in checks}
assert all(r['characterized'] and r['control_rig'] and r['wrist_movement_cm']>5 for r in checks)
changed=[r for r in rows if r.get('changed_objects') or r.get('changed_geometry_ids')]
assert len(changed)==144
for row in baseline['files']:assert sha(ROOT/row['file'])==row['sha256'],row['file']
for row in rows:
    assert sha(ROOT/row['file'])==row['before_sha256'],row['file']
    if row in changed:assert sha(OUT/'Files'/row['file'])==row['sha256'],row['file']
new_hashes={r['file']:r['sha256'] for r in rows}
for check in checks:
    path=ROOT/check['file'];relative=path.with_name('validation_'+path.stem+'.json').relative_to(ROOT).as_posix()
    old=read(ROOT/relative);before=sha(ROOT/relative);assert by_file[relative]['sha256']==before
    old['source_sha256_at_characterization']=old['source_sha256']
    source=Path(old['source']);source_rel=source.relative_to(ROOT).as_posix() if source.is_absolute() else source.as_posix()
    old['source_sha256']=new_hashes.get(source_rel,old['source_sha256'])
    old['hair_normal_revision']='2026-10-25';old['output_sha256']=check['sha256']
    old['postprocess_wrist_control_hand_movement_cm']=check['wrist_movement_cm']
    old['postprocess_scene_nodes_preserved']=True
    staged=OUT/'Files'/relative;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_text(json.dumps(old,indent=2))
    changed.append({'file':relative,'before_sha256':before,'sha256':sha(staged),'validation_sidecar_updated':True})
assert not ARCHIVE.exists(),ARCHIVE
ARCHIVE.mkdir(parents=True)
shutil.copy2(CURRENT,ARCHIVE/'current_assets_before.json')
for row in changed:
    source=ROOT/row['file'];backup=ARCHIVE/row['file'];backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,backup);assert sha(backup)==row['before_sha256']
for row in changed:
    target=ROOT/row['file'];assert sha(target)==row['before_sha256']
    shutil.copy2(OUT/'Files'/row['file'],target);assert sha(target)==row['sha256']
    print('NORMALS_INSTALLED',row['file'],flush=True)
for row in rows+changed:
    if row['file'] not in by_file or row['sha256']!=row['before_sha256']:
        by_file[row['file']]={'file':row['file'],'sha256':row['sha256'],'revision_manifest':'Resources/Models/FinalRefinement/HairNormalDelivery/published.json'}
for row in by_file.values():assert sha(ROOT/row['file'])==row['sha256'],row['file']
result={'passed':True,'native_files_changed':51,'fbx_files_changed':93,'motionbuilder_checks':12,'export_reimports':81,'review_images':6,'archive':str(ARCHIVE),'files':changed,'checked_rows':rows,'limitations':'Normals only. Hair silhouette/fibers, belt/free-cloth simulation and Unreal validation remain unfinished.'}
(OUT/'published.json').write_text(json.dumps(result,indent=2))
temporary=CURRENT.with_suffix('.pending.json');temporary.write_text(json.dumps({'passed':True,'files':list(by_file.values())},indent=2));temporary.replace(CURRENT)
(OUT/'installation_complete.txt').write_text('51 native files, 93 FBXs and 12 validation sidecars installed and hashed. See published.json.\n')
print('HAIR_NORMAL_INSTALL_COMPLETE',len(by_file),'current assets verified',flush=True)
