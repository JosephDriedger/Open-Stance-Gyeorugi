import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardVariantReview'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Candidate.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r.animation_data.action=None;scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
review.audit.pose(r,'Neutral',scale);s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,-.045*scale,0));position=target+Vector((.65,-.5,.7))*scale
for style,label in [(0,'Standard'),(1,'Padded')]:
 r['FootGuardsStyle']=style;review.build.refresh(r)
 assert bpy.data.objects['FootGuards'].hide_render==bool(style)
 assert bpy.data.objects['FootGuards_PaddedInstep'].hide_render==(not bool(style))
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.36*scale,600,600)
