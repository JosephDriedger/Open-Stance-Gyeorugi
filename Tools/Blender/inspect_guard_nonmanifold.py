import bpy,json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardShellRebuildV4'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Candidate.blend'));o=bpy.data.objects['FootGuards'];m=o.data;edges=defaultdict(list)
for p in m.polygons:
 for edge in p.edge_keys:edges[tuple(sorted(edge))].append(p.index)
rows=[]
for edge,faces in edges.items():
 if len(faces)!=2:rows.append({'edge':edge,'points':[list(m.vertices[i].co) for i in edge],'faces':[{'index':i,'vertices':list(m.polygons[i].vertices),'normal':list(m.polygons[i].normal),'area':m.polygons[i].area} for i in faces]})
(OUT/'nonmanifold_detail.json').write_text(json.dumps(rows,indent=2))
