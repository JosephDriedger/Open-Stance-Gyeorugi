import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Resources/Models/FinalRefinement'
def capture(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));result={}
 for name in ('FootGuards','FootGuards_PaddedInstep'):
  o=bpy.data.objects[name]
  payload={'positions':[tuple(v.co) for v in o.data.vertices],'faces':[tuple(p.vertices) for p in o.data.polygons],'uv':{uv.name:[tuple(d.uv) for d in uv.data] for uv in o.data.uv_layers},'materials':[m.name for m in o.data.materials]}
  result[name]={'mesh_sha256':hashlib.sha256(json.dumps(payload).encode()).hexdigest(),'weights_normalized':all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in o.data.vertices),'max_influences':max(len(v.groups) for v in o.data.vertices)}
 return result
before=capture(BASE/'FootguardVariantReview/Candidate.blend')
after=capture(BASE/'FootguardLocalROMSmooth/Candidate.blend')
for name in before:
 assert before[name]['mesh_sha256']==after[name]['mesh_sha256'],name
 assert after[name]['weights_normalized'] and after[name]['max_influences']<=4,name
(BASE/'FootguardLocalROMSmooth/preservation.json').write_text(json.dumps({'passed':True,'scope':'Guard geometry, topology, UVs and material slots unchanged; weights normalized and limited to four influences','before':before,'after':after},indent=2))
