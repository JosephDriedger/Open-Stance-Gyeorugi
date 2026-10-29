"""Publish the verified follow-up, retaining prior assets and checking for intervening edits."""
from pathlib import Path
p=Path(__file__).with_name('publish_tailored_doboks.py')
s=p.read_text().replace('TailoredDoboks','FollowupFix').replace('Before_Tailored_Doboks_20261015_','Before_Followup_Fix_20261022_').replace('dobok_fit_revision','followup_fix_revision').replace('2026-10-15','2026-10-22')
s=s.replace('Tailored dobok fit, 2026-10-22: both uniform styles now have less torso, sleeve and trouser bulk, with original body shapes and rigs retained. Current files, animations and characterized targets use the updated fit.','Model follow-up, 2026-10-22: single-leg garment corrections, chest-guard shape/weights, helmet taper and crowd scalp clearance updated across the library. Original bodies, rigs and authored animation keyframes retained. Full free uniform physics remains experimental.')
s=s.replace("native=check(S/'delivery_validation.json',63)","assert read(S/'visual_review.json')['passed_for_targeted_repairs']\nnative=check(S/'delivery_validation.json',63)")
extra="""
for kind in KINDS:
 report=read(S/kind/'Tpose_validation.json');src=S/kind/report['file'];assert report['passed'] and sha(src)==report['sha256'];add(src,M/'TPose'/src.name)
for level,destination in [('Gear',M/'ProtectorReferenceV2/Chest_Protector_Library.blend'),('Physics',M/'Animation/Physics/LiveCloth_Pilot.blend')]:
 report=read(S/'Medium'/(level+'_validation.json'));src=S/'Medium'/report['file'];assert report['passed'] and sha(src)==report['sha256'];add(src,destination)
for row in check(S/'exports_validation.json',18)['files']:
 src=S/row['file'];add(src,M/'CharacterSuite'/src.parent.name/'HairstyleSamples'/src.name)
previous=read(M/'CollarEarRepair/published.json')
old={row['file'].replace('\\\\','/'):row['sha256'] for row in previous['files']}
for _,dest in mapping:
 rel=dest.relative_to(ROOT).as_posix()
 if dest.exists() and rel in old:assert sha(dest)==old[rel],('Intervening edit; preserve before publication',rel)
"""
s=s.replace("archive=M/'Archive'",extra+"\narchive=M/'Archive'")
s=s.replace("for _,p in mapping:backup(p)","print('Backing up '+str(len(mapping))+' assets',flush=True)\nfor _,p in mapping:backup(p)")
s=s.replace("records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})","records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})\n if len(records)%100==0:print('Installed '+str(len(records)),flush=True)")
s=s.replace("for folder in ['ROMRepair','GarmentRollout','AlternateJacketRepair']:","for folder in []:")
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
