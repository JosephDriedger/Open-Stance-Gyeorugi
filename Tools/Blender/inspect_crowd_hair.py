import bpy
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/CrowdFaceRefinement/Tall/Crowd_Near.blend')
for o in bpy.context.scene.objects:
 if 'Pony' in o.name:print(o.name,tuple(o.location),len(o.data.vertices) if o.type=='MESH' else o.type,[(m.name,m.type) for m in o.modifiers])

from mathutils import Vector
for o in bpy.context.scene.objects:
 if o.type=='ARMATURE':o.data.pose_position='REST'
bpy.context.view_layer.update()
for o in bpy.context.scene.objects:
 if 'Pony' in o.name:
  vs=[o.matrix_world@v.co for v in o.data.vertices];print(o.name,'bounds',[(min(v[i] for v in vs),max(v[i] for v in vs)) for i in range(3)])
