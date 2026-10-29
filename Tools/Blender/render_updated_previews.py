"""Render the rebuilt native profiles and crowd actions for visual review."""
import bpy,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
def render(kind):
 d=b.OUT/kind
 for level in ['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
  bpy.ops.wm.open_mainfile(filepath=str(d/(level+'.blend')));scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_'+kind]
  scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
  b.view.camera(scene,(.8*scale,-2*scale,1.55*scale),(0,0,.91*scale),2.06*scale)
  scene.render.resolution_x=720;scene.render.resolution_y=900;scene.render.resolution_percentage=100
  if hasattr(scene,'cycles'):scene.cycles.samples=16
  scene.render.filepath=str(d/(level+'.png'));bpy.ops.render.render(write_still=True)
  if level=='Preview':
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[prop]=True
   b.refresh(rig);scene.render.filepath=str(d/'Updated_Sparring.png');bpy.ops.render.render(write_still=True)
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[prop]=False
   b.refresh(rig);b.view.camera(scene,(.43*scale,-1*scale,1.77*scale),(0,-.003*scale,1.57*scale),.52*scale)
   scene.render.filepath=str(d/'Portrait.png');bpy.ops.render.render(write_still=True)
  if level=='Crowd_Near':
   for clip in ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer','Crowd_Wave']:
    rig.animation_data.action=bpy.data.actions[clip];scene.frame_set(16);bpy.context.view_layer.update()
    scene.render.filepath=str(d/(clip+'.png'));bpy.ops.render.render(write_still=True)
 b.log(kind+' render review complete')
if __name__=='__main__':
 try:
  for kind in sys.argv[sys.argv.index('--')+1:]:render(kind)
 except:b.log(traceback.format_exc());raise
