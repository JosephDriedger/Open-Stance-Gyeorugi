"""Install only the validated, reviewed sparring-fit delivery, keeping backups."""
from pathlib import Path
p=Path(__file__).with_name('publish_tailored_doboks.py');s=p.read_text()
s=s.replace('TailoredDoboks','SparringFitRepair').replace('Before_Tailored_Doboks_20261015_','Before_Sparring_Fit_20261018_').replace('dobok_fit_revision','sparring_fit_revision').replace('2026-10-15','2026-10-18')
s=s.replace('Tailored dobok fit, 2026-10-18: both uniform styles now have less torso, sleeve and trouser bulk, with original body shapes and rigs retained. Current files, animations and characterized targets use the updated fit.','Sparring fit repairs, 2026-10-18: shoulder coverage, lower protector clearance, helmet rear taper and fitted scalp coverage updated. Original bodies, rigs and authored animations retained.')
s=s.replace('is the current slimmer-fit revision.','is the current sparring-fit revision.')
s=s.replace("for folder in ['ROMRepair','GarmentRollout','AlternateJacketRepair']:","for folder in ['VisualFitRepair']:")
s=s.replace("native=check(S/'delivery_validation.json',63)","assert read(S/'visual_review.json')['passed']\nassert read(S/'cloth_pilot.json')['completed']\nassert sha(S/'LiveCloth_Pilot.blend')==read(S/'cloth_pilot.json')['sha256']\nnative=check(S/'delivery_validation.json',63)")
s=s.replace("archive=M/'Archive'", "for kind in KINDS:\n r=read(S/kind/'Tpose_validation.json');src=S/kind/r['file'];assert r['passed'] and sha(src)==r['sha256'];add(src,M/'TPose'/src.name)\nadd(S/'LiveCloth_Pilot.blend',M/'Animation/Physics/LiveCloth_Pilot.blend')\ngear=read(S/'Gear/validation.json');assert gear['passed'] and sha(S/'Gear'/gear['file'])==gear['sha256']\nadd(S/'Gear'/gear['file'],M/'ProtectorReferenceV2'/gear['file'])\narchive=M/'Archive'")
s=s.replace('for _,p in mapping:backup(p)',"print('Backing up '+str(len(mapping))+' assets',flush=True)\nfor i,(_,p) in enumerate(mapping,1):\n backup(p)\n if i%100==0:print('Backup '+str(i),flush=True)")
s=s.replace("records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})","records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})\n if len(records)%100==0:print('Installed '+str(len(records)),flush=True)")
s+="\np=M/'SparringStyleReview_20261016/REPORT.md'\nwrite(p,'> Follow-up: [SparringFitRepair](../SparringFitRepair/README.md) contains the installed repairs. Findings below describe the preceding models.\\n\\n'+p.read_text(encoding='utf-8'))\n"
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
