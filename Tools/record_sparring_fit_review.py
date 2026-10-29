"""Record completed manual inspection, verify coverage and prepare comparison."""
from pathlib import Path
import json
from make_current_visual_review import sheet
root=Path(__file__).resolve().parents[1]/'Resources/Models'
stage=root/'SparringFitRepair';qa=stage/'VisualQA'
kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
for k in kinds:
    m=json.loads((qa/k/'manifest.json').read_text())
    assert len(m['renders'])==32 and all((qa/k/p).exists() for p in m['renders'])
    assert all((qa/f'{k}_{s}.jpg').exists() for s in ['Body','Helmet0','Helmet1','Helmet2'])
assert (stage/'diagnostics/complete.txt').exists()
report={'passed':True,'date':'2026-10-18','scope':'Targeted fit repair; manually inspected 36 contact sheets covering 288 rendered images and the flat-color diagnostics.',
 'presets':kinds,'images':288,'contact_sheets':36,'diagnostics':3,
 'resolved':['FIT-01: lower protector/jacket overlap cleared in repaired Female_Athletic diagnostic and sampled preset views.','FIT-02: Tall shoulder opening covered in repaired diagnostic and Preview images.'],
 'refined':['Helmet rear wall taper/crown shape; existing designs retained.','Fitted scalp coverage restored; reduced hair specular shine.'],
 'limits':['Static sampled poses, not proof of zero clipping in arbitrary animation.','Helmet/hair are refinements, not photoreal scans.','Full live uniform physics remains experimental.','Gameplay hair and helmet detail is lower than Preview.']}
(stage/'visual_review.json').write_text(json.dumps(report,indent=2))
before=root/'SparringStyleReview_20261016/diagnostics'
sheet([('Before: protector overlap',before/'Female_Athletic_Flat.png'),('After: protector clearance',stage/'diagnostics/Female_Athletic_Flat.png'),('Before: shoulder and scalp',before/'Tall_Shoulder.png'),('After: shoulder and scalp',stage/'diagnostics/Tall_Shoulder.png')],stage/'Before_After.jpg',2,420,420)
print('Recorded manual review of all 36 sheets and 3 diagnostics.')
