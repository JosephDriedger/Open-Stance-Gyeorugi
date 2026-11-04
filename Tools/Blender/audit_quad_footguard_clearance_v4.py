import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardQuadRebuildV4'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Candidate.blend'));body=bpy.data.objects['Body']
tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons]);rows=[]
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];distances=[]
 for v in o.data.vertices:
  point=o.matrix_world@v.co;hit,n,_,_=tree.find_nearest(point);distances.append((point-hit).dot(n))
 o.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in o.data.loop_triangles];points=[o.matrix_world@v.co for v in o.data.vertices]
 own=BVHTree.FromPolygons(points,triangles,all_triangles=True)
 overlaps=[(a,b) for a,b in own.overlap(own) if a<b and not set(triangles[a])&set(triangles[b])]
 rows.append({'object':name,'vertices_inside_over_1mm':sum(d<-.001 for d in distances),'minimum_signed_clearance_m':min(distances),'nonadjacent_triangle_overlap_pairs':len(overlaps)})
(OUT/'clearance.json').write_text(json.dumps({'scope':'Rest-pose vertex clearance and BVH nonadjacent triangle overlap; not swept animation validation','checks':rows},indent=2))

