"""Reuse the checked library publisher with opening-repair inputs and notices."""
from pathlib import Path
p=Path(__file__).with_name('publish_tailored_doboks.py')
s=p.read_text()
s=s.replace("S=M/'TailoredDoboks'","S=M/'OpeningRepair'")
s=s.replace("native=check(S/'delivery_validation.json',63)","assert len(read(S/'closeup_validation.json')['rendered'])==24\nassert read(S/'visual_review.json')['passed']\nnative=check(S/'delivery_validation.json',63)")
s=s.replace('Before_Tailored_Doboks_','Before_Garment_Openings_')
s=s.replace('dobok_fit_revision','garment_opening_revision')
s=s.replace('../TailoredDoboks/README.md','../OpeningRepair/README.md')
s=s.replace('Resources/Models/TailoredDoboks/README.md','Resources/Models/OpeningRepair/README.md')
s=s.replace('Tailored dobok fit, 2026-10-15: both uniform styles now have less torso, sleeve and trouser bulk, with original body shapes and rigs retained. Current files, animations and characterized targets use the updated fit.',
 'Wrist and ankle repair, 2026-10-15: skin now extends inside sleeve and trouser openings. Both uniform styles, animations and characterized targets use the repaired coverage masks.')
s=s.replace('[TailoredDoboks](../OpeningRepair/README.md) is the current slimmer-fit revision.', '[OpeningRepair](../OpeningRepair/README.md) is the current wrist and ankle coverage revision.')
s=s.replace("for folder in ['ROMRepair','GarmentRollout','AlternateJacketRepair']:","for folder in ['ROMRepair','GarmentRollout','AlternateJacketRepair','TailoredDoboks']:")
s=s.replace("archive=M/'Archive'", "for kind in KINDS:\n r=read(S/kind/'Tpose_validation.json');src=S/kind/r['file'];assert r['passed'] and sha(src)==r['sha256'];add(src,M/'TPose'/src.name)\narchive=M/'Archive'")
s=s.replace("(S/'published.json').write_text", "p=M/'TPose/README.md';write(p,p.read_text().replace('The cuff and ankle opening defects remain in these copies. They are not corrected by changing the pose.','Wrist and ankle coverage masks have been repaired in these copies; see ../OpeningRepair/README.md.'))\n(S/'published.json').write_text")
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
