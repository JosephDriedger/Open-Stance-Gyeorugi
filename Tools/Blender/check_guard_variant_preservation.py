import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardVariantReview'
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));data={}
 for name in ('FootGuards','FootGuards_PaddedInstep'):
  o=bpy.data.objects[name];m=o.data
  data[name]={'weights':[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],'uvs':{uv.name:[list(x.uv) for x in uv.data] for uv in m.uv_layers},'positions':[list(v.co) for v in m.vertices]}
 return data
a=snapshot(ROOT/'Resources/Models/FinalRefinement/FootguardCorrectedKickReview/Animation_Test.blend');b=snapshot(OUT/'Candidate.blend')
assert a['FootGuards']==b['FootGuards'],'Standard guard changed'
for key in ('weights','faces','uvs'):assert a['FootGuards_PaddedInstep'][key]==b['FootGuards_PaddedInstep'][key],key
for i in list(range(3072,6144))+list(range(9216,12288)):assert a['FootGuards_PaddedInstep']['positions'][i]==b['FootGuards_PaddedInstep']['positions'][i],i
(OUT/'preservation.json').write_text(json.dumps({'passed':True,'standard_guard_unchanged':True,'padded_weights_topology_uvs_inner_lining_unchanged':True},indent=2))
