import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardPanelRebuildV2'
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));result={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
  m=o.data
  data={'vertices':[list(v.co) for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],'weights':[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in m.vertices],'original_uvs':{name:[list(x.uv) for x in m.uv_layers[name].data] for name in ('UVMap','UVWeave')},'shape_keys':{key.name:[list(v.co) for v in key.data] for key in m.shape_keys.key_blocks} if m.shape_keys else {}}
  result[o.name]=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
 return result
a=snapshot(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend');b=snapshot(OUT/'Candidate.blend')
assert a==b
assert bpy.data.images['Footguard_Continuous_Instep'].packed_file
(OUT/'preservation.json').write_text(json.dumps({'passed':True,'geometry_weights_shape_keys_original_uvs_unchanged':True,'texture_packed':True,'hashes':b},indent=2))
