import bpy,json
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision')
bpy.ops.wm.open_mainfile(filepath=str(p/'Medium_Cloth_Physics_Test.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update();d={'gravity':list(scene.gravity),'units':scene.unit_settings.scale_length}
for name in ['Pants','Uniform_Wrap_Skirt']:
 o=bpy.data.objects[name]
 for mod in o.modifiers:
  if mod.type=='SOLIDIFY':mod.show_viewport=False
 bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();values=[]
 for face in m.polygons:
  c=o.matrix_world@face.center;n=o.matrix_world.to_3x3().inverted().transposed()@face.normal
  if .3<c.z<.5 and name=='Pants':values.append(n.x*(c.x-(.13 if c.x>0 else -.13))+n.y*c.y)
  elif name!='Pants':values.append(n.x*c.x+n.y*c.y)
 d[name]={'scale':list(o.scale),'normal_radial':sum(values)/len(values) if values else 0,'modifiers':[(x.name,x.type) for x in o.modifiers]};ev.to_mesh_clear()
(p/'diagnosis.json').write_text(json.dumps(d,indent=2))
