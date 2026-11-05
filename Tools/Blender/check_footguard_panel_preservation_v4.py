import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));rows={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
  m=o.data
  protected={'faces':[list(p.vertices) for p in m.polygons],'uvs':{uv.name:[list(x.uv) for x in uv.data] for uv in m.uv_layers},'weights':[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in m.vertices],'materials':[p.material_index for p in m.polygons]}
  rows[o.name]=hashlib.sha256(json.dumps(protected,sort_keys=True).encode()).hexdigest()
 return rows
a=snapshot(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend')
b=snapshot(ROOT/'Resources/Models/FinalRefinement/FootguardPanelReviewV4/Candidate.blend')
assert a==b,(a,b)
(ROOT/'Resources/Models/FinalRefinement/FootguardPanelReviewV4/preservation.json').write_text(json.dumps({'passed':True,'scope':'Footguard topology, UV layers, skin weights and face material assignments unchanged','hashes':b},indent=2))

