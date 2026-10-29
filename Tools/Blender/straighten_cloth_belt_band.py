import bpy,bmesh,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision')
for filename in ['Medium_Cloth_Physics_Test.blend','Front_Kick_Cloth_Baked.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(p/filename));r=bpy.data.objects['RIG_Body_Medium'];o=bpy.data.objects['Belt']
 # Preserve the knot component; replace the uneven band with a flat ribbon.
 bm=bmesh.new();bm.from_mesh(o.data);unseen=set(bm.verts);remove=[]
 while unseen:
  todo=[unseen.pop()];part=[]
  while todo:
   v=todo.pop();part.append(v)
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in unseen:unseen.remove(w);todo.append(w)
  if len(part)!=178:remove+=part
 bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(o.data);bm.free()
 verts=[];faces=[];cols=128
 for row in range(3):
  for col in range(cols):
   a=math.tau*col/cols;verts.append((.209*math.sin(a),-.012-.208*math.cos(a),.948+row*.024))
 for row in range(2):
  for col in range(cols):
   j=(col+1)%cols;faces.append((row*cols+col,(row+1)*cols+col,(row+1)*cols+j,row*cols+j))
 mesh=bpy.data.meshes.new('Flat woven belt band');mesh.from_pydata(verts,[],faces);mesh.update();band=bpy.data.objects.new('Belt_Waistband',mesh);bpy.context.scene.collection.objects.link(band)
 mesh.materials.append(bpy.data.materials['Belt_Black_Woven'])
 for poly in mesh.polygons:poly.use_smooth=True
 uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   vi=mesh.loops[li].vertex_index;uv.data[li].uv=(vi%cols/cols,vi//cols*.05)
 band.vertex_groups.new(name='pelvis').add(list(range(len(verts))),1,'REPLACE');band.modifiers.new('Body motion','ARMATURE').object=r;band.modifiers.new('Woven thickness','SOLIDIFY').thickness=.003
 scene=bpy.context.scene;scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(p/filename))
 if filename.startswith('Front'):
  build.export(r,p/'Front_Kick_Cloth_Baked.fbx',True)
  for f in range(1,73,2):
   scene.frame_set(f);scene.render.filepath=str(p/'Frames'/f'{(f-1)//2:04d}.png');bpy.ops.render.render(write_still=True)
(p/'belt_complete.txt').write_text('Flat waist band rebuilt; original knot retained.\n')
