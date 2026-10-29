import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import audit_fighter_range as audit
try:
 for folder in sorted(audit.OUT.iterdir()):
  path=folder/'ROM_Audit.blend'
  if not path.exists():continue
  bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));a=r.animation_data.action;scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  r.animation_data.action=None;s.frame_set(61);angles=audit.pose(r,'Cross_Body',scale);values={p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in r.pose.bones};r.animation_data.action=a
  for p in r.pose.bones:
   p.location,p.rotation_quaternion,p.scale=values[p.name]
   for channel in ['location','rotation_quaternion','scale']:p.keyframe_insert(channel,frame=61,group=p.name)
  for gear in [False,True]:
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
   audit.build.refresh(r);s.frame_set(61);audit.motion.update();audit.build.view.camera(s,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale);s.render.filepath=str(folder/f'{"Gear" if gear else "Dobok"}_05_Cross_Body.png');bpy.ops.render.render(write_still=True)
  s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(path));report=json.loads((folder/'audit.json').read_text());report['poses'][5]['joint_angles_deg']=angles;report['cross_body_fixture']='Forearms staggered in depth and height';(folder/'audit.json').write_text(json.dumps(report,indent=2));audit.log(folder.name+' cross-body fixture corrected')
except:audit.log(traceback.format_exc());raise
