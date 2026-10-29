import bpy,json
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/Front_Kick.blend')
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=bpy.data.objects[name]
 print(name,'MODIFIERS',[(m.name,m.type) for m in o.modifiers])
 print('GROUPS',[(g.name,len([v for v in o.data.vertices if any(w.group==g.index and w.weight>.001 for w in v.groups)])) for g in o.vertex_groups])
 print('KEYS',[(k.name,k.value) for k in o.data.shape_keys.key_blocks])
 print('DRIVERS',[(d.data_path,d.driver.expression) for d in o.data.shape_keys.animation_data.drivers])
 print('POSE',[(b.name,list(b.rotation_euler)) for b in bpy.data.objects['RIG_Body_Medium'].pose.bones if 'belt' in b.name.lower()])
