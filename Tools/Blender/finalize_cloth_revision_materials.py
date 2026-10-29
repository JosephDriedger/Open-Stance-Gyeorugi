import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision')
def material(name,base):
 m=bpy.data.materials[name];m['PortableFabric']=True;n=m.node_tree.nodes;l=m.node_tree.links
 n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
 bs.inputs['Specular IOR Level'].default_value=.23;bs.inputs['Sheen Weight'].default_value=.12
 uv=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(12,12,12);l.new(uv.outputs['UV'],mapping.inputs['Vector'])
 for filename,socket,noncolor in [(base,'Base Color',False),('Cotton_Roughness','Roughness',True),('Cotton_Normal','Normal',True)]:
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/'Textures'/(filename+'.png')),check_existing=True)
  if noncolor:t.image.colorspace_settings.name='Non-Color'
  t.image.pack();l.new(mapping.outputs['Vector'],t.inputs['Vector'])
  if socket=='Normal':
   normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.4;l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
  else:l.new(t.outputs['Color'],bs.inputs[socket])
for filename in ['Medium_Cloth_Physics_Test.blend','Front_Kick_Cloth_Baked.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/filename));material('Dobok_White_Cotton','Cotton_BaseColor');material('Belt_Black_Woven','Belt_BaseColor')
 scene=bpy.context.scene;scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/filename))
 if filename.startswith('Front'):
  build.export(bpy.data.objects['RIG_Body_Medium'],OUT/'Front_Kick_Cloth_Baked.fbx',True)
  # Re-render the baked simulation with the final portable texture maps.
  for f in range(1,73,2):
   scene.frame_set(f);scene.render.filepath=str(OUT/'Frames'/f'{(f-1)//2:04d}.png');bpy.ops.render.render(write_still=True)
  build.view.camera(scene,(1.4,-2,1.55),(0,-.05,1.13),.85)
  scene.frame_set(1);scene.render.filepath=str(OUT/'Fabric_Closeup.png');bpy.ops.render.render(write_still=True)
(OUT/'materials_complete.txt').write_text('Packed albedo, roughness and normal maps; FBX re-exported.\n')
