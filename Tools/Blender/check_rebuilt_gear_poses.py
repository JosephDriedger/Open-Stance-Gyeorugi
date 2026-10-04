"""Check all rebuilt gear attachments against actual posed evaluated meshes."""
import bpy,json,traceback,sys
from pathlib import Path
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
OUT=Path(__file__).resolve().parents[2]/'Resources/Models/GearUpgrade'
try:
 report={};paths=[p for p in sorted(OUT.glob('*/*.blend')) if p.stem in ['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far']];assert len(paths)==20
 for path in paths:
  bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+path.parent.name];scene=bpy.context.scene
  tests={}
  for category,count,bone_name in [('Helmet',3,'head'),('Protector',2,'spine_03')]:
   for index in range(count):
    rig[category+'Style']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1);bpy.context.view_layer.update()
    objects=[o for o in scene.objects if o.get('GearCategory')==category and o['GearStyle']==index]
    assert objects and all(not o.hide_render for o in objects)
    deps=bpy.context.evaluated_depsgraph_get();before={o.name:(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co).copy() for o in objects}
    bone=rig.pose.bones[bone_name];saved=bone.matrix_basis.copy();bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,0,1),.18);bpy.context.view_layer.update()
    distances=[(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co-before[o.name]).length for o in objects]
    assert min(distances)>.00001,(path,category,index,min(distances))
    tests[category+'_'+str(index)]={'parts':len(objects),'minimum_motion_m':min(distances)}
    if path.parent.name=='Medium' and path.stem=='Gameplay_High' and category=='Protector' and index==0:
     rig['HelmetStyle']=0;rig.update_tag();bpy.context.view_layer.update();view.camera(scene,(.8,-2,1.55),(0,0,1.34),1.12);scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
     scene.render.filepath=str(OUT/'Medium'/'Torso_Twist_Check.png');bpy.ops.render.render(write_still=True)
    bone.matrix_basis=saved;bpy.context.view_layer.update()
  report[str(path.relative_to(OUT))]={'passed':True,'attachment_checks':tests}
  (OUT/'pose_validation.json').write_text(json.dumps(report,indent=2))
 (OUT/'poses.log').write_text('COMPLETE')
except:(OUT/'poses.log').write_text(traceback.format_exc());raise
