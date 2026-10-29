from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]/'Resources/Models/FinalRefinement/BodyPhysics'
rows=[]
for p in root.glob('*/validation.json'):
 report=json.loads(p.read_text());ratios={}
 for name in ['Belt_Tail_Left','Belt_Tail_Right']:
  values={x['frame']:x['height_m'] for x in report['measurements'] if x['object']==name}
  ratios[name]=values[144]/values[1]
 row={'preset':p.parent.name,'finite':report['finite'],'rig_preserved':report['rig_preserved'],'settled_height_ratios':ratios,'collapse_screen_passed':min(ratios.values())>=.5}
 rows.append(row);print(p.parent.name,{k:round(v,3) for k,v in ratios.items()})
(root/'numeric_review.json').write_text(json.dumps({'presets':rows,'note':'Height ratios screen for gross settling collapse; they do not establish collision-free contact or visual quality.'},indent=2))
