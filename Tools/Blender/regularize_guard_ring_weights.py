import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardRingWeights';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardQuadRebuildV4/Candidate.blend'))
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];old=[{g.group:g.weight for g in v.groups} for v in o.data.vertices]
 for base in (0,6144):
  for ring in range(48):
   ids=[base+layer*3072+ring*64+j for layer in range(2) for j in range(64)];mixed={}
   for i in ids:
    for group,w in old[i].items():mixed[group]=mixed.get(group,0)+w/len(ids)
   mixed=dict(sorted(mixed.items(),key=lambda x:-x[1])[:4]);total=sum(mixed.values())
   for i in ids:
    for group in old[i]:o.vertex_groups[group].remove([i])
    for group,w in mixed.items():o.vertex_groups[group].add([i],w/total,'REPLACE')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
