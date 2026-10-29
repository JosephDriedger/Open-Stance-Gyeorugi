import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
from repair_protector_binding import repair
out=a.ROOT/'Resources/Models/FinalRefinement/ProtectorBindingMotion';out.mkdir(exist_ok=True);rows=[]
for kind in a.build.PRESETS:
 s,r,scale,source=a.load(kind,'Gameplay_High');repair(s);s.cycles.samples=12
 for design,pose in [(0,'Cross_Body'),(1,'Knee_L')]:
  a.select(r,design,design,design);a.audit.pose(r,pose,scale)
  label=kind+'_'+pose
  a.render(s,r,scale,out,label,(1.7,-4,1.65),(0,0,1.15),1.05,600,600)
  rows.append(label)
 a.audit.pose(r,'Neutral',scale)
 a.render(s,r,scale,out,kind+'_Rear',(1.7,4,1.65),(0,0,1.15),1.05,600,600);rows.append(kind+'_Rear')
(out/'validation.json').write_text(json.dumps({'renders':rows,'physics':False,'source_saved':False},indent=2))
