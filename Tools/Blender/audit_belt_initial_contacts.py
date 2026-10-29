import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_sparring_fit as fit
ROOT=fit.ROOT
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;r.update_tag();s.frame_set(1)
for collider in bpy.data.collections['Cloth_Belt_Contact'].objects:
 collider.driver_remove('hide_viewport');collider.hide_viewport=False;collider.hide_set(False)
bpy.context.view_layer.update();rows=[]
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=bpy.data.objects[name];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();points=[o.matrix_world@v.co for v in mesh.vertices];ev.to_mesh_clear()
 for collider in bpy.data.collections['Cloth_Belt_Contact'].objects:
  tree=fit.tree(collider,True);dist=[]
  for p in points:
   q,n,_,d=tree.find_nearest(p)
   if q is not None:dist.append((p-q).dot(n))
  rows.append({'belt':name,'collider':collider.name,'min_signed_m':min(dist),'max_signed_m':max(dist),'negative':sum(d<-.001 for d in dist),'points':len(dist)})
print(json.dumps(rows,indent=2));(ROOT/'Resources/Models/FinalRefinement/belt_initial_contacts.json').write_text(json.dumps(rows,indent=2))
