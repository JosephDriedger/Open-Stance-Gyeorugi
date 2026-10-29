"""Fit skirt and belt skinning to the sample kick; keep the body skeleton intact."""
import bpy,sys,json,traceback,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];scene.frame_set(1)
 report={}
 for name in ['Jacket','Belt']:
  o=bpy.data.objects[name]
  # Store original weights once, so tuning is repeatable.
  if 'BeforeKickClothingWeights' not in o:
   o['BeforeKickClothingWeights']=json.dumps([[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in o.data.vertices])
  original=json.loads(o['BeforeKickClothingWeights']);count=0
  for v,weights in zip(o.data.vertices,original):
   p=o.matrix_world@v.co
   if name=='Jacket':
    strength=(1-smooth(.87,.97,p.z))*(1-smooth(.01,.15,p.y))
    left=smooth(-.11,.03,p.x)
   else:
    front=1-smooth(-.14,-.04,p.y)
    strength=front*(.65+.35*(1-smooth(.85,.95,p.z)))
    left=smooth(-.15,-.015,p.x)
   strength=min(.98,strength)
   for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
   new={n:w*(1-strength) for n,w in weights}
   for n,w in [('thigh_l',strength*left),('thigh_r',strength*(1-left))]:new[n]=new.get(n,0)+w
   for n,w in new.items():
    if w>1e-6:(o.vertex_groups.get(n) or o.vertex_groups.new(name=n)).add([v.index],w,'REPLACE')
   count+=strength>.01
  report[name]={'reweighted_vertices':count}
 scene.frame_set(170)
 build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 for f in [162,170,179,189]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Clothing_Side_{f}.png');bpy.ops.render.render(write_still=True)
 build.view.camera(scene,(2.5,-4,2.0),(0,-.15,.94),2.3)
 scene.frame_set(170);scene.render.filepath=str(OUT/'Clothing_Front.png');bpy.ops.render.render(write_still=True)
 scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 (OUT/'clothing_fix.json').write_text(json.dumps(report,indent=2))
 with (OUT/'build.log').open('a') as f:f.write('CLOTHING REVIEW READY\n')
try:run()
except:
 with (OUT/'build.log').open('a') as f:f.write(traceback.format_exc())
 raise
