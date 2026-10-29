import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
bpy.ops.wm.open_mainfile(filepath=str(out/'Medium_Sparring_Samples.blend'))
r=bpy.data.objects['RIG_Body_Medium'];data={'bones':[b.name for b in r.data.bones if any(s in b.name for s in ['thigh','pelvis','cloth','skirt','spine'])]}
for name in ['Jacket','Belt','Pants']:
 o=bpy.data.objects[name];points=[o.matrix_world@v.co for v in o.data.vertices]
 groups={g.index:g.name for g in o.vertex_groups};totals={}
 for v in o.data.vertices:
  for g in v.groups:totals[groups[g.group]]=totals.get(groups[g.group],0)+g.weight
 data[name]={'bounds':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],'groups':sorted(totals.items(),key=lambda x:-x[1])[:20],'modifiers':[(m.name,m.type) for m in o.modifiers]}
 if name=='Belt':
  adjacency=[[] for _ in o.data.vertices]
  for e in o.data.edges:a,b=e.vertices;adjacency[a].append(b);adjacency[b].append(a)
  unseen=set(range(len(points)));parts=[]
  while unseen:
   todo=[unseen.pop()];ids=[]
   while todo:
    a=todo.pop();ids.append(a)
    for b in adjacency[a]:
     if b in unseen:unseen.remove(b);todo.append(b)
   pp=[points[i] for i in ids];parts.append({'count':len(ids),'bounds':[[min(p[i] for p in pp),max(p[i] for p in pp)] for i in range(3)]})
  data[name]['parts']=parts
(out/'clothing_inspection.json').write_text(json.dumps(data,indent=2))
