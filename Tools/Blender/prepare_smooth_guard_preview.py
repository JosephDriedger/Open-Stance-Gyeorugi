import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardSmoothKickReview'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Animation_Test.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
s.render.fps=30;s.frame_set(35)
review.render(s,r,scale,OUT,'FullBody_Kick',(4,-.8,1.65),(0,-.25,.95),2.25,600,700)
s.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Animation_Test.blend'),compress=True)

