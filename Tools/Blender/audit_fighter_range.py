"""Non-destructive visual range-of-motion audit for all fighter presets."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import build_sample_fighter_animations as motion
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/Animation/RangeOfMotion';OUT.mkdir(exist_ok=True)
POSES=['Neutral','Arms_Wide','Arms_Overhead','Forward_Reach','Elbows_Flexed','Cross_Body','Knee_L','Knee_R','Front_Kick_L','Front_Kick_R','Side_Kick_L','Side_Kick_R','Deep_Squat','Lunge_L','Lunge_R','Heel_Back_L','Heel_Back_R','Twist_L','Twist_R','Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']
def log(s):
 with (OUT/'audit.log').open('a') as f:f.write(str(s)+'\n')
def pose(r,label,scale):
 for p in r.pose.bones:p.matrix_basis=Matrix();p.rotation_mode='QUATERNION'
 def rot(n,axis,a):
  p=r.pose.bones[n];p.rotation_quaternion=Quaternion(p.bone.matrix_local.to_quaternion().inverted()@Vector(axis),a)
 drop=.32 if label=='Deep_Squat' else .17 if label.startswith('Lunge') else .025
 p=r.pose.bones['pelvis'];p.location=p.bone.matrix_local.to_3x3().inverted()@r.matrix_world.to_3x3().inverted()@Vector((0,0,-drop*scale))
 if label.startswith('Twist'):rot('spine_03',(0,0,1),.5 if label.endswith('L') else -.5)
 if label=='Deep_Squat':rot('spine_03',(1,0,0),.25)
 motion.update()
 for side,sign in [('l',1),('r',-1)]:
  selected=label.endswith(side.upper());foot=Vector((sign*.17,0,.083))*scale;pole=Vector((sign*.25,-.6,.5))*scale
  if selected and label.startswith('Knee'):foot=Vector((sign*.10,-.18,.64))*scale;pole=Vector((sign*.16,-.8,1.8))*scale
  if selected and label.startswith('Front_Kick'):foot=Vector((sign*.1,-.80,1.04))*scale;pole=Vector((sign*.18,-.8,1.8))*scale
  if selected and label.startswith('Side_Kick'):foot=Vector((sign*.80,0,.94))*scale;pole=Vector((sign*.85,-.15,1.4))*scale
  if selected and label.startswith('Heel_Back'):foot=Vector((sign*.17,.36,.64))*scale;pole=Vector((sign*.25,-.4,.4))*scale
  if label=='Deep_Squat':foot.x=sign*.23*scale;pole=Vector((sign*.38,-.5,.35))*scale
  if label.startswith('Lunge'):foot.y=(-.45 if selected else .40)*scale
  if label.startswith('Ankle') and side=='l':foot=Vector((.1,-.2,.55))*scale;pole=Vector((.16,-.8,1.8))*scale
  motion.solve(r,['thigh_'+side,'calf_'+side,'foot_'+side],foot,pole)
  p=r.pose.bones['foot_'+side];m=p.bone.matrix_local.copy();m.translation=p.matrix.translation;p.matrix=m;motion.update()
  if label.startswith('Ankle') and side=='l':
   p=r.pose.bones['foot_l'];axis=p.matrix.to_3x3().inverted()@Vector((1,0,0));p.rotation_quaternion=p.rotation_quaternion@Quaternion(axis,.55 if label=='Ankle_Flexed' else -.55);motion.update()
  shoulder=r.matrix_world@r.pose.bones['upperarm_'+side].matrix.translation
  target=Vector((sign*.24,-.30,1.40))*scale;elbow=Vector((sign*.52,-.12,1.04))*scale
  if label=='Neutral':target=Vector((sign*.29,0,.95))*scale
  if label=='Arms_Wide':target=shoulder+Vector((sign*.56,0,0))*scale
  if label=='Arms_Overhead':target=shoulder+Vector((sign*.10,0,.55))*scale;elbow=shoulder+Vector((sign*.35,-.12,.35))*scale
  if label in ['Forward_Reach','Wrists_Flexed','Wrists_Extended']:target=Vector((sign*.2,-.65,1.4))*scale
  if label=='Elbows_Flexed':target=Vector((sign*.25,-.05,1.54))*scale
  if label=='Cross_Body':target=Vector((-sign*.12,-.43 if side=='l' else -.26,1.39 if side=='l' else 1.32))*scale;elbow=Vector((sign*.35,-.47 if side=='l' else -.30,1.15))*scale
  motion.solve(r,['upperarm_'+side,'lowerarm_'+side,'hand_'+side],target,elbow)
  if label.startswith('Wrists'):
   r.pose.bones['hand_'+side].rotation_quaternion=Quaternion((1,0,0),.7 if label=='Wrists_Flexed' else -.7)
  motion.update()
 return {n:math.degrees((r.pose.bones[a].matrix.translation-r.pose.bones[b].matrix.translation).angle(r.pose.bones[c].matrix.translation-r.pose.bones[b].matrix.translation)) for n,a,b,c in [('elbow_l','upperarm_l','lowerarm_l','hand_l'),('elbow_r','upperarm_r','lowerarm_r','hand_r'),('knee_l','thigh_l','calf_l','foot_l'),('knee_r','thigh_r','calf_r','foot_r')]}
def audit(kind,source_override=None):
 source=ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend' if kind!='Updated_Medium' else ROOT/'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend'
 if source_override is not None:source=Path(source_override)
 bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;r=next(o for o in scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 r.animation_data_create();r.animation_data.action=None
 for track in r.animation_data.nla_tracks:track.mute=True
 for o in scene.objects:
  if o.type=='MESH' and o.data.shape_keys:
   keys=o.data.shape_keys
   if keys.animation_data:keys.animation_data.action=None
   for k in keys.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
  if o.get('MarkerLabel'):o.hide_render=True
 scene.render.engine='CYCLES';scene.cycles.samples=4;scene.render.resolution_x=480;scene.render.resolution_y=540;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 scene.frame_start=1;scene.frame_end=len(POSES)*12;scene.render.fps=24
 directory=OUT/kind;directory.mkdir(exist_ok=True);report={'source':str(source),'bones':len(r.data.bones),'poses':[],'cloth_mode':'General skinning; sample-specific corrective animation disabled'}
 for i,label in enumerate(POSES):
  r.animation_data.action=None;scene.frame_set(i*12+1);angles=pose(r,label,scale)
  values={p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in r.pose.bones}
  r.animation_data.action=bpy.data.actions.get('ROM_Audit')
  for p in r.pose.bones:
   p.location,p.rotation_quaternion,p.scale=values[p.name]
   for channel in ['location','rotation_quaternion','scale']:p.keyframe_insert(channel,frame=i*12+1,group=p.name)
  r.animation_data.action.name='ROM_Audit';report['poses'].append({'frame':i*12+1,'name':label,'joint_angles_deg':angles})
 action=r.animation_data.action;action.use_fake_user=True
 for gear in [False,True]:
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
  build.refresh(r)
  for i,label in enumerate(POSES):
   scene.frame_set(i*12+1);motion.update()
   build.view.camera(scene,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
   scene.render.filepath=str(directory/f'{"Gear" if gear else "Dobok"}_{i:02d}_{label}.png');bpy.ops.render.render(write_still=True)
   if kind=='Updated_Medium' and label in ['Arms_Overhead','Cross_Body','Knee_L','Front_Kick_L','Side_Kick_L','Deep_Squat','Heel_Back_L']:
    build.view.camera(scene,(4*scale,-.5*scale,1.7*scale),(0,-.1*scale,.96*scale),2.35*scale);scene.render.filepath=str(directory/f'{"Gear" if gear else "Dobok"}_{i:02d}_{label}_Side.png');bpy.ops.render.render(write_still=True)
  log(kind+(' gear' if gear else ' dobok')+' poses rendered')
 scene.frame_set(1);build.view.camera(scene,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
 for i,label in enumerate(POSES):scene.timeline_markers.new(label,frame=i*12+1)
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/'ROM_Audit.blend'));(directory/'audit.json').write_text(json.dumps(report,indent=2));log(kind+' COMPLETE')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:]
  for kind in args:audit(kind)
 except:log(traceback.format_exc());raise
