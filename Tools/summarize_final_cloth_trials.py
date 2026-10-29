from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]/'Resources/Models/FinalRefinement'
reports=[]
for name in ['ClothFinal_0','ClothFinal_1','ClothStiffBelt_0','ClothCleanContact_0','ClothSettle_0']:
 p=root/name/'measurements.json';data=json.loads(p.read_text());rows=data['rows']
 summary={n:round(max(r['max_m'] for r in rows if r['object']==n),6) for n in sorted({r['object'] for r in rows})}
 reports.append({'trial':name,'frames':len({r['frame'] for r in rows}),'finite':data['finite'],'maximum_displacement_from_skinning_m':summary,'approved_for_production':False})
(root/'physics_trials.json').write_text(json.dumps({'trials':reports,'visual_findings':'Belt folding remains too sharp. Settling improves but does not establish robust cloth/contact across body types. The 144-frame variant is delivered only as an experimental study.','native_default_physics_changed':False},indent=2))
print('Recorded '+str(len(reports))+' physics trial reports.')
