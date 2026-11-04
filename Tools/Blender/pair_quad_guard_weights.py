import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardPairedWeights';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardQuadRebuildV4/Candidate.blend'))
rows=[];ring_vertices=48*64
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];assert len(o.data.vertices)==4*ring_vertices
 old=[{g.group:g.weight for g in v.groups} for v in o.data.vertices];maximum=0
 for base in (0,2*ring_vertices):
  for i in range(ring_vertices):
   a=base+i;b=a+ring_vertices;combined={g:(old[a].get(g,0)+old[b].get(g,0))*.5 for g in set(old[a])|set(old[b])}
   combined=dict(sorted(combined.items(),key=lambda x:-x[1])[:4]);total=sum(combined.values());combined={g:w/total for g,w in combined.items()}
   for index in (a,b):
    maximum=max(maximum,sum(abs(old[index].get(g,0)-combined.get(g,0)) for g in set(old[index])|set(combined)))
    for g in old[index]:o.vertex_groups[g].remove([index])
    for g,w in combined.items():o.vertex_groups[g].add([index],w,'REPLACE')
 rows.append({'object':name,'paired_vertices':2*ring_vertices,'maximum_weight_L1_change':maximum})
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'geometry_changed':False,'changes':rows},indent=2))
