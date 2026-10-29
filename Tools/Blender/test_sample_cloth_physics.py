"""Actual cloth trial with pinned waistband and free skirt/belt tails."""
import bpy,sys,json,traceback,math,bmesh
from mathutils import Vector
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision');OUT.mkdir(exist_ok=True)
def log(s):
 with (OUT/'simulation.log').open('a') as f:f.write(str(s)+'\n')
def fabric(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
 bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.82
 bs.inputs['Specular IOR Level'].default_value=.23;bs.inputs['Sheen Weight'].default_value=.12
 uv=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=420;noise.inputs['Detail'].default_value=1.5
 l.new(uv.outputs['UV'],noise.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.00035
 l.new(noise.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],bs.inputs['Normal']);return m
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];r.animation_data.action=bpy.data.actions['Sample_Front_Kick']
 scene.frame_start=1;scene.frame_end=72;scene.frame_set(1)
 cotton=fabric('Dobok_White_Cotton',(.72,.735,.75));black=fabric('Belt_Black_Woven',(.012,.014,.017))
 for name in ['Jacket','Belt','Pants']:
  o=bpy.data.objects[name]
  if o.get('BeforeKickClothingWeights'):
   for v,weights in zip(o.data.vertices,json.loads(o['BeforeKickClothingWeights'])):
    for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
    for n,w in weights:(o.vertex_groups.get(n) or o.vertex_groups.new(name=n)).add([v.index],w,'REPLACE')
  if o.data.shape_keys:
   for k in list(o.data.shape_keys.key_blocks):
    if k.name.startswith('KickContact_'):o.shape_key_remove(k)
  if 'PreserveExportShapeKeys' in o:del o['PreserveExportShapeKeys']
  bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  o.data.materials.clear();o.data.materials.append(black if name=='Belt' else cotton)
  for p in o.data.polygons:p.material_index=0
  for m in o.modifiers:
   if m.type=='SOLIDIFY':m.thickness=(.0014 if name!='Belt' else .003)/max(o.matrix_world.to_scale());m.offset=0
 for side in 'lr':
  for bone,end,rad in [('thigh_'+side,'calf_'+side,.112),('calf_'+side,'foot_'+side,.075)]:
   a=r.matrix_world@r.data.bones[bone].head_local;b=r.matrix_world@r.data.bones[end].head_local
   center=(a+b)*.5;rotation=Vector((0,0,1)).rotation_difference(b-a)
   bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=1)
   proxy=bpy.context.object;proxy.name='Collision_'+bone
   for v in proxy.data.vertices:v.co=center+rotation@Vector((v.co.x*rad,v.co.y*rad,v.co.z*((b-a).length*.55)))
   proxy.vertex_groups.new(name=bone).add(list(range(len(proxy.data.vertices))),1,'REPLACE');proxy.modifiers.new('Body motion','ARMATURE').object=r
   proxy.modifiers.new('Cloth collider','COLLISION');proxy.collision.thickness_outer=.004;proxy.collision.thickness_inner=.001;proxy.collision.cloth_friction=.2;proxy.hide_render=True;proxy.display_type='WIRE'
 # Replace only the lower wrap and belt tails with regular cloth topology.
 for name in ['Jacket','Belt']:
  o=bpy.data.objects[name];o.shape_key_clear();bm=bmesh.new();bm.from_mesh(o.data)
  doomed=[v for v in bm.verts if (o.matrix_world@v.co).z<(.943 if name=='Belt' else .94) and (name=='Belt' or abs((o.matrix_world@v.co).x)<.28)]
  bmesh.ops.delete(bm,geom=doomed,context='VERTS');bm.to_mesh(o.data);bm.free()
 def meshpart(name,verts,faces,material):
  data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();o=bpy.data.objects.new(name,data);scene.collection.objects.link(o)
  data.materials.append(material)
  for p in data.polygons:p.use_smooth=True
  o.vertex_groups.new(name='pelvis').add(list(range(len(verts))),1,'REPLACE');o.modifiers.new('Body motion','ARMATURE').object=r
  o.modifiers.new('Fabric thickness','SOLIDIFY').thickness=.0015
  return o
 verts=[];faces=[];cols=65;rows=21
 for row in range(rows):
  t=row/(rows-1);z=.965-.285*t
  for col in range(cols):
   angle=.32+col/(cols-1)*(math.tau+.12)
   verts.append(((.205+.065*t)*math.sin(angle),-.012-(.19+.045*t)*math.cos(angle),z))
 for row in range(rows-1):
  for col in range(cols-1):
   if row>=12 and col in [12,43]:continue
   a=row*cols+col;faces.append((a+cols,a+1+cols,a+1,a))
 skirt=meshpart('Uniform_Wrap_Skirt',verts,faces,cotton)
 uv=skirt.data.uv_layers.new(name='UVMap')
 for p in skirt.data.polygons:
  for li in p.loop_indices:
   vi=skirt.data.loops[li].vertex_index;uv.data[li].uv=(vi%cols/(cols-1),vi//cols/(rows-1))
 for side,sign in [('Left',1),('Right',-1)]:
  verts=[];faces=[];cols=7;rows=25
  for row in range(rows):
   t=row/(rows-1)
   for col in range(cols):verts.append((sign*(.018+.024*t)+(col/(cols-1)-.5)*.042,-.241-.005*math.sin(t*math.pi),.964-(.29 if sign==1 else .25)*t))
  for row in range(rows-1):
   for col in range(cols-1):
    a=row*cols+col;faces.append((a,a+1,a+1+cols,a+cols))
  meshpart('Belt_Tail_'+side,verts,faces,black)
 for name in ['Uniform_Wrap_Skirt','Belt_Tail_Left','Belt_Tail_Right']:
  o=bpy.data.objects[name];group=o.vertex_groups.get('ClothPin') or o.vertex_groups.new(name='ClothPin')
  for v in o.data.vertices:
   p=o.matrix_world@v.co
   weight=max(0,min(1,(p.z-(.941 if name.startswith('Belt') else .935))/.016))
   group.add([v.index],weight,'REPLACE')
  cloth=o.modifiers.new('Cotton cloth dynamics','CLOTH');s=cloth.settings
  s.quality=20;s.mass=.18;s.tension_stiffness=80;s.compression_stiffness=45;s.shear_stiffness=25;s.bending_stiffness=.25 if name=='Uniform_Wrap_Skirt' else 1.2
  s.tension_damping=10;s.compression_damping=10;s.shear_damping=8;s.bending_damping=5;s.vertex_group_mass=group.name;s.pin_stiffness=1
  cloth.collision_settings.use_collision=True;cloth.collision_settings.distance_min=.006;cloth.collision_settings.collision_quality=6
  cloth.collision_settings.use_self_collision=False;cloth.collision_settings.self_distance_min=.003
  if '--no-contact' in sys.argv:
   cloth.collision_settings.use_collision=False;cloth.collision_settings.use_self_collision=False
  # Dynamics on the cloth surface, thickness afterwards.
  for m in list(o.modifiers):
   if m.type=='SOLIDIFY':
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_to_index(modifier=m.name,index=len(o.modifiers)-1)
  cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=72
 view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Cloth_Physics_Test.blend'))
 for f in range(1,73):
  scene.frame_set(f);bpy.context.view_layer.update()
  # Force evaluation every step, including non-rendered frames.
  for name in ['Uniform_Wrap_Skirt','Belt_Tail_Left','Belt_Tail_Right']:
   ev=bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();ev.to_mesh_clear()
  if f in [1,18,26,35,45,60,72]:
   scene.render.filepath=str(OUT/f'Physics_{f}.png');bpy.ops.render.render(write_still=True)
  if f%6==0:log('FRAME '+str(f))
 log('SIMULATION COMPLETE')
try:run()
except:log(traceback.format_exc());raise
