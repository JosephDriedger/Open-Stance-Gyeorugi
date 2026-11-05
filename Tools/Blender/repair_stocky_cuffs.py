import bpy,sys,numpy as np
from mathutils import Vector
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stocky_cuff_math import local_repair,transform_normals

def configure(scene):
 o=bpy.data.objects.get('Pants')
 if not o:return False
 rig=next((m.object for m in o.modifiers if m.type=='ARMATURE' and m.object),None)
 if not rig or 'Stocky' not in rig.name:return False
 if o.get('CuffClearanceRevision')=='2026-10-30':return False
 axes=[[list(rig.matrix_world@rig.data.bones[b+'_'+side].head_local) for b in ('calf','foot')] for side in 'lr']
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 before=np.array([v.co[:] for v in o.data.vertices]);after,transforms=local_repair(before,np.array(o.matrix_world),axes,scale)
 delta=after-before;normal_values=None
 if o.data.has_custom_normals:
  normal_values=transform_normals([n.vector[:] for n in o.data.corner_normals],[l.vertex_index for l in o.data.loops],transforms)
 keys=o.data.shape_keys
 if keys:
  for key in keys.key_blocks:
   for v,d in zip(key.data,delta):v.co+=Vector(d)
  for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
 else:
  for v,p in zip(o.data.vertices,after):v.co=p
 o.data.update()
 if normal_values is not None:o.data.normals_split_custom_set(normal_values.tolist())
 o['CuffClearanceRevision']='2026-10-30'
 return {'vertices_changed':int(np.sum(np.linalg.norm(delta,axis=1)>1e-9)),'maximum_local_displacement':float(np.linalg.norm(delta,axis=1).max())}
