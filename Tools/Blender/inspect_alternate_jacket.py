import bpy,json,bmesh
from pathlib import Path
R=Path('D:/Open-Stance-Gyeorugi/Resources/Models');O=R/'AlternateJacketRepair';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'CharacterSuite/Medium/Gameplay_High.blend'));result={}
for name in ['Jacket','Jacket_WhiteVNeck']:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);rows=[]
 while remaining:
  stack=[remaining.pop()];part=[]
  while stack:
   v=stack.pop();part.append(v)
   for e in v.link_edges:
    n=e.other_vert(v)
    if n in remaining:remaining.remove(n);stack.append(n)
  pts=[o.matrix_world@v.co for v in part];rows.append({'vertices':len(part),'bounds':[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]})
 result[name]=rows;bm.free()
(O/'components.json').write_text(json.dumps(result,indent=2))
