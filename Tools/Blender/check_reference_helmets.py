"""Saved-file validation for all three reference helmet variants."""
import bpy,json,traceback
from pathlib import Path
from mathutils import Quaternion,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/CharacterSuite'
try:
 report={}
 for kind in ['Medium','Compact','Stocky','LeanTall','Tall']:
  for profile in ['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far']:
   bpy.ops.wm.open_mainfile(filepath=str(OUT/kind/(profile+'.blend')));rig=bpy.data.objects['RIG_Body_'+kind]
   helmets=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Helmet_')];assert len(helmets)==3
   rig['Wear_Helmet']=True;counts={}
   for i in range(3):
    rig['HelmetStyle']=i;rig.update_tag();bpy.context.scene.frame_set(i+2);bpy.context.view_layer.update()
    visible=[o for o in helmets if not o.hide_render];assert len(visible)==1
    o=visible[0];o.data.calc_loop_triangles();counts[o.name]=len(o.data.loop_triangles)
    assert next(m.object for m in o.modifiers if m.type=='ARMATURE')==rig
    names={g.index:g.name for g in o.vertex_groups}
    assert all(len(v.groups)==1 and names[v.groups[0].group]=='head' and abs(v.groups[0].weight-1)<1e-5 for v in o.data.vertices)
    assert all(d.driver.is_valid for d in o.animation_data.drivers)
    for mat in o.data.materials:
     if mat.node_tree.animation_data:
      for d in mat.node_tree.animation_data.drivers:
       assert d.driver.is_valid and all(t.id==rig for v in d.driver.variables for t in v.targets)
    deps=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(deps);before=o.matrix_world@e.data.vertices[0].co
    p=rig.pose.bones['head'];saved=p.matrix_basis.copy();p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion((0,1,0),.25);bpy.context.view_layer.update()
    after=o.matrix_world@o.evaluated_get(deps).data.vertices[0].co;assert (after-before).length>.005,(kind,profile,o.name,'not following head')
    p.matrix_basis=saved;bpy.context.view_layer.update()
   rig['Wear_Helmet']=False;rig.update_tag();bpy.context.scene.frame_set(9);bpy.context.view_layer.update();assert all(o.hide_render for o in helmets)
   report[kind+'/'+profile]={'variants':counts,'head_skinning':True,'head_pose_deformation':True,'exclusive_style_switch':True,'removable':True,'material_drivers':True}
 (OUT/'helmet_validation.json').write_text(json.dumps(report,indent=2))
except:
 (OUT/'helmet_validation_error.log').write_text(traceback.format_exc());raise
