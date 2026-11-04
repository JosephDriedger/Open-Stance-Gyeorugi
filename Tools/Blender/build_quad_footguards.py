"""Clean swept sock shells fitted to the unmasked body; experimental delivery."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/FootguardQuadRebuild';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardPanelRebuildV2/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
body=bpy.data.objects['Body'];body.data.calc_loop_triangles();points=[body.matrix_world@v.co for v in body.data.vertices];tris=[tuple(t.vertices) for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(points,tris,all_triangles=True)
weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups if body.vertex_groups[g.group].name in r.data.bones} for v in body.data.vertices]
verts=[];faces=[];axes=[];misses=0;N=48;K=64
for side in 'lr':
 foot=r.matrix_world@r.data.bones['foot_'+side].head_local;ball=r.matrix_world@r.data.bones['ball_'+side].head_local
 forward=ball-foot;forward.z=0;length=forward.length;forward.normalize();lat=Vector((-forward.y,forward.x,0));axes.append((foot,forward,lat))
 # A quarter ellipse turns the forefoot tube upward into the ankle.
 centers=[];directions=[];radii=np.zeros((N,K))
 for i in range(N):
  t=i/(N-1);angle=t*math.pi/2
  center=foot+forward*((length-.006*scale)*(1-math.sin(angle)));center.z=.035*scale+(foot.z+.075*scale-.035*scale)*(1-math.cos(angle));centers.append(center)
  tangent=-forward*((length-.006*scale)*math.cos(angle))+Vector((0,0,(foot.z+.075*scale-.035*scale)*math.sin(angle)));tangent.normalize();up=lat.cross(tangent).normalized()
  row=[]
  for j in range(K):
   a=2*math.pi*j/K;direction=lat*math.cos(a)+up*math.sin(a);row.append(direction)
   hit,normal,index,distance=tree.ray_cast(center,direction,.16*scale)
   if hit is None:
    misses+=1;distance=1/math.sqrt((math.cos(a)/(.05*scale))**2+(math.sin(a)/(.03*scale))**2)
   radii[i,j]=distance
  directions.append(row)
 # Smooth the envelope while retaining measured body clearance.
 smooth=radii.copy()
 for iteration in range(16):
  neighbors=(np.roll(smooth,1,1)+np.roll(smooth,-1,1)+np.vstack((smooth[:1],smooth[:-1]))+np.vstack((smooth[1:],smooth[-1:])))/4
  smooth=.5*smooth+.5*neighbors
 outer=np.maximum(smooth,radii)+.004*scale
 base=len(verts)
 for layer in range(2):
  for i in range(N):
   for j in range(K):verts.append(centers[i]+directions[i][j]*(outer[i,j]-(.002*scale if layer else 0)))
 def index(layer,i,j):return base+layer*N*K+i*K+j%K
 for layer in range(2):
  for i in range(N-1):
   for j in range(K):
    face=(index(layer,i,j),index(layer,i,j+1),index(layer,i+1,j+1),index(layer,i+1,j));faces.append(face if layer==0 else tuple(reversed(face)))
 for i in (0,N-1):
  for j in range(K):
   face=(index(0,i,j),index(1,i,j),index(1,i,j+1),index(0,i,j+1));faces.append(face if i==0 else tuple(reversed(face)))
mesh=bpy.data.meshes.new('Clean_quad_sock');mesh.from_pydata(verts,[],faces);mesh.update()
import bmesh
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
mesh.materials.append(bpy.data.materials['Footguard_Continuous_Instep']);uv=mesh.uv_layers.new(name='UVInstepPanel')
for p in mesh.polygons:
 p.use_smooth=True
 for li in p.loop_indices:
  point=mesh.vertices[mesh.loops[li].vertex_index].co;foot,forward,lat=min(axes,key=lambda a:abs(point.x-a[0].x));d=point-foot
  uv.data[li].uv=(d.dot(lat)/(.3*scale)+.5,(d.dot(forward)-max(0,d.z)*.85)/(.3*scale)+.25)
newweights=[]
for point in verts:
 q,n,ti,d=tree.find_nearest(point);ids=tris[ti];a,b,c=[points[i] for i in ids];u=b-a;v=c-a;w=q-a;den=u.dot(u)*v.dot(v)-u.dot(v)**2
 if abs(den)<1e-18:factors=[1,0,0]
 else:
  y=(v.dot(v)*w.dot(u)-u.dot(v)*w.dot(v))/den;z=(u.dot(u)*w.dot(v)-u.dot(v)*w.dot(u))/den;factors=[max(0,1-y-z),max(0,y),max(0,z)]
 mixed={}
 for i,factor in zip(ids,factors):
  for bone,weight in weights[i].items():mixed[bone]=mixed.get(bone,0)+factor*weight
 mixed=sorted(mixed.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in mixed);newweights.append([(bone,w/total) for bone,w in mixed])
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];o.data=mesh.copy();o.data.transform(o.matrix_world.inverted());o.vertex_groups.clear();groups={}
 for i,row in enumerate(newweights):
  for bone,w in row:
   if bone not in groups:groups[bone]=o.vertex_groups.new(name=bone)
   groups[bone].add([i],w,'REPLACE')
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
for label in ['Neutral','Front_Kick_L','Side_Kick_L','Ankle_Extended']:
 review.audit.pose(r,label,scale);target=r.matrix_world@r.pose.bones['foot_l'].matrix.translation+Vector((0,0,.05*scale));position=target+Vector((1,-.6,.3))*scale
 review.render(s,r,1,OUT,label,tuple(position),tuple(target),.42*scale,600,600)
review.audit.pose(r,'Neutral',scale);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'vertices_per_pair':len(verts),'quads_per_pair':len(faces),'ray_misses':misses,'ray_count':2*N*K},indent=2))
