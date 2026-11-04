import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'FootguardPanelReviewV3'
def capture(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));result={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
  o.data.calc_loop_triangles()
  result[o.name]=[(tuple(t.vertices),[(o.matrix_world@o.data.vertices[i].co).copy() for i in t.vertices]) for t in o.data.loop_triangles]
 return result
a=capture(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend')
b=capture(ROOT/'Resources/Models/FinalRefinement'/folder/'Candidate.blend');rows=[]
for name,triangles in a.items():
 flipped=collapsed=0
 for (ids,old),(ids2,new) in zip(triangles,b[name]):
  assert ids==ids2
  before=(old[1]-old[0]).cross(old[2]-old[0]);after=(new[1]-new[0]).cross(new[2]-new[0])
  if before.length>1e-10:
   flipped+=before.dot(after)<0
   collapsed+=after.length<before.length*.01
 rows.append({'object':name,'reversed_triangle_normals':flipped,'new_near_collapsed_triangles':collapsed})
(ROOT/'Resources/Models/FinalRefinement'/folder/'surface_quality.json').write_text(json.dumps({'passed':all(not row['reversed_triangle_normals'] and not row['new_near_collapsed_triangles'] for row in rows),'checks':rows},indent=2))
