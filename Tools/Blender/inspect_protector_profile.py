import bpy
bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/CharacterSuite/Medium/Gameplay_High.blend')
o=bpy.data.objects['Quilted_Lace_Back__Padded_Torso_Shell']
for z in [1.,1.03,1.06,1.09,1.12,1.15,1.18,1.21,1.24]:
 p=[o.matrix_world@v.co for v in o.data.vertices];q=[v.y for v in p if abs(v.x)<.03 and abs(v.z-z)<.015 and v.y<0]
 print(z,min(q) if q else None,max(q) if q else None)
