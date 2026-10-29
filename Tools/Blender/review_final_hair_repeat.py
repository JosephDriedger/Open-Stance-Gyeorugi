import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
from refine_final_hair import seam
out=a.ROOT/'Resources/Models/FinalRefinement/HairRepeat/Review';out.mkdir(parents=True,exist_ok=True)
rows=[]
for kind in a.build.PRESETS:
 s,r,scale,source=a.load(kind,'Gameplay_High');seam(s);s.cycles.samples=12
 for style in range(6):
  for helmet in [False,True]:
   r['HairStyle']=style;r['Wear_Helmet']=helmet;r['HelmetDesign']=style%3;a.build.refresh(r)
   pos=(.5,1,1.84) if style>=3 else (.4,-1,1.85)
   label=kind+'_'+str(style)+'_'+str(int(helmet))
   a.render(s,r,scale,out,label,pos,(0,0,1.64),.54,400,450)
   active=[o for o in s.objects if o.type=='MESH' and o.name.startswith('Hair_'+a.build.hair.STYLES[style]+'__')]
   assert active and all(not o.hide_render for o in active)
   for o in active:
    if o.data.shape_keys:assert abs(o.data.shape_keys.key_blocks['HelmetFit'].value-int(helmet))<.001
   rows.append({'file':label+'.png','preset':kind,'hair_style':style,'helmet':helmet,'helmet_design':style%3})
 print('HAIR_REVIEW '+kind,flush=True)
(out/'manifest.json').write_text(json.dumps({'passed_controls':True,'renders':rows},indent=2))
