import bpy,json,sys
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[2]
folder=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'FootguardShellRebuildV3'
OUT=ROOT/'Resources/Models/FinalRefinement'/folder
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Candidate.blend'))
rows=[]
for name in ['Body','FootGuards','FootGuards_PaddedInstep']:
 o=bpy.data.objects[name];m=o.data;links=defaultdict(set);edges=Counter()
 for p in m.polygons:
  for edge in p.edge_keys:
   a,b=edge;links[a].add(b);links[b].add(a);edges[tuple(sorted(edge))]+=1
 remaining=set(range(len(m.vertices)));components=[]
 while remaining:
  start=remaining.pop();group={start};stack=[start]
  while stack:
   for j in links[stack.pop()]:
    if j in remaining:remaining.remove(j);group.add(j);stack.append(j)
  points=[o.matrix_world@m.vertices[i].co for i in group]
  components.append({'vertices':len(group),'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]})
 invalid=[v.index for v in m.vertices if not v.groups or abs(sum(g.weight for g in v.groups if o.vertex_groups[g.group].name in bpy.data.objects['RIG_Body_Stocky'].data.bones)-1)>.001]
 rows.append({'object':name,'edge_valence':dict(Counter(edges.values())),'components':sorted(components,key=lambda x:-x['vertices']),'invalid_deform_weights':len(invalid)})
(OUT/'shell_audit.json').write_text(json.dumps(rows,indent=2))
