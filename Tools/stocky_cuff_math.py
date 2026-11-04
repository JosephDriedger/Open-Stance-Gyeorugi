"""Small, tapered cuff clearance in canonical Blender metre coordinates."""
import numpy as np

def deform(points,axes,scale,bottom):
 points=np.asarray(points,dtype=float);axes=np.asarray(axes,dtype=float)
 side=np.argmin(abs(points[:,0,None]-axes[None,:,1,0]),axis=1)
 start=axes[side,0];end=axes[side,1]
 t=(points[:,2]-start[:,2])/(end[:,2]-start[:,2])
 center=start+(end-start)*t[:,None];direction=points-center;direction[:,2]=0
 length=np.linalg.norm(direction,axis=1);direction/=np.maximum(length[:,None],1e-12)
 factor=np.clip((bottom+.16*scale-points[:,2])/(.10*scale),0,1);factor=factor*factor*(3-2*factor)
 factor[length<=.01]=0
 return points+direction*(factor*.006*scale)[:,None]

def local_repair(points,world_matrix,axes,scale):
 points=np.asarray(points,dtype=float);matrix=np.asarray(world_matrix,dtype=float)
 a=matrix[:3,:3];translation=matrix[:3,3];inverse=np.linalg.inv(a)
 world=points@a.T+translation;bottom=world[:,2].min()
 fixed=deform(world,axes,scale,bottom);local=(fixed-translation)@inverse.T
 # Transform existing normals through the local deformation Jacobian.
 h=1e-5;columns=[]
 for axis in range(3):
  step=np.zeros(3);step[axis]=h
  columns.append((deform(world+step,axes,scale,bottom)-deform(world-step,axes,scale,bottom))/(2*h))
 jacobian=np.stack(columns,axis=2)
 local_jacobian=np.einsum('ij,njk,kl->nil',inverse,jacobian,a)
 normals=np.linalg.inv(local_jacobian).transpose(0,2,1)
 return local,normals

def transform_normals(normals,vertices,transforms):
 result=np.einsum('nij,nj->ni',transforms[np.asarray(vertices)],np.asarray(normals))
 length=np.linalg.norm(result,axis=1);assert np.all(length>1e-8)
 return result/length[:,None]
