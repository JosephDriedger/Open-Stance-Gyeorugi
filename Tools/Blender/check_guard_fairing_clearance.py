import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardFairingReviewV2'
def sample(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));body=bpy.data.objects['Body'];m=body.data
 tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in m.vertices],[tuple(p.vertices) for p in m.polygons]);rows={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
  distances=[]
  for v in o.data.vertices:
   p=o.matrix_world@v.co;point,normal,index,d=tree.find_nearest(p);distances.append((p-point).dot(normal))
  rows[o.name]=distances
 return rows
a=sample(ROOT/'Resources/Models/FinalRefinement/FootguardRemeshRefined/Candidate.blend');b=sample(OUT/'Candidate.blend');rows=[]
for name,values in b.items():
 new=[i for i,(before,after) in enumerate(zip(a[name],values)) if before>=-.001 and after<-.001]
 worsened=[i for i,(before,after) in enumerate(zip(a[name],values)) if after<-.001 and after<before-.001]
 rows.append({'object':name,'new_penetrations_over_1mm':len(new),'worsened_penetrations_over_1mm':len(worsened),'minimum_signed_clearance_m':min(values),'baseline_minimum_m':min(a[name])})
(OUT/'body_clearance.json').write_text(json.dumps({'passed':all(not row['new_penetrations_over_1mm'] and not row['worsened_penetrations_over_1mm'] for row in rows),'scope':'Rest-pose nearest-surface vertex check, not complete posed collision validation','checks':rows},indent=2))

