"""Tailored independent wrap panels; world-space garment collision; settled cloth."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Resources/Models/Animation/Samples/UniformRebuild';OUT.mkdir(exist_ok=True)
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def curves(a):
 if hasattr(a,'fcurves'):return list(a.fcurves)
 return [fc for layer in a.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'ClothRevision/Front_Kick_Cloth_Baked.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];original=bpy.data.actions['Sample_Front_Kick']
 settled=original.copy();settled.name='Front_Kick_With_Settle'
 for fc in curves(settled):
  for k in fc.keyframe_points:k.co.x+=48;k.handle_left.x+=48;k.handle_right.x+=48
 r.animation_data.action=settled;scene.frame_start=1;scene.frame_end=120;scene.frame_set(1)
 for o in list(bpy.data.objects):
  if o.name.startswith(('Uniform_Wrap_Skirt','Belt_Tail_','Collision_')):bpy.data.objects.remove(o,do_unlink=True)
 # Export the actual trouser surface to world coordinates before adding collision.
 pants=bpy.data.objects['Pants'];solids=[m for m in pants.modifiers if m.type=='SOLIDIFY']
 for m in solids:m.show_viewport=False
 positions=[];faces=None
 for f in range(1,121):
  scene.frame_set(f);bpy.context.view_layer.update();ev=pants.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
  positions.append([pants.matrix_world@v.co for v in mesh.vertices])
  if faces is None:faces=[list(p.vertices) for p in mesh.polygons]
  ev.to_mesh_clear()
 for m in solids:m.show_viewport=True
 data=bpy.data.meshes.new('WorldSpace_Pants_Contact');data.from_pydata(positions[0],[],faces);data.update();proxy=bpy.data.objects.new('Collision_Trousers',data);scene.collection.objects.link(proxy)
 proxy.shape_key_add(name='Basis')
 for i,coords in enumerate(positions):
  k=proxy.shape_key_add(name=f'Pose_{i+1:03d}')
  for v,p in zip(k.data,coords):v.co=p
  for f,value in [(0,0),(i,0),(i+1,1),(i+2,0),(122,0)]:k.value=value;k.keyframe_insert('value',frame=f)
  k.value=0
 proxy.modifiers.new('World space cloth contact','COLLISION');proxy.collision.thickness_outer=.003;proxy.collision.thickness_inner=.001;proxy.collision.cloth_friction=.5;proxy.hide_render=True;proxy.display_type='WIRE'
 log('World-space trouser collider ready')
 def part(name,verts,faces,uvs,mat):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
  mesh.materials.append(bpy.data.materials[mat]);uv=mesh.uv_layers.new(name='UVMap')
  for p in mesh.polygons:
   p.use_smooth=True
   for li in p.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
  o.vertex_groups.new(name='pelvis').add(list(range(len(verts))),1,'REPLACE');o.modifiers.new('Waist attachment','ARMATURE').object=r
  pin=o.vertex_groups.new(name='ClothPin')
  for v in mesh.vertices:pin.add([v.index],max(0,min(1,(v.co.z-.935)/.018)),'REPLACE')
  cloth=o.modifiers.new('Woven cloth simulation','CLOTH');s=cloth.settings;s.quality=24;s.mass=.2;s.tension_stiffness=100;s.compression_stiffness=70;s.shear_stiffness=45;s.bending_stiffness=.45 if name.startswith('Jacket') else 1.0
  s.tension_damping=12;s.compression_damping=12;s.shear_damping=8;s.bending_damping=6;s.vertex_group_mass=pin.name;s.pin_stiffness=1
  cloth.collision_settings.use_collision=True;cloth.collision_settings.distance_min=.004;cloth.collision_settings.collision_quality=8;cloth.collision_settings.use_self_collision=False
  cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=120
  o.modifiers.new('Fabric thickness','SOLIDIFY').thickness=.0014 if name.startswith('Jacket') else .0025
  return o
 names=[]
 for name,lo,hi in [('Jacket_Front_Left',-.11,math.pi/2+.12),('Jacket_Back',math.pi/2-.06,3*math.pi/2+.06),('Jacket_Front_Right',3*math.pi/2-.12,math.tau+.08)]:
  cols=41 if name=='Jacket_Back' else 25;rows=25;verts=[];faces=[];uvs=[]
  for row in range(rows):
   t=row/(rows-1)
   for col in range(cols):
    u=col/(cols-1);a=lo+(hi-lo)*u
    verts.append(((.219+.04*t)*math.sin(a),-.012-(.206+.025*t)*math.cos(a),.966-.266*t));uvs.append((u*.5,t*.5))
  for row in range(rows-1):
   for col in range(cols-1):
    a=row*cols+col;faces.append((a+cols,a+cols+1,a+1,a))
  part(name,verts,faces,uvs,'Dobok_White_Cotton');names.append(name)
 for name,sign,length in [('Belt_Tail_Left',1,.28),('Belt_Tail_Right',-1,.245)]:
  verts=[];faces=[];uvs=[];cols=7;rows=29
  for row in range(rows):
   t=row/(rows-1)
   for col in range(cols):
    u=col/(cols-1);verts.append((sign*(.02+.025*t)+(u-.5)*.042,-.25-.006*t,.966-length*t));uvs.append((u*.08,t*.5))
  for row in range(rows-1):
   for col in range(cols-1):
    a=row*cols+col;faces.append((a,a+1,a+cols+1,a+cols))
  part(name,verts,faces,uvs,'Belt_Black_Woven');names.append(name)
 scene.frame_set(1);view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Uniform_Simulation.blend'))
 (OUT/'cloth_objects.json').write_text(json.dumps(names))
 for f in range(1,121):
  scene.frame_set(f);bpy.context.view_layer.update()
  for name in names:
   ev=bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();ev.to_mesh_clear()
  if f in [49,66,74,83,93,108,120]:
   scene.render.filepath=str(OUT/f'Review_{f-48}.png');bpy.ops.render.render(write_still=True)
  if f%12==0:log('SIM '+str(f))
 log('REVIEW READY')
try:run()
except:log(traceback.format_exc());raise
