import bpy,sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import extend_garment_repairs as base
from fitted_belt_physics import configure
ROOT=a.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/BodyPhysics';OUT.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:]
clip='Front_Kick'
thin=False
while args and '=' in args[0]:
 key,value=args.pop(0).split('=',1)
 if key=='clip':clip=value
 elif key=='contact':assert value=='thin';thin=True
 else:raise ValueError(key)
if thin:OUT=OUT.with_name('BodyPhysicsThin');OUT.mkdir(exist_ok=True)
for kind in args:
 folder=kind if clip=='Front_Kick' else kind+'_'+clip
 out=OUT/folder;out.mkdir(exist_ok=True)
 source=ROOT/'Resources/Models/Animation'/('OpenStance_'+kind+'_Animation.blend')
 source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];before=base.signature(r)
 sample='Front_Kick.blend' if clip=='Front_Kick' else 'Medium_Sparring_Samples.blend'
 with bpy.data.libraries.load(str(ROOT/'Resources/Models/Animation/Samples'/sample),link=False) as (available,loaded):
  assert 'Sample_'+clip in available.actions,available.actions
  loaded.actions=['Sample_'+clip]
 action=loaded.actions[0];action.name='Physics_Test_'+clip+'_'+kind
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 for curve in base.curves(action):
  if curve.data_path.endswith('.location'):
   for k in curve.keyframe_points:k.co.y*=scale;k.handle_left.y*=scale;k.handle_right.y*=scale
 r.animation_data_create();r.animation_data.action=action
 if action.slots:r.animation_data.action_slot=action.slots[0]
 for track in r.animation_data.nla_tracks:track.mute=True
 for prop in ['Wear_Jacket','Wear_Pants','Wear_Helmet','Wear_Protector','Wear_Hair']:r[prop]=True
 if thin:
  for prop in ['Wear_Gloves','Wear_FootGuards']:r[prop]=True
 r['JacketStyle']=0;r['BlenderCloth']=False;r.update_tag();s.frame_set(2);s.frame_set(1);bpy.context.view_layer.update()
 setup=configure(s,r,(.002,.005) if thin else (.005,.018));assert before==base.signature(r)
 s.frame_start=1;s.frame_end=144;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 measurements=[];rotations=[]
 for frame in range(1,145):
  s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
  if frame in [1,18,35,48]:rotations.append(tuple(r.pose.bones['thigh_l' if clip=='Front_Kick' else 'upperarm_l'].matrix.to_quaternion()))
  for name in ['Belt_Tail_Left','Belt_Tail_Right','Pants','Jacket_Front_Left','Jacket_Front_Right']:
   o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();points=[o.matrix_world@v.co for v in me.vertices]
   assert all(math.isfinite(x) and abs(x)<5 for p in points for x in p),(kind,frame,name)
   if name.startswith('Belt') and frame in [1,35,72,144]:measurements.append({'object':name,'frame':frame,'height_m':max(p.z for p in points)-min(p.z for p in points)})
   ev.to_mesh_clear()
  if frame in [1,26,35,72,144]:
   a.render(s,r,scale,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,640,720)
   a.render(s,r,scale,out,'Side_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,640,720)
  with (out/'progress.log').open('a') as f:f.write(str(frame)+'\n')
 assert len(set(rotations))>1,(kind,'Action did not animate the tested limb')
 s.frame_set(1);s['ValidationStatus']='Experimental body-proportion physics test; requires visual review.'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/('SecondaryCloth_'+folder+'_Wrap.blend')),compress=True)
 (out/'validation.json').write_text(json.dumps({'clip':clip,'finite':True,'frames':144,'rig_preserved':before==base.signature(r),'rig_bones':len(r.data.bones),'source':str(source),'source_sha256':source_sha,'full_sparring_gear':thin,'setup':setup,'measurements':measurements,'production_installed':False},indent=2))
 print('BODY_PHYSICS_COMPLETE '+kind,flush=True)
