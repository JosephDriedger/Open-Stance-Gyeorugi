"""Replace the straight-line foot lift with chamber/strike/rechamber timing."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import build_sample_fighter_animations as demo
import rebuild_updated_characters as build
OUT=demo.OUT
def smooth(f,keys):
 for (a,x),(b,y) in zip(keys,keys[1:]):
  if a<=f<=b:
   t=(f-a)/(b-a);t=t*t*(3-2*t);return x*(1-t)+y*t
 return keys[0][1] if f<keys[0][0] else keys[-1][1]
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];action=bpy.data.actions['Sample_Front_Kick'];combined=bpy.data.actions['Sample_Demo']
 changed=['pelvis','spine_01','spine_03','spine_05','head']+[n+'_'+s for s in 'lr' for n in ['thigh','calf','foot','ball','upperarm','lowerarm','hand']]
 samples=[]
 for f in range(1,73):
  r.animation_data.action=action;scene.frame_set(f)
  for n in changed:r.pose.bones[n].matrix_basis=Matrix();r.pose.bones[n].rotation_mode='QUATERNION'
  load=smooth(f,[(1,0),(9,0),(20,1),(48,1),(66,0),(72,0)])
  extension=smooth(f,[(1,0),(27,0),(34,1),(37,1),(44,0),(72,0)])
  p=r.pose.bones['pelvis'];offset=Vector((-.15*load,.025*load,-.035+.018*load))
  p.location=p.bone.matrix_local.to_3x3().inverted()@r.matrix_world.to_3x3().inverted()@offset
  p=r.pose.bones['spine_03'];p.rotation_quaternion=Quaternion(p.bone.matrix_local.to_quaternion().inverted()@Vector((1,0,0)),-.10*load)
  demo.update()
  base=Vector((.19,-.08186,.082762));chamber=Vector((.015,-.16,.64));strike=Vector((.005,-.84,1.10))
  foot=smooth(f,[(1,base),(12,base),(26,chamber),(34,strike),(37,strike),(45,chamber),(52,chamber),(66,base),(72,base)])
  for s in 'lr':
   target=foot if s=='l' else Vector((-.19,.06814,.082762))
   # An elevated forward knee pole keeps the knee above the ankle during chamber.
   pole=(.02,-.7,1.85) if s=='l' else (-.21,-1,.55)
   demo.solve(r,['thigh_'+s,'calf_'+s,'foot_'+s],target,pole)
   p=r.pose.bones['foot_'+s];position=p.matrix.translation.copy()
   tilt=(.40*load*(1-extension)-.12*extension) if s=='l' else 0
   m=Quaternion((1,0,0),tilt).to_matrix().to_4x4()@r.data.bones[p.name].matrix_local
   m.translation=position;p.matrix=m
   if s=='l':
    toe=r.pose.bones['ball_l'];toe.rotation_quaternion=Quaternion(toe.bone.matrix_local.to_quaternion().inverted()@Vector((1,0,0)),-.35*extension)
   demo.update()
   sign=1 if s=='l' else -1
   demo.solve(r,['upperarm_'+s,'lowerarm_'+s,'hand_'+s],(sign*.23-.075*load,-.31+.025*load,1.40+.012*load),(sign*.52,-.13,1.02))
  demo.update()
  if f in [1,26,35,45,66]:
   a,b,c=[r.matrix_world@r.pose.bones[n].matrix.translation for n in ['thigh_l','calf_l','foot_l']]
   angle=math.degrees((a-b).angle(c-b))
   support=r.matrix_world@r.pose.bones['foot_r'].matrix.translation
   samples.append({'frame':f,'knee_angle':angle,'knee':list(b),'ankle':list(c),'support_ankle':list(support)})
  vals={n:(r.pose.bones[n].location.copy(),r.pose.bones[n].rotation_quaternion.copy()) for n in changed}
  for target_action,frame in [(action,f),(combined,144+f)]:
   r.animation_data.action=target_action
   for n,(loc,q) in vals.items():
    p=r.pose.bones[n];p.location=loc;p.rotation_quaternion=q
    p.keyframe_insert('location',frame=frame,group=n);p.keyframe_insert('rotation_quaternion',frame=frame,group=n)
 assert samples[2]['knee_angle']>155,samples
 assert samples[1]['knee_angle']<100,samples
 assert max(Vector(s['support_ankle']).__sub__(Vector(samples[0]['support_ankle'])).length for s in samples)<.002
 (OUT/'kick_pose_validation.json').write_text(json.dumps(samples,indent=2))
 r.animation_data.action=action;scene.frame_start=1;scene.frame_end=72;scene.frame_set(1);build.export(r,OUT/'Front_Kick.fbx',True)
 r.animation_data.action=combined;scene.frame_start=1;scene.frame_end=216;scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 for f in [170,179,189]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Kick_Review_{f}.png');bpy.ops.render.render(write_still=True)
 build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 scene.frame_set(179);scene.render.filepath=str(OUT/'Kick_Side.png');bpy.ops.render.render(write_still=True)
 demo.log('KICK REFINEMENT COMPLETE')
try:run()
except:demo.log(traceback.format_exc());raise
