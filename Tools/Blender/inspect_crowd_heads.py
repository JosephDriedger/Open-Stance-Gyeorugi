import bpy
for level in ['Gameplay_Far','Crowd_Near','Crowd_Far']:
 bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/CharacterSuite/Medium/'+level+'.blend');o=bpy.data.objects['Head']
 print(level,'MATS',[(i,m.name if m else None) for i,m in enumerate(o.data.materials)],'mods',[(m.name,m.type) for m in o.modifiers]);print('groups',len(o.vertex_groups),'eyes',[(o.name,len(o.data.vertices)) for o in bpy.data.objects if o.type=='MESH' and ('eye' in o.name.lower())][:10])
