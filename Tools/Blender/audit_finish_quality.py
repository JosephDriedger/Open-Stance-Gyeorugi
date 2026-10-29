import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
OUT=a.ROOT/'Resources/Models/FinishQuality';OUT.mkdir(exist_ok=True)
try:
 for kind in ['Male_Athletic','Female_Athletic']:
  s,r,z,src=a.load(kind,'Preview');s.cycles.samples=24
  d=OUT/kind;d.mkdir(exist_ok=True)
  for p in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[p]=False
  for style in range(6):
   r['HairStyle']=style;a.build.refresh(r)
   for side,pos in [('Front',(.5,-1,1.84)),('Rear',(.5,1,1.84))]:
    a.render(s,r,z,d,f'Hair{style}_{side}',pos,(0,0,1.65),.55,640,640)
  a.render(s,r,z,d,'Uniform',(.7,-4,1.6),(0,0,1.10),1.35,640,720)
  report={}
  for o in s.objects:
   if o.type=='MESH' and o.name.startswith(('Jacket','Pants','Belt','Hair_Low_Ponytail')):
    report[o.name]={'vertices':len(o.data.vertices),'materials':[{ 'name':m.name,'nodes':[(n.name,n.type) for n in m.node_tree.nodes] if m.use_nodes else []} for m in o.data.materials if m]}
  (d/'inventory.json').write_text(json.dumps(report,indent=2))
 (OUT/'complete.txt').write_text('Complete')
except:(OUT/'error.log').write_text(traceback.format_exc());raise
