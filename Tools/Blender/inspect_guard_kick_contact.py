import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardAnimationReview'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Animation_Test.blend'));s=bpy.context.scene;s.frame_set(35)
body=bpy.data.objects['Body']
for m in body.modifiers:
 if m.type=='MASK':m.show_viewport=False
dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);mesh=ev.to_mesh();tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons]);ev.to_mesh_clear()
o=bpy.data.objects['FootGuards'];ev=o.evaluated_get(dg);mesh=ev.to_mesh();rows=[]
for v in mesh.vertices:
 point=o.matrix_world@v.co;hit,n,_,_=tree.find_nearest(point);distance=(point-hit).dot(n)
 if distance<-.001:rows.append({'vertex':v.index,'signed_distance_m':distance,'rest':list(o.data.vertices[v.index].co),'posed':list(point),'weights':{o.vertex_groups[g.group].name:g.weight for g in o.data.vertices[v.index].groups}})
ev.to_mesh_clear();(OUT/'kick_contact.json').write_text(json.dumps(rows,indent=2))
