"""Rebuild the instep color transition with a continuous, portable UV texture."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardPanelRebuildV3';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyCalfFitReview/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
axes=[]
for side in 'lr':
 foot=r.matrix_world@r.data.bones['foot_'+side].head_local;ball=r.matrix_world@r.data.bones['ball_'+side].head_local
 forward=ball-foot;forward.z=0;forward.normalize();lateral=Vector((-forward.y,forward.x,0))
 axes.append((foot,forward,lateral,(ball-foot).dot(forward)))
length=sum(a[3] for a in axes)/2
n=1024;v,u=np.mgrid[0:n,0:n].astype(float);lateral=(u/(n-1)-.5)*.3*scale;along=(v/(n-1)-.25)*.3*scale
start=.03*scale;end=length-.02*scale;radius=.009*scale
qx=np.abs(lateral)-(.034*scale-radius);qy=np.abs(along-(start+end)/2)-((end-start)/2-radius)
distance=np.sqrt(np.maximum(qx,0)**2+np.maximum(qy,0)**2)+np.minimum(np.maximum(qx,qy),0)-radius
mask=np.clip(.5-distance/(.0006*scale),0,1)
pixels=np.ones((n,n,4),dtype=np.float32)
for c,(white,gray) in enumerate(zip((.79,.79,.80),(.065,.069,.077))):pixels[:,:,c]=white*(1-mask)+gray*mask
image=bpy.data.images.new('Footguard_Continuous_Instep',width=n,height=n,alpha=True)
image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(OUT/'Footguard_Instep_BaseColor.png');image.file_format='PNG';image.save();image.pack()
mat=bpy.data.materials.new('Footguard_Continuous_Instep');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.62
uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='UVInstepPanel'
tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='EXTEND';links.new(uvnode.outputs['UV'],tex.inputs['Vector']);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=450;noise.inputs['Detail'].default_value=2
links.new(uvnode.outputs['UV'],noise.inputs['Vector'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00012*scale;bump.inputs['Strength'].default_value=.35
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
rows=[]
for o in s.objects:
 if o.type!='MESH' or not o.name.startswith('FootGuards'):continue
 mesh=o.data
 if mesh.has_custom_normals:mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops))
 mesh.update()
 uv=mesh.uv_layers.get('UVInstepPanel') or mesh.uv_layers.new(name='UVInstepPanel');slot=len(mesh.materials);mesh.materials.append(mat)
 count=0
 for p in mesh.polygons:
  center=o.matrix_world@p.center;normal=o.matrix_world.to_3x3()@p.normal
  # Keep the existing sole finish; rebuild upper and side color boundaries.
  if normal.z<-.35 and center.z<.055*scale:continue
  p.material_index=slot;count+=1
  for li in p.loop_indices:
   point=o.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co
   foot,forward,lateral,length=min(axes,key=lambda a:abs(point.x-a[0].x))
   delta=point-foot;uv.data[li].uv=(delta.dot(lateral)/(.3*scale)+.5,(delta.dot(forward)-max(0,delta.z)*.85)/(.3*scale)+.25)
 rows.append({'object':o.name,'reassigned_faces':count})
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'geometry_changed':False,'weights_changed':False,'texture':image.filepath_raw,'changes':rows},indent=2))


