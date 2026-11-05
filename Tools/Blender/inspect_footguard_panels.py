import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend'))
rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
 uv=o.data.uv_layers.active
 counts={}
 for p in o.data.polygons:
  key=(p.material_index,tuple(round(x,3) for x in uv.data[p.loop_start].uv))
  counts[str(key)]=counts.get(str(key),0)+1
 rows.append({'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'materials':[m.name for m in o.data.materials],'uvs':[u.name for u in o.data.uv_layers],'regions':counts,'modifiers':[(m.name,m.type) for m in o.modifiers]})
(ROOT/'Resources/Models/FinalRefinement/footguard_inspection.json').write_text(json.dumps(rows,indent=2))
