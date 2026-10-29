import bpy,sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_collar_ears as fix
import rebuild_updated_characters as b
try:
 rows=[]
 for kind in b.PRESETS:
  for level in ['Gameplay_High','Gameplay_Mid','Gameplay_Far']:
   p=fix.OUT/kind/(level+'_validation.json');deadline=time.monotonic()+3600
   while not p.exists():
    assert time.monotonic()<deadline;time.sleep(5)
   bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/kind/(level+'.blend')))
   for o in bpy.context.scene.objects:
    if o.type!='MESH' or not ('__Foam_Ear_' in o.name or '__Ear_Pad_Piping' in o.name):continue
    pts=[o.matrix_world@v.co for v in o.data.vertices];vol=0.
    for face in o.data.polygons:
     f=face.vertices
     for i in range(1,len(f)-1):vol+=pts[f[0]].dot(pts[f[i]].cross(pts[f[i+1]]))/6
    assert vol>0,(kind,level,o.name,vol)
    assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in o.data.vertices)
    rows.append({'preset':kind,'profile':level,'object':o.name,'signed_volume':vol,'head_weights':True})
 assert len(rows)==216,len(rows)
 (fix.OUT/'ear_topology_validation.json').write_text(json.dumps({'passed':True,'objects':rows},indent=2))
except:(fix.OUT/'ear_topology_error.log').write_text(traceback.format_exc());raise
