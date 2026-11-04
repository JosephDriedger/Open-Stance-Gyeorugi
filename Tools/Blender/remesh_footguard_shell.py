import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardRemeshReview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardShellRebuildV4/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
source=bpy.data.objects['FootGuards'];names=[g.name for g in source.vertex_groups];tree=KDTree(len(source.data.vertices));weights=[]
for v in source.data.vertices:tree.insert(v.co,v.index);weights.append([(g.group,g.weight) for g in v.groups])
tree.balance();temp=source.copy();temp.data=source.data.copy();s.collection.objects.link(temp);temp.animation_data_clear()
for m in list(temp.modifiers):temp.modifiers.remove(m)
temp.hide_set(False);temp.hide_viewport=False
bpy.context.view_layer.objects.active=temp;temp.select_set(True)
mod=temp.modifiers.new('Rebuild_shell_volume','REMESH');mod.mode='VOXEL';mod.voxel_size=.001*scale;mod.use_smooth_shade=True
with bpy.context.temp_override(object=temp,active_object=temp):bpy.ops.object.modifier_apply(modifier=mod.name)
temp.vertex_groups.clear()
for name in names:temp.vertex_groups.new(name=name)
maximum=0
for v in temp.data.vertices:
 point,index,distance=tree.find(v.co);maximum=max(maximum,distance)
 for group,w in weights[index]:temp.vertex_groups[group].add([v.index],w,'REPLACE')
uv=temp.data.uv_layers.new(name='UVInstepPanel');axes=[]
for side in 'lr':
 foot=r.matrix_world@r.data.bones['foot_'+side].head_local;ball=r.matrix_world@r.data.bones['ball_'+side].head_local;forward=ball-foot;forward.z=0;forward.normalize();axes.append((foot,forward,Vector((-forward.y,forward.x,0))))
for loop in temp.data.loops:
 p=temp.matrix_world@temp.data.vertices[loop.vertex_index].co;foot,forward,lateral=min(axes,key=lambda a:abs(p.x-a[0].x));d=p-foot
 uv.data[loop.index].uv=(d.dot(lateral)/(.3*scale)+.5,(d.dot(forward)-max(0,d.z)*.85)/(.3*scale)+.25)
newweights=[[(g.group,g.weight) for g in v.groups] for v in temp.data.vertices]
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];o.data=temp.data.copy();o.vertex_groups.clear()
 for group in names:o.vertex_groups.new(name=group)
 for i,row in enumerate(newweights):
  for group,w in row:o.vertex_groups[group].add([i],w,'REPLACE')
bpy.data.objects.remove(temp,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'weight_transfer':'nearest source vertex, experimental','maximum_transfer_distance_m':maximum,'vertices':len(source.data.vertices)},indent=2))
