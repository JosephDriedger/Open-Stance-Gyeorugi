import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/HipFit')
bpy.ops.wm.open_mainfile(filepath=str(P/'Front_Kick.blend'));r=bpy.data.objects['RIG_Body_Medium'];s=bpy.context.scene
report={'panel_weights':{},'support_foot_drift_m':0}
for name in ['Jacket_Front_Left','Jacket_Back','Jacket_Front_Right']:
 o=bpy.data.objects[name]
 assert all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in o.data.vertices)
 assert any(o.vertex_groups[g.group].name.startswith('thigh_') and g.weight>.2 for v in o.data.vertices for g in v.groups)
 report['panel_weights'][name]='normalized pelvis/thigh weights'
points=[]
for f in range(1,73):
 s.frame_set(f);bpy.context.view_layer.update();points.append(r.matrix_world@r.pose.bones['foot_r'].matrix.translation)
report['support_foot_drift_m']=max((p-points[0]).length for p in points)
assert report['support_foot_drift_m']<.002
for name in report['panel_weights']:
 o=bpy.data.objects[name];a=o.data.shape_keys.key_blocks['ClothBake_01'];b=o.data.shape_keys.key_blocks['ClothBake_72'];assert max((x.co-y.co).length for x,y in zip(a.data,b.data))<.002
report['jacket_loop_endpoint']='matched within 2 mm'
(P/'motion_validation.json').write_text(json.dumps(report,indent=2))
