"""Validate review coverage and publish the inspected gallery and findings."""
from pathlib import Path
import json
from html import escape

root=Path(__file__).resolve().parents[1]/'Resources/Models/SparringStyleReview_20261016'
kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
suffixes=['Front','Rear','Motion','Helmet0_Hair','Helmet1_Hair','Helmet2_Hair','LOD']
for kind in kinds:
    for mode,count in [('body',22),('hair',27),('lod',2)]:
        d=root/kind/mode
        m=json.loads((d/'manifest.json').read_text())
        assert len(m['renders'])==count and not m['source_files_saved']
        assert all((d/name).is_file() for name in m['renders'])
    assert all((root/f'{kind}_{s}.jpg').is_file() for s in suffixes)
assert not list(root.glob('*error.log'))
findings=[
 {'id':'FIT-01','status':'confirmed','priority':'high','title':'Jacket penetrates lower protector',
  'scope':'Confirmed Female_Athletic / Gameplay_High / wrap jacket / quilted protector; similar lower-edge irregularities in other overview images need per-preset clearance measurement.',
  'evidence':['Female_Athletic/body/J0_H0_P0_Front.png','diagnostics/Female_Athletic_Flat.png'],
  'detail':'Green jacket surfaces interrupt the blue protector along both lower side transitions in the emission-material diagnostic. This is geometry overlap, not a highlight. Fit the shell and its binding together around the dressed torso; preserve belt overlap. Recheck both protector designs, both jackets and movement poses.'},
 {'id':'FIT-02','status':'confirmed','priority':'high','title':'Skin visible through shoulder region',
  'scope':'Tall / Preview / wrap jacket, visible with all three helmet designs in head closeups.',
  'evidence':['Tall/hair/H1_Hair1_Front.png','diagnostics/Tall_Shoulder.png'],
  'detail':'A skin-colored opening remains between the green jacket and blue protector shoulder in the diagnostic. Determine whether the cause is neckline topology or insufficient clearance before repairing. Do not mask away the forearm/ankle skin and reintroduce disconnected limbs.'},
 {'id':'ART-01','status':'visual_quality_concern','priority':'medium','title':'Helmet rear silhouette remains too cylindrical',
  'scope':'Shared helmet designs across the nine presets.',
  'evidence':['Medium/hair/H0_Hair3_Rear.png','Male_Athletic/hair/H1_Hair3_Rear.png'],
  'detail':'Tall, nearly vertical rear walls and abrupt crown transitions read as a rigid bucket rather than fitted foam padding. This is an art-quality judgment, not a proven mesh intersection. Shape and surface finish need refinement against the supplied references.'},
 {'id':'ART-02','status':'visual_quality_concern','priority':'medium','title':'Helmet-fit hair loses natural coverage and texture',
  'scope':'Open-crown helmet especially; side part and long styles visible in the closeup sheets.',
  'evidence':['Tall/hair/H1_Hair1_Front.png','Male_Athletic/hair/H1_Hair3_Rear.png','Medium_Helmet1_Hair.jpg'],
  'detail':'Some fitted styles reveal a broad bare-looking scalp area; other styles form smooth cap-like surfaces or sharp strips. Visibility and HelmetFit assertions pass, but those checks do not establish realistic hair coverage. Inspect fit-shape positions and hair alpha at higher quality before approving.'}
]
result={'completed':'2026-10-18','status':'issues_found_not_visually_approved','presets':kinds,'audit_renders':459,'contact_sheets_reviewed':63,'additional_flat_color_diagnostics':3,'model_files_modified':False,'findings':findings,
 'limits':['Static pose audit, not continuous animation collision proof.','Live cloth off; skinning and pose correctives only.','No new FBX/Unreal/mocap playback validation.','Not every hair, gear, pose and LOD cross-product rendered.','Crowd and gear-free models not covered by this sparring pass.','8-sample denoised renders can conceal fine surface defects.']}
(root/'review_result.json').write_text(json.dumps(result,indent=2))
lines=['# Sparring style visual review','', 'Completed 18 October 2026. **Issues found; library not visually approved.**', '',
 'Reviewed 459 renders through all 63 contact sheets, plus original images for suspect details and three flat-color diagnostic renders. Nine presets, two jackets, three helmets, two chest protectors and six hairstyles were sampled. Source models were not saved or changed.', '',
 '## Confirmed defects and quality concerns','']
for f in findings:
    lines += [f"### {f['id']}: {f['title']}",'',f"**{f['status']} — {f['priority']} priority.** {f['scope']}",'',f['detail'],'']
    lines += ['Evidence: '+', '.join(f'[{p}]({p})' for p in f['evidence']), '']
lines += ['## Checks that completed','',
 '- All 27 manifests contain the expected render counts; all referenced images exist; no worker error logs.',
 '- Gear selection assertions passed: selected helmet/protector visible and alternatives hidden.',
 '- All selected hair objects were visible with HelmetFit = 1.',
 '- No gross detached hands/feet or exploded meshes seen in the sampled overview poses. This does not rule out small penetrations.',
 '- Rear lace and buckle variants are present; ponytail and bun remain visible below the rear helmet edge.',
 '- Mid/Far sampled silhouettes remain recognizable. Fine texture quality is not established by these images.','',
 '## Coverage and limits','',
 '| Mode | Per preset | Total | Coverage |','|---|---:|---:|---|',
 '| Gameplay High | 22 | 198 | 12 front combinations, 6 rear wrap-jacket views, 4 movement poses |',
 '| Preview hair | 27 | 243 | 3 helmets × 6 hairstyles front; 3 longer styles rear |',
 '| Gameplay Mid/Far | 2 | 18 | One cross-body pose and selected gear per level |','',
 'Movement samples: arms overhead, cross-body, left knee raise and deep squat. Colors alternate red/blue rather than testing every color combination. Four sampled poses are not a full range-of-motion or animation sweep. Rear V-neck combinations, all hairstyle/gear/pose cross-products, crowd, gear-free styles and runtime exports are outside this pass.','',
 '**Physics remains unapproved for unrestricted uniform movement.** Live cloth was OFF for this audit. The earlier hybrid demo keeps the reviewed uniform deformation and simulates belt tails; it is not evidence of fully reactive uniform cloth. Appearance materials alone do not provide garment collision or bending simulation.','',
 'The tiny calf mark noted during initial review remains unresolved at this render resolution and is not counted as a confirmed defect.','',
 '## Gallery','', '[Open all comparison sheets](gallery.html)','']
for k in kinds:
    lines += [f"- {k}: "+' · '.join(f'[{s}]({k}_{s}.jpg)' for s in suffixes)]
(root/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
html=['<!doctype html><meta charset="utf-8"><title>Sparring style review</title><style>body{background:#20242b;color:#eee;font:16px system-ui;margin:2rem} img{max-width:100%;height:auto} details{margin:1rem 0}a{color:#91c8ff}</style><h1>Sparring style review</h1><p>459 audit renders. Issues found; not visually approved. Completed 18 October 2026.</p><p><a href="REPORT.md">Report</a></p>']
for k in kinds:
    html += [f'<details><summary>{escape(k)}</summary>']
    for s in suffixes:html += [f'<h3>{s}</h3><a href="{k}_{s}.jpg"><img loading="lazy" src="{k}_{s}.jpg" alt="{k} {s}"></a>']
    html += ['</details>']
(root/'gallery.html').write_text('\n'.join(html),encoding='utf-8')
print('Validated 459 audit renders, 27 manifests and 63 sheets; report and gallery written.')
