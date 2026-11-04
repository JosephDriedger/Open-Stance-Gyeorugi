import bpy,sys,json,math
from mathutils.bvhtree import BVHTree
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from refine_pants_cloth import configure
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/PantsClothDeliveryV3'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Medium_Wrap.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r['BlenderCloth']=False;s.frame_set(1);bpy.context.view_layer.update();assert configure(s)
pants=bpy.data.objects['Pants'];probe=pants.copy();probe.data=pants.data.copy();probe.animation_data_clear();probe.name='AUDIT_Kinematic_Pants';s.collection.objects.link(probe);probe.hide_render=True;probe.hide_viewport=False;probe.hide_set(False)
for m in list(probe.modifiers):
 if m.type=='CLOTH':probe.modifiers.remove(m)
for o in s.objects:
 if o.type=='MESH' and o!=pants:
  for m in o.modifiers:
   if m.type=='CLOTH':
    for prop in ('show_viewport','show_render'):m.driver_remove(prop);setattr(m,prop,False)
r['BlenderCloth']=True;r.update_tag();s.frame_set(1);rows=[]
for frame in range(1,73):
 s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
 if frame not in (26,35,72):continue
 vertices=[]
 for o in (pants,probe):
  ev=o.evaluated_get(dg);mesh=ev.to_mesh();vertices.append([o.matrix_world@v.co for v in mesh.vertices]);ev.to_mesh_clear()
 assert len(vertices[0])==len(vertices[1])
 distances=[(a-b).length for a,b in zip(*vertices)]
 index=max(range(len(distances)),key=lambda i:distances[i])
 row={'frame':frame,'maximum_displacement_m':max(distances),'mean_displacement_m':sum(distances)/len(distances),'p99_displacement_m':sorted(distances)[int(len(distances)*.99)],'maximum_vertex_index':index,'maximum_vertex_simulated':list(vertices[0][index]),'maximum_vertex_skinned':list(vertices[1][index])}
 if max(distances)>.05:
  contacts=[];cloth=next(m for m in pants.modifiers if m.type=='CLOTH')
  for contact in cloth.collision_settings.collection.objects:
   ev=contact.evaluated_get(dg);mesh=ev.to_mesh();tree=BVHTree.FromPolygons([contact.matrix_world@v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
   point=vertices[1][index];hit,normal,_,_=tree.find_nearest(point);before=(point-hit).dot(normal)
   point=vertices[0][index];hit,normal,_,_=tree.find_nearest(point);after=(point-hit).dot(normal)
   contacts.append({'collider':contact.name,'skinned_signed_distance_m':before,'simulated_signed_distance_m':after});ev.to_mesh_clear()
  row['contact_response']=min(contacts,key=lambda x:x['skinned_signed_distance_m'])
 rows.append(row)
maximum=max(x['maximum_displacement_m'] for x in rows)
passed=1e-6<maximum<.10 and all(math.isfinite(x['mean_displacement_m']) and x['mean_displacement_m']<.003 and x['p99_displacement_m']<.04 for x in rows)
passed=passed and all('contact_response' not in x or (x['contact_response']['skinned_signed_distance_m']<-.01 and x['contact_response']['simulated_signed_distance_m']>=-.001) for x in rows)
(OUT/'secondary_motion.json').write_text(json.dumps({'passed':passed,'checks':rows,'scope':'Medium simulated trousers versus the same skinned trousers with cloth removed; no new animation keys.'},indent=2))
assert passed,rows
print('PANTS_SECONDARY_MOTION_PASSED',rows,flush=True)


