"""Fit jacket panels around the hips and bake pose-dependent cloth contact."""
import bpy,sys,math,json,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));import rebuild_updated_characters as build
ROOT=Path(__file__).resolve().parents[2];S=ROOT/'Resources/Models/Animation/Samples';OUT=S/'HipFit';OUT.mkdir(exist_ok=True)
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def tree_for(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();tree=BVHTree.FromPolygons([o.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();return tree
def transform(r,n):return r.matrix_world@r.pose.bones[n].matrix@r.data.bones[n].matrix_local.inverted()@r.matrix_world.inverted()
def run():
 bpy.ops.wm.open_mainfile(filepath=str(S/'Medium_Sparring_Samples.blend'));scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];pants=bpy.data.objects['Pants']
 scene.frame_set(1);r.data.pose_position='REST';bpy.context.view_layer.update();tree=tree_for(pants)
 profile=json.loads((S/'BeltFit/fit.json').read_text())['profile_radius_m']
 def rad(a):
  t=(a%math.tau)/math.tau*len(profile);i=int(t);return profile[i]*(1-(t-i))+profile[(i+1)%len(profile)]*(t-i)
 # Close-fitting hip silhouette with only small wearing ease, not a flared skirt.
 parts=[]
 for name,lo,hi,cols in [('Jacket_Front_Left',-.035,math.pi/2+.025,25),('Jacket_Back',math.pi/2-.025,3*math.pi/2+.025,41),('Jacket_Front_Right',3*math.pi/2-.025,math.tau+.035,25)]:
  o=bpy.data.objects[name];o.shape_key_clear();verts=[];weights=[]
  for row in range(25):
   t=row/24;z=.980-.205*t
   for col in range(cols):
    u=col/(cols-1);a=lo+(hi-lo)*u;d=Vector((math.sin(a),-math.cos(a),0))
    # Cast inward from outside so crotch gaps cannot select an inner leg wall.
    origin=d*.4;origin.z=z;hit=tree.ray_cast(origin,-d,.4)[0]
    hiprad=hit.xy.length+.010 if hit else rad(a)+.006
    blend=min(1,max(0,(t-.10)/.45));blend=blend*blend*(3-2*blend)
    radius=rad(a)+.001+(hiprad-rad(a)-.001)*blend
    q=d*radius;q.z=z;verts.append(q)
    w=max(0,min(1,(t-.15)/.85));w=w*w*(3-2*w)
    front=max(0,math.cos(a));w*=.92 if front>0 else .50
    left=max(0,min(1,(q.x+.035)/.07));weights.append((w*left,w*(1-left)))
  # Smooth the fitted rest surface along each row to remove trouser micro-folds.
  for repeat in range(4):
   old=[v.copy() for v in verts]
   for row in range(3,25):
    for col in range(1,cols-1):
     i=row*cols+col;verts[i]=old[i]*.5+(old[i-1]+old[i+1])*.25
  assert len(verts)==len(o.data.vertices)
  for v,q in zip(o.data.vertices,verts):v.co=q
  o.vertex_groups.clear()
  groups={n:o.vertex_groups.new(name=n) for n in ['pelvis','thigh_l','thigh_r']}
  for i,(wl,wr) in enumerate(weights):
   for n,w in [('pelvis',1-wl-wr),('thigh_l',wl),('thigh_r',wr)]:
    if w>0:groups[n].add([i],w,'REPLACE')
  o.shape_key_add(name='Basis');parts.append((o,verts,weights,cols))
 r.data.pose_position='POSE';r.animation_data.action=bpy.data.actions['Sample_Front_Kick'];scene.frame_start=1;scene.frame_end=72
 report=[]
 for f in range(1,73):
  scene.frame_set(f);bpy.context.view_layer.update();tree=tree_for(pants);pelvis=transform(r,'pelvis');left=transform(r,'thigh_l');right=transform(r,'thigh_r');inv=pelvis.inverted()
  maximum=0
  for o,rest,weights,cols in parts:
   posed=[]
   for q,(wl,wr) in zip(rest,weights):posed.append((pelvis@q)*(1-wl-wr)+(left@q)*wl+(right@q)*wr)
   # Keep cloth just outside visible trousers, retaining its rounded hip shape.
   for repeat in range(3):
    old=[p.copy() for p in posed]
    if repeat:
     for row in range(4,24):
      for col in range(1,cols-1):
       i=row*cols+col;posed[i]=old[i]*.65+(old[i-1]+old[i+1]+old[i-cols]+old[i+cols])*.0875
    for i,p in enumerate(posed):
     if i<cols*3:continue
     hit,n,_,dist=tree.find_nearest(p)
     if hit is not None and dist<.14 and (p-hit).dot(n)<.007:
      target=hit+n*.009;maximum=max(maximum,(target-p).length);posed[i]=target
   k=o.shape_key_add(name=f'ClothBake_{f:02d}')
   for v,p,(wl,wr) in zip(k.data,posed,weights):
    skin=pelvis*(1-wl-wr)+left*wl+right*wr
    v.co=skin.inverted()@p
   for frame,value in [(0,0),(f-1,0),(f,1),(f+1,0),(74,0)]:k.value=value;k.keyframe_insert('value',frame=frame)
   k.value=0
   o['PreserveExportShapeKeys']=True
  report.append({'frame':f,'max_contact_correction_m':maximum})
  if f%12==0:log('BAKED '+str(f))
 # Existing belt-tail keys use the combined timeline; align them with this clip.
 for name in ['Belt_Tail_Left','Belt_Tail_Right']:
  a=bpy.data.objects[name].data.shape_keys.animation_data.action.copy();bpy.data.objects[name].data.shape_keys.animation_data.action=a
  fcs=list(a.fcurves) if hasattr(a,'fcurves') else [fc for l in a.layers for st in l.strips for bag in st.channelbags for fc in bag.fcurves]
  for fc in fcs:
   for p in fc.keyframe_points:p.co.x-=144;p.handle_left.x-=144;p.handle_right.x-=144
 scene.frame_set(1);build.view.camera(scene,(2.5,-4,2),(0,-.15,.94),2.3)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Front_Kick.blend'))
 for f in [1,18,26,35,45,60,72]:
  scene.frame_set(f)
  for angle,cam in [('Front',(1,-4,1.65)),('Side',(4,-.8,1.65))]:
   build.view.camera(scene,cam,(0,-.15,.93),1.8);scene.render.filepath=str(OUT/f'{angle}_{f}.png');bpy.ops.render.render(write_still=True)
 (OUT/'contact.json').write_text(json.dumps(report,indent=2));log('REVIEW READY')
try:run()
except:log(traceback.format_exc());raise
