import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
from repair_protector_binding import repair
out=a.ROOT/'Resources/Models/FinalRefinement/ProtectorBindingReview';out.mkdir(exist_ok=True)
rows=[]
for kind in a.build.PRESETS:
 s,r,scale,src=a.load(kind,'Gameplay_High');changes=repair(s);assert len(changes)==8,(kind,changes)
 s.cycles.samples=12;r['Wear_Protector']=True;r['Wear_Helmet']=True
 for design in [0,1]:
  r['ProtectorDesign']=design;a.build.refresh(r)
  a.render(s,r,scale,out,kind+'_'+str(design),(.2,-4,1.3),(0,0,1.15),.9,600,600)
 rows.append({'preset':kind,'changed':changes})
(out/'validation.json').write_text(json.dumps(rows,indent=2))
