"""Separate hand-authored motion tests; never modifies library masters."""
import bpy, math, sys, json, traceback
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Resources/Models/Animation/Samples'
OUT.mkdir(exist_ok=True)
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def update():bpy.context.view_layer.update()
def solve(rig,names,target,pole):
 update();u,l,h=[rig.pose.bones[n] for n in names]
 a,b,c=[p.matrix.translation.copy() for p in (u,l,h)]
 target=rig.matrix_world.inverted()@Vector(target);pole=rig.matrix_world.inverted()@Vector(pole)
 l1=(b-a).length;l2=(c-b).length;axis=(target-a).normalized();dist=min((target-a).length,(l1+l2)*.985)
 target=a+axis*dist;d=(l1*l1-l2*l2+dist*dist)/(2*dist)
 perp=pole-a-axis*(pole-a).dot(axis);perp.normalize();elbow=a+axis*d+perp*math.sqrt(max(0,l1*l1-d*d))
 q=(b-a).rotation_difference(elbow-a);u.matrix=Matrix.Translation(a)@q.to_matrix().to_4x4()@Matrix.Translation(-a)@u.matrix
 update();b=l.matrix.translation.copy();c=h.matrix.translation.copy();q=(c-b).rotation_difference(target-b)
 l.matrix=Matrix.Translation(b)@q.to_matrix().to_4x4()@Matrix.Translation(-b)@l.matrix;update()
def bump(f,a,b,c):
 if f<a or f>c:return 0
 t=(f-a)/(b-a) if f<b else (c-f)/(c-b)
 return t*t*(3-2*t)
def run():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'))
 scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_Medium']
 rig.animation_data.action=None
 for tr in rig.animation_data.nla_tracks:tr.mute=True
 for n in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[n]=True
 build.refresh(rig)
 scene.render.fps=24;scene.frame_start=1;scene.frame_end=72
 restfeet={s:rig.matrix_world@rig.data.bones['foot_'+s].head_local for s in 'lr'}
 log({s:list(v) for s,v in restfeet.items()})
 changed=['pelvis','spine_01','spine_03','spine_05','head']+[n+'_'+s for s in 'lr' for n in ['thigh','calf','foot','upperarm','lowerarm','hand']]
 fingers=[f'{finger}_{joint:02d}_{s}' for s in 'lr' for finger in ['index','middle','ring','pinky','thumb'] for joint in [1,2,3] if f'{finger}_{joint:02d}_{s}' in rig.pose.bones]
 changed+=fingers
 clips=[]
 for label in ['Guard_Idle','Straight_Punches','Front_Kick']:
  rig.animation_data.action=None
  for f in range(1,73):
   scene.frame_set(f)
   for p in rig.pose.bones:p.matrix_basis=Matrix();p.rotation_mode='QUATERNION'
   def rot(n,axis,angle):
    p=rig.pose.bones[n];p.rotation_quaternion=Quaternion(p.bone.matrix_local.to_quaternion().inverted()@Vector(axis),angle)
   kick=bump(f,15,37,61) if label=='Front_Kick' else 0
   jab=bump(f,12,22,33) if label=='Straight_Punches' else 0
   cross=bump(f,37,47,61) if label=='Straight_Punches' else 0
   bob=.006*math.sin((f-1)*math.tau/71)
   p=rig.pose.bones['pelvis'];p.location=p.bone.matrix_local.to_3x3().inverted()@rig.matrix_world.to_3x3().inverted()@Vector((-.065*kick,0,-.035+bob))
   for n in fingers:
    joint=int(n.split('_')[1]);angle=([.35,.55,.45] if n.startswith('thumb') else [.9,1.15,.75])[joint-1]
    rig.pose.bones[n].rotation_quaternion=Quaternion((0,0,1),angle)
   rot('spine_03',(1,0,0),-.07*kick);rot('spine_01',(0,0,1),.10*jab-.12*cross)
   update()
   for s,sign in [('l',1),('r',-1)]:
    foot=restfeet[s].copy();foot.x=sign*.19;foot.y+=-.08 if s=='l' else .07
    if s=='l':foot=foot.lerp(Vector((.13,-.92,1.02)),kick)
    solve(rig,['thigh_'+s,'calf_'+s,'foot_'+s],foot,(sign*.22,-1,.55))
    p=rig.pose.bones['foot_'+s];m=p.matrix.copy();m=rig.data.bones[p.name].matrix_local.copy();m.translation=p.matrix.translation;p.matrix=m;update()
    amount=jab if s=='l' else cross
    target=Vector((sign*.23,-.31,1.40))
    target=target.lerp(Vector((sign*.12,-.73,1.43)),amount)
    solve(rig,['upperarm_'+s,'lowerarm_'+s,'hand_'+s],target,(sign*.52,-.13,1.02))
   for n in changed:
    p=rig.pose.bones[n];p.keyframe_insert('rotation_quaternion',frame=f,group=n);p.keyframe_insert('location',frame=f,group=n)
  action=rig.animation_data.action;action.name='Sample_'+label;action.use_fake_user=True;clips.append(action)
  scene.frame_set(1);build.export(rig,OUT/(label+'.fbx'),True);log('EXPORTED '+label)
 # A separate action stitches the three samples together for easy playback.
 rig.animation_data.action=None
 for i,action in enumerate(clips):
  for f in range(1,73):
   rig.animation_data.action=action;scene.frame_set(f);update()
   values={n:(rig.pose.bones[n].location.copy(),rig.pose.bones[n].rotation_quaternion.copy()) for n in changed}
   rig.animation_data.action=bpy.data.actions.get('Sample_Demo')
   for n,(loc,q) in values.items():
    p=rig.pose.bones[n];p.location=loc;p.rotation_quaternion=q
    p.keyframe_insert('location',frame=i*72+f,group=n);p.keyframe_insert('rotation_quaternion',frame=i*72+f,group=n)
   rig.animation_data.action.name='Sample_Demo'
 scene.frame_start=1;scene.frame_end=216;scene.frame_set(1)
 build.view.camera(scene,(2.5,-4,2.0),(0,-.15,.94),2.3)
 scene.render.engine='CYCLES';scene.cycles.samples=12
 scene.render.resolution_x=640;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG'
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 for frame in [1,94,181]:
  scene.frame_set(frame);scene.render.filepath=str(OUT/f'Pose_{frame}.png');bpy.ops.render.render(write_still=True)
 log('BUILD COMPLETE')
if __name__=='__main__':
 try:run()
 except:log(traceback.format_exc());raise
