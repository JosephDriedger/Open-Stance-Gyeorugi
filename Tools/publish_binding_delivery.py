"""Install hash-checked staging files with recoverable originals."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/FinalRefinement/BindingDelivery'
archive=ROOT/'Resources/Models/Archive/Before_Binding_Clearance_20261024'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old={x['file']:x for x in json.loads((ROOT/'Resources/Models/HairExportFinish/published.json').read_text())['files']}
rows=[]
for p in OUT.glob('*.json'):
 data=json.loads(p.read_text())
 if 'changed' in data:rows.append(data)
assert len(rows)==93,len(rows)
assert len([r for r in rows if r['changed']])==75
assert len(next(r for r in rows if 'Workspace.blend' in r['file'])['changed'])==72
for p in OUT.glob('*_exports.json'):rows+=json.loads(p.read_text())['files']
assert len(rows)==153,len(rows)
reports=list((OUT/'Files/Resources/Models/Animation/MotionBuilder').rglob('validation_*.json'));assert len(reports)==18,len(reports)
for p in reports:
 report=json.loads(p.read_text());assert report['characterized'] and report['control_rig'] and report['reopened_successfully']
 assert sha(ROOT/report['source'])==report['source_sha256']
 staged=Path(report['output']);rel=staged.relative_to(OUT/'Files').as_posix()
 rows.append({'file':rel,'before_sha256':old[rel]['sha256'],'sha256':sha(staged),'characterized':True,'control_rig':True,'reopened_successfully':True})
 # Keep the canonical validation sidecar accurate after moving out of staging.
 rel_report=p.relative_to(OUT/'Files');original=ROOT/rel_report
 report['source']=str(Path(report['source']).relative_to(OUT.relative_to(ROOT)/'Files')).replace('\\','/')
 report['output']=str(ROOT/rel);report['binding_revision']='2026-10-23'
 before=sha(original) if original.exists() else None
 p.write_text(json.dumps(report,indent=2))
 rows.append({'file':rel_report.as_posix(),'before_sha256':before,'sha256':sha(p),'validation_sidecar':True})
assert (OUT/'ExportReview/complete.txt').exists()
assert len(json.loads((OUT.parent/'ProtectorBindingMotion/validation.json').read_text())['renders'])==27
assert len(json.loads((OUT.parent/'ProtectorBindingReview/validation.json').read_text()))==9
# Preflight the entire transaction before changing any canonical asset.
for r in rows:
 target=ROOT/r['file'];staged=OUT/'Files'/r['file']
 assert (sha(target) if target.exists() else None)==r['before_sha256'],('Canonical asset changed',target)
 if r.get('changed')==[]:continue
 assert sha(staged)==r['sha256'],staged
installed=[]
for r in rows:
 target=ROOT/r['file']
 if r.get('changed')!=[]:
  backup=archive/r['file'];backup.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():
   assert not backup.exists(),backup
   shutil.copy2(target,backup);assert sha(backup)==r['before_sha256']
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/'Files'/r['file'],target)
 assert sha(target)==r['sha256'];installed.append(r)
 (OUT/'installation_progress.json').write_text(json.dumps(installed,indent=2))
(OUT/'published.json').write_text(json.dumps({'passed':True,'files':installed,'archive':str(archive),'native_checked':93,'native_changed':75,'fbx_changed':78,'motionbuilder_targets':18,'validation_sidecars':18,'visual_scope':'18 neutral, 27 pose/rear, 6 independently imported FBX images','physics_changes_installed':False},indent=2))
print('BINDING_DELIVERY_COMPLETE',len(installed))
