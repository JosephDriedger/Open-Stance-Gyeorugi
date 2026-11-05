import bpy, math, json, sys
from mathutils import Vector
from pathlib import Path
root=Path(bpy.path.abspath('//')).parent
out=root/'TrouserLimbContact';out.mkdir(exist_ok=True)
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];p=bpy.data.objects['Pants']
for o in s.objects:
 for m in o.modifiers:
  if m.type=='CLOTH' and o!=p:m.show_viewport=False;m.show_render=False
c=next(m for m in p.modifiers if m.type=='CLOTH')
collection=bpy.data.collections.new('Trouser limb contact');s.collection.children.link(collection)
for side in ('l','r'):
 for start,end,width in [('thigh','calf',.070),('calf','foot',.042)]:
  b=r.pose.bones[start+'_'+side];a=r.matrix_world@b.head;z=r.matrix_world@r.pose.bones[end+'_'+side].head
  bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,location=(a+z)/2)
  o=bpy.context.object;o.name='SIM_'+start+'_'+side;o.rotation_euler=(z-a).to_track_quat('Z','Y').to_euler();o.scale=(width,width,(z-a).length*.53)
  bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
  mat=o.matrix_world.copy();o.parent=r;o.parent_type='BONE';o.parent_bone=b.name;bpy.context.view_layer.update();o.matrix_world=mat
  collection.objects.link(o);o.hide_render=True;o.display_type='WIRE';o.modifiers.new('Contact','COLLISION');o.collision.thickness_outer=.002;o.collision.thickness_inner=.001
c.collision_settings.collection=collection;c.collision_settings.use_self_collision=False
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Trouser_Test.blend'),compress=True)
rows=[]
for f in range(1,96):
 s.frame_set(f);e=p.evaluated_get(bpy.context.evaluated_depsgraph_get());v=[(e.matrix_world@x.co).z for x in e.data.vertices];rows.append([f,min(v),max(v)])
(out/'cuff_heights.json').write_text(json.dumps(rows));print('CUFF SAMPLES',rows[::10],flush=True)
