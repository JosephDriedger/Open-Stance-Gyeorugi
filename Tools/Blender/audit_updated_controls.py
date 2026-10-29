"""Resolve all used customization driver targets in final native assets."""
import bpy,sys,json,traceback
from mathutils import Quaternion
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
def run(kind):
 rows=[]
 for name in ['Preview',f'OpenStance_{kind}_Animation','Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
  p=b.OUT/kind/(name+'.blend');bpy.ops.wm.open_mainfile(filepath=str(p));rig=bpy.data.objects['RIG_Body_'+kind];changed=False
  if 'MatchSide' not in rig:rig['MatchSide']=0;rig.id_properties_ui('MatchSide').update(min=0,max=1);changed=True
  b.refresh(rig);owners=set(bpy.context.scene.objects)
  for o in bpy.context.scene.objects:
   if o.type=='MESH':
    if o.data.shape_keys:owners.add(o.data.shape_keys)
    for m in o.data.materials:
     if m and m.use_nodes:owners.add(m.node_tree)
  count=0
  for owner in owners:
   if not owner.animation_data:continue
   for d in owner.animation_data.drivers:
    if d.mute:continue
    for v in d.driver.variables:
     if v.type=='SINGLE_PROP':
      for t in v.targets:
       assert t.id is not None,(p.name,owner.name,d.data_path,v.name)
       t.id.path_resolve(t.data_path)
    if not d.driver.is_valid:
     detail={'file':str(p),'materials':[m.name for m in bpy.data.materials if m.use_nodes and m.node_tree==owner],'expression':d.driver.expression,'targets':[(v.name,t.id.name if t.id else None,t.data_path) for v in d.driver.variables for t in v.targets]}
     b.log('DRIVER RETRY '+json.dumps(detail))
     d.driver.expression=d.driver.expression;owner.update_tag();b.refresh(rig)
    assert d.driver.is_valid,(p.name,owner.name,d.data_path)
    count+=1
  if changed:bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True)
  if name.startswith(('Gameplay_','Crowd_')):
   cap=next(o for o in b.meshes() if 'Scalp_Coverage' in o.name and not o.hide_render)
   bone=rig.pose.bones['head'];saved=bone.rotation_quaternion.copy();mode=bone.rotation_mode
   point=lambda:(cap.matrix_world@cap.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices[0].co).copy()
   before=point();bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,1,0),.15);bpy.context.view_layer.update()
   assert (point()-before).length>.003,'Hair did not follow head motion'
   bone.rotation_quaternion=saved;bone.rotation_mode=mode;bpy.context.view_layer.update()
   totals={};deps=bpy.context.evaluated_depsgraph_get()
   for o in b.meshes():
    if not o.hide_render:
     e=o.evaluated_get(deps);mesh=e.to_mesh();mesh.calc_loop_triangles();totals[o.name]=len(mesh.loop_triangles);e.to_mesh_clear()
   report_path=b.OUT/kind/(name+'_validation.json');profile=json.loads(report_path.read_text());profile['visible_evaluated_triangles']=totals;profile['visible_evaluated_total']=sum(totals.values());report_path.write_text(json.dumps(profile,indent=2))
  rows.append({'file':p.name,'resolved_drivers':count,'passed':True})
 (b.OUT/kind/'controls_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
 b.log(kind+' controls audit complete')
if __name__=='__main__':
 try:
  for kind in sys.argv[sys.argv.index('--')+1:]:run(kind)
 except:b.log(traceback.format_exc());raise
