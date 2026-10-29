import bpy
bpy.ops.mesh.primitive_cube_add();o=bpy.context.object;m=o.modifiers.new('test','SOFT_BODY');print([(p.identifier,p.type) for p in m.settings.bl_rna.properties]);print('CLOTH',[(p.identifier,p.type) for p in o.modifiers.new('cloth','CLOTH').settings.bl_rna.properties if 'pin' in p.identifier])
