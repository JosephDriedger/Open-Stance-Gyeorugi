"""Deterministic position-based cloth: gravity, damping, stretch/shear/bend and body contact."""
import bpy,sys,json,math,traceback,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/UniformRebuild')
def log(s):
 with (OUT/'solver.log').open('a') as f:f.write(str(s)+'\n')
def matrix_points(m,p):
 a=np.array(m);return p@a[:3,:3].T+a[:3,3]
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Uniform_Simulation.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];names=json.loads((OUT/'cloth_objects.json').read_text())
 for o in list(bpy.data.objects):
  if o.name.startswith('Collision_'):bpy.data.objects.remove(o,do_unlink=True)
 cloth=[]
 for name in names:
  o=bpy.data.objects[name]
  for m in list(o.modifiers):
   if m.type=='CLOTH':o.modifiers.remove(m)
  cols=41 if name=='Jacket_Back' else 25 if name.startswith('Jacket') else 7;rows=len(o.data.vertices)//cols
  rest=np.array([v.co[:] for v in o.data.vertices]);pairs=[];stiff=[]
  for row in range(rows):
   for col in range(cols):
    for dr,dc,k in [(1,0,1),(0,1,1),(1,1,.8),(1,-1,.8),(2,0,.18),(0,2,.18)]:
     if 0<=row+dr<rows and 0<=col+dc<cols:pairs.append((row*cols+col,(row+dr)*cols+col+dc));stiff.append(k)
  pairs=np.array(pairs);a=pairs[:,0];b=pairs[:,1];length=np.linalg.norm(rest[b]-rest[a],axis=1)
  pinned=np.arange(len(rest))<cols*2;inv=np.ones(len(rest));inv[pinned]=0
  cloth.append(dict(name=name,o=o,rest=rest,a=a,b=b,length=length,stiff=np.array(stiff),pin=pinned,inv=inv,x=None,prev=None,snapshots=[]))
 def bone(n):return np.array((r.matrix_world@r.pose.bones[n].matrix.translation)[:])
 substeps=10;dt=1/(24*substeps)
 for f in range(1,121):
  for sub in range(substeps):
   scene.frame_set(f,subframe=sub/substeps);bpy.context.view_layer.update()
   transform=r.matrix_world@r.pose.bones['pelvis'].matrix@r.data.bones['pelvis'].matrix_local.inverted()@r.matrix_world.inverted()
   capsules=[]
   for s in 'lr':
    capsules.extend([(bone('thigh_'+s),bone('calf_'+s),.118),(bone('calf_'+s),bone('foot_'+s),.079)])
   pelvis=bone('pelvis');center=pelvis+np.array([0,-.005,.18]);radii=np.array([.18,.15,.245])
   for c in cloth:
    anchor=matrix_points(transform,c['rest']);pin=c['pin'];inv=c['inv'];a=c['a'];b=c['b']
    if c['x'] is None:c['x']=anchor.copy();c['prev']=anchor.copy()
    x=c['x'];previous=x.copy();x=x+(x-c['prev'])*.98+np.array([0,0,-9.81])*dt*dt;x[pin]=anchor[pin]
    for it in range(32):
     difference=x[b]-x[a];dist=np.linalg.norm(difference,axis=1);den=inv[a]+inv[b];den=np.maximum(den,1)
     corr=difference*((dist-c['length'])/np.maximum(dist,1e-8)*c['stiff']/den)[:,None]
     delta=np.zeros_like(x);count=np.zeros(len(x));np.add.at(delta,a,corr*inv[a,None]);np.add.at(delta,b,-corr*inv[b,None]);np.add.at(count,a,1);np.add.at(count,b,1)
     x+=delta/np.maximum(count,1)[:,None]*1.35;x[pin]=anchor[pin]
     for start,end,radius in capsules:
      axis=end-start;t=np.clip((x-start)@axis/(axis@axis),0,1);nearest=start+t[:,None]*axis;d=x-nearest;dist=np.linalg.norm(d,axis=1)
      inside=(dist<radius)&(~pin);x[inside]=nearest[inside]+d[inside]/np.maximum(dist[inside,None],1e-8)*radius
     q=(x-center)/radii;dist=np.linalg.norm(q,axis=1);inside=(dist<1)&(~pin)
     x[inside]=center+q[inside]/np.maximum(dist[inside,None],1e-8)*radii
    c['prev']=previous;c['x']=x
  if f>=49:
   inverse=transform.inverted()
   for c in cloth:c['snapshots'].append(matrix_points(inverse,c['x']))
  if f%12==0:log('SOLVED '+str(f))
 # Bake the collision-constrained fabric in local rest space, retaining body skinning.
 for c in cloth:
  o=c['o'];o.shape_key_add(name='Basis')
  for i,coords in enumerate(c['snapshots']):
   k=o.shape_key_add(name=f'ClothBake_{i+1:02d}');k.data.foreach_set('co',coords.astype(np.float32).ravel())
   for frame,value in [(0,0),(i,0),(i+1,1),(i+2,0),(74,0)]:k.value=value;k.keyframe_insert('value',frame=frame)
   k.value=0
  o['PreserveExportShapeKeys']=True
 r.animation_data.action=bpy.data.actions['Sample_Front_Kick'];scene.frame_start=1;scene.frame_end=72;scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Uniform_Corrected.blend'))
 for f in [1,18,26,35,45,60,72]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Solved_{f}.png');bpy.ops.render.render(write_still=True)
 log('REVIEW READY')
try:run()
except:log(traceback.format_exc());raise
