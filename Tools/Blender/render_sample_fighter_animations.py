import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/Animation/Samples'
def log(s):
 with (OUT/'render.log').open('a') as f:f.write(str(s)+'\n')
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene
 frames=OUT/'Frames';frames.mkdir(exist_ok=True)
 for f in ([] if '--validate' in sys.argv else range(145 if '--kick-only' in sys.argv else 1,217,2)):
  scene.frame_set(f);scene.render.filepath=str(frames/f'{(f-1)//2:04d}.png')
  bpy.ops.render.render(write_still=True)
  if '--kick-only' in sys.argv:
   side=OUT/'SideFrames';side.mkdir(exist_ok=True)
   build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
   scene.render.filepath=str(side/f'{(f-145)//2:04d}.png');bpy.ops.render.render(write_still=True)
   build.view.camera(scene,(2.5,-4,2.0),(0,-.15,.94),2.3)
  log('FRAME '+str(f))
 reports=[]
 for name in ['Guard_Idle','Straight_Punches','Front_Kick']:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/(name+'.fbx')))
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1
  r=rigs[0];assert len(r.data.bones)==341 and r.animation_data.action
  action=r.animation_data.action;assert action.frame_range[1]-action.frame_range[0]>=70
  samples=[]
  for f in [1,22,37,47,72]:
   bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
   samples.append({n:list(r.matrix_world@r.pose.bones[n].matrix.translation) for n in ['pelvis','hand_l','hand_r','foot_l']})
  joint={'Guard_Idle':'pelvis','Straight_Punches':'hand_l','Front_Kick':'foot_l'}[name]
  assert any(sum((s[joint][i]-samples[0][joint][i])**2 for i in range(3))>1e-8 for s in samples[1:]),name
  reports.append({'clip':name,'bones':341,'frames':list(action.frame_range),'reimport_passed':True,'joint_samples':samples})
 (OUT/'validation.json').write_text(json.dumps(reports,indent=2))
 log('COMPLETE')
except:log(traceback.format_exc());raise
