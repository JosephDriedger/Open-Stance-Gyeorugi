"""Uninstalled rest-fit experiment; preserve the source library."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT = review.ROOT
OUT = ROOT/'Resources/Models/FinalRefinement/StockyCalfClearance'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfWeights/Candidate.blend'))
s=bpy.context.scene; r=bpy.data.objects['RIG_Body_Stocky']; body=bpy.data.objects['Body']; pants=bpy.data.objects['Pants']
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices], [tuple(t.vertices) for t in body.data.loop_triangles], all_triangles=True)
axes=[(r.matrix_world@r.data.bones['calf_'+side].head_local,r.matrix_world@r.data.bones['foot_'+side].head_local) for side in 'lr']
changes=[]
for v in pants.data.vertices:
 p=pants.matrix_world@v.co
 if p.z>.48*scale: continue
 a,b=min(axes,key=lambda ab:abs(p.x-ab[1].x))
 center=a+(b-a)*((p.z-a.z)/(b.z-a.z)); direction=p-center; direction.z=0
 if direction.length<.01:continue
 direction.normalize()
 hit,normal,index,distance=tree.ray_cast(center,direction,.25*scale)
 if hit is None:continue
 current=(p-center).dot(direction)
 required=distance+.012*scale
 delta=max(0,required-current)
 if delta==0:continue
 offset=pants.matrix_world.inverted().to_3x3()@(direction*delta)
 if pants.data.shape_keys:
  for key in pants.data.shape_keys.key_blocks:key.data[v.index].co+=offset
 else:v.co+=offset
 changes.append(delta)
pants.data.update()
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
for label,side in [('Neutral','l'),('Front_Kick_L','l'),('Front_Kick_R','r'),('Side_Kick_L','l'),('Ankle_Flexed','l'),('Deep_Squat','l')]:
 review.audit.pose(r,label,scale)
 target=r.matrix_world@r.pose.bones['foot_'+side].matrix.translation+Vector((0,0,.065*scale))
 position=target+Vector((1 if side=='l' else -1,-.4,.2))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.4*scale,600,600)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'changes.json').write_text(json.dumps({'production_installed':False,'moved_vertices':len(changes),'maximum_rest_expansion_m':max(changes,default=0),'clearance_m':.012*scale},indent=2))
