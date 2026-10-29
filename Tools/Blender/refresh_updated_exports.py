"""Refresh portable exports from finalized native files without rebuilding meshes."""
import bpy,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
def run(kind):
 d=b.OUT/kind
 for level in ['Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
  bpy.ops.wm.open_mainfile(filepath=str(d/(level+'.blend')));rig=bpy.data.objects['RIG_Body_'+kind]
  if level.startswith('Crowd'):
   b.export(rig,d/(level+'.fbx'))
   if level=='Crowd_Near':
    for clip in ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer','Crowd_Wave']:
     rig.animation_data.action=bpy.data.actions[clip];b.export(rig,d/(clip+'.fbx'),True)
  else:
   b.export(rig,d/(level+'_Sparring.fbx'))
   for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[key]=False
   b.refresh(rig);b.export(rig,d/(level+'_Dobok.fbx'))
   if level=='Gameplay_High':b.export(rig,d/f'OpenStance_{kind}_Mocap_Source.fbx')
 b.log(kind+' exports refreshed')
if __name__=='__main__':
 try:
  for kind in sys.argv[sys.argv.index('--')+1:]:
   run(kind)
   import check_updated_exports as check
   check.run(kind)
 except:b.log(traceback.format_exc());raise
