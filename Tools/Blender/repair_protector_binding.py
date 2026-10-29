"""Prevent the white edge binding from dipping into the padded shell."""
from mathutils import Vector

def repair(scene):
 rows=[]
 for o in scene.objects:
  if o.type!='MESH' or not any(prefix in o.name for prefix in ['Smooth_Buckle_Back__','Quilted_Lace_Back__']):continue
  if not any(word in o.name for word in ['Bound_Hem','Bound_Upper_Edge','Rear_Wing_Binding']):continue
  if o.get('BindingClearanceRevision')=='2026-10-23':continue
  rig=next((m.object for m in o.modifiers if m.type=='ARMATURE' and m.object),None)
  if rig is None:raise RuntimeError('No binding rig: '+o.name)
  scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
  inverse=o.matrix_world.inverted().to_3x3()
  for v in o.data.vertices:
   p=o.matrix_world@v.co;delta=inverse@(Vector((p.x,p.y+.006*scale,0)).normalized()*.003*scale);v.co+=delta
   if o.data.shape_keys:
    for key in o.data.shape_keys.key_blocks:key.data[v.index].co+=delta
  o['BindingClearanceRevision']='2026-10-23';rows.append(o.name)
 return rows
