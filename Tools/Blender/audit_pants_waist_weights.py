import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_AnchorFit/Candidate.blend'))
o=bpy.data.objects['Pants'];pts=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in pts);rows=[]
for distance in [.02,.04,.06,.08]:
    ids=[i for i,p in enumerate(pts) if p.z>top-distance];weights={}
    for i in ids:
        for group in o.data.vertices[i].groups:
            name=o.vertex_groups[group.group].name
            weights[name]=weights.get(name,0)+group.weight/len(ids)
    rows.append({'top_band_m':distance,'count':len(ids),'mean_weights':weights})
report={'top_z':top,'bands':rows}
(root/'pants_waist_weights.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
