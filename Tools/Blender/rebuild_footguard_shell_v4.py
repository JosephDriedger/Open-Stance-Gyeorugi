"""Reconstruct both shell surfaces from the unmasked body, with explicit thickness."""
import bpy,sys,json,numpy as np
from pathlib import Path
from types import SimpleNamespace
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
import build_clean_gear as gear
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardShellRebuildV4';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardPanelRebuildV2/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];review.audit.pose(r,'Neutral',1)
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body=bpy.data.objects['Body'];copy=body.copy();copy.data=body.data.copy();s.collection.objects.link(copy)
for mod in list(copy.modifiers):copy.modifiers.remove(mod)
import bmesh
bm=bmesh.new();bm.from_mesh(copy.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0006*scale)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(copy.data);bm.free();copy.data.update()
B=gear.Surface(copy)
for i,name in enumerate(B.names):
 if name not in r.data.bones:B.W[:,i]=0
J={b.name:np.array(r.matrix_world@b.head_local) for b in r.data.bones}
parts=[];axes=[]
for side in 'lr':
 foot,ball=J['foot_'+side],J['ball_'+side];forward=gear.unit(np.array([ball[0]-foot[0],ball[1]-foot[1],0.]));lateral=np.array([-forward[1],forward[0],0.])
 along=(B.co-foot)@forward;length=(ball-foot)@forward;z=B.co[:,2]
 gate=(abs(B.co[:,0]-foot[0])<.10*scale)&(np.linalg.norm(B.co-foot,axis=1)<.30*scale)&(B.w('thigh',side=side)<.3)
 boundary=np.minimum(foot[2]+.075*scale-z,length+.004*scale-along)
 surf=gear.region(B,boundary,gate,100)
 part=gear.shell(surf,surf.faces,np.full(surf.n,.004*scale),np.full(surf.n,.0015*scale),role='binding',name='Sock_'+side,wall_role='binding',pos=surf.co,nrm=surf.ext_unit(B.smooth(B.nrm,8)))
 parts.append(part);axes.append((Vector(foot),Vector(forward),Vector(lateral),length))
combined=gear.merge_parts('FootGuards',parts)
combined.clean=lambda:gear.Part.clean(combined,merge=1e-7,min_area=1e-12)
new=gear.to_object(combined,B,r,s.collection,'Rebuilt')
# Limit weights to four deform bones, preserving normalized body-derived influences.
for v in new.data.vertices:
 weights=sorted([(g.group,g.weight) for g in v.groups],key=lambda x:-x[1])[:4];total=sum(w for _,w in weights)
 for g in list(v.groups):new.vertex_groups[g.group].remove([v.index])
 for index,w in weights:new.vertex_groups[index].add([v.index],w/total,'REPLACE')
mat=bpy.data.materials['Footguard_Continuous_Instep'];new.data.materials.append(mat)
uv=new.data.uv_layers.new(name='UVInstepPanel')
for p in new.data.polygons:
 for li in p.loop_indices:
  point=new.matrix_world@new.data.vertices[new.data.loops[li].vertex_index].co
  foot,forward,lateral,length=min(axes,key=lambda a:abs(point.x-a[0].x));delta=point-foot
  uv.data[li].uv=(delta.dot(lateral)/(.3*scale)+.5,(delta.dot(forward)-max(0,delta.z)*.85)/(.3*scale)+.25)
names=[g.name for g in new.vertex_groups];weights=[[(g.group,g.weight) for g in v.groups] for v in new.data.vertices];rows=[]
for name in ('FootGuards','FootGuards_PaddedInstep'):
 old=bpy.data.objects[name];assert not old.data.shape_keys,'Need explicit shape-key transfer'
 old_count=len(old.data.vertices);old.data=new.data.copy()
 # The new mesh is in world coordinates; transform to the existing object space.
 old.data.transform(old.matrix_world.inverted())
 old.vertex_groups.clear()
 for group in names:old.vertex_groups.new(name=group)
 for index,entries in enumerate(weights):
  for group,weight in entries:old.vertex_groups[group].add([index],weight,'REPLACE')
 assert all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in old.data.vertices)
 rows.append({'object':name,'old_vertices':old_count,'new_vertices':len(old.data.vertices),'faces':len(old.data.polygons)})
bpy.data.objects.remove(new,do_unlink=True);bpy.data.objects.remove(copy,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'inner_offset_m':.0015*scale,'outer_offset_m':.004*scale,'changes':rows},indent=2))


