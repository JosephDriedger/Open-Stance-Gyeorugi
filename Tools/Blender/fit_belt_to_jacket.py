import bpy,sys,math,json,traceback,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'Resources/Models/Animation/Samples';OUT=P/'BeltFit';OUT.mkdir(exist_ok=True)
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def run():
 bpy.ops.wm.open_mainfile(filepath=str(P/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];scene.frame_set(1);r.data.pose_position='REST';bpy.context.view_layer.update()
 shirt=bpy.data.objects['Jacket'];ev=shirt.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 tree=BVHTree.FromPolygons([shirt.matrix_world@v.co for v in mesh.vertices],[list(f.vertices) for f in mesh.polygons]);ev.to_mesh_clear()
 profile=[];cols=128
 for i in range(cols):
  a=math.tau*i/cols;d=Vector((math.sin(a),-math.cos(a),0));hit=tree.ray_cast(Vector((0,0,1.005)),d,.32)[0]
  assert hit is not None,(i,'missing jacket surface')
  profile.append(hit.xy.length)
 # Smooth only sub-centimeter irregularities, retaining the torso outline.
 profile=[sum(profile[(i+k)%cols] for k in [-2,-1,0,1,2])/5 for i in range(cols)]
 def radius(p):
  a=math.atan2(p.x,-p.y)%math.tau;t=a/math.tau*cols;i=int(t);return profile[i]*(1-(t-i))+profile[(i+1)%cols]*(t-i)
 band=bpy.data.objects['Belt_Waistband']
 for v in band.data.vertices:
  p=v.co;direction=Vector((p.x,p.y,0)).normalized();p.x,p.y=(direction*(radius(p)+.006)).xy
 # Shape a continuous, pelvis-bound waist under the belt. The source cut
 # edge is tucked behind the band; all baked panel states share this seam.
 invshirt=shirt.matrix_world.inverted()
 pelvis=shirt.vertex_groups.get('pelvis') or shirt.vertex_groups.new(name='pelvis')
 for v in shirt.data.vertices:
  q=shirt.matrix_world@v.co
  if abs(q.x)<.28 and q.z<1.055:
   t=max(0,min(1,(1.055-q.z)/.045));t=t*t*(3-2*t)
   d=Vector((q.x,q.y,0)).normalized();target=d*radius(q)
   q.x+=(target.x-q.x)*t;q.y+=(target.y-q.y)*t
   q.z=max(q.z,.968);v.co=invshirt@q
   old=[(g.group,g.weight) for g in v.groups]
   for index,w in old:shirt.vertex_groups[index].add([v.index],w*(1-t),'REPLACE')
   prior=next((w for index,w in old if index==pelvis.index),0)
   pelvis.add([v.index],prior*(1-t)+t,'REPLACE')
 for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  o=bpy.data.objects[name];basis=o.data.shape_keys.key_blocks[0]
  cols_panel=41 if name=='Jacket_Back' else 25
  lo,hi={'Jacket_Front_Left':(-.11,math.pi/2+.12),'Jacket_Back':(math.pi/2-.06,3*math.pi/2+.06),'Jacket_Front_Right':(3*math.pi/2-.12,math.tau+.08)}[name]
  assert len(basis.data)==cols_panel*25
  for key in o.data.shape_keys.key_blocks:
   for index,point in enumerate(key.data):
    row,col=divmod(index,cols_panel);a=lo+(hi-lo)*col/(cols_panel-1)
    t=max(0,min(1,(10-row)/5));t=t*t*(3-2*t)
    direction=Vector((math.sin(a),-math.cos(a),0))
    target=direction*(radius(direction)+.001+max(0,row-3)*.0026)
    target.z=.98-row*.011
    point.co=point.co.lerp(target,t)
  for v,p in zip(o.data.vertices,basis.data):v.co=p.co
 # Trousers must sit inside the jacket at the waist, not outside the belt.
 pants=bpy.data.objects['Pants'];inv=pants.matrix_world.inverted()
 pg=pants.vertex_groups.get('pelvis') or pants.vertex_groups.new(name='pelvis')
 data_sets=[k.data for k in pants.data.shape_keys.key_blocks] if pants.data.shape_keys else [pants.data.vertices]
 for data in data_sets:
  for v in data:
   q=pants.matrix_world@v.co;t=max(0,min(1,(q.z-.87)/.065));t=t*t*(3-2*t)
   if t:
    d=Vector((q.x,q.y,0)).normalized();rad=min(q.xy.length,radius(q)-.012)
    target=d*rad;q.x+=(target.x-q.x)*t;q.y+=(target.y-q.y)*t;v.co=inv@q
 for v in pants.data.vertices:
  q=pants.matrix_world@v.co;t=max(0,min(1,(q.z-.90)/.045))
  if t:
   old=[(g.group,g.weight) for g in v.groups]
   for index,w in old:pants.vertex_groups[index].add([v.index],w*(1-t),'REPLACE')
   prior=next((w for index,w in old if index==pg.index),0);pg.add([v.index],prior*(1-t)+t,'REPLACE')
 front=profile[0];knot=bpy.data.objects['Belt'];points=[knot.matrix_world@v.co for v in knot.data.vertices];center_y=(min(p.y for p in points)+max(p.y for p in points))/2;shift=-front-.014-center_y
 inv=knot.matrix_world.to_3x3().inverted();delta=inv@Vector((0,shift,0))
 for v in knot.data.vertices:v.co+=delta
 for name in ['Belt_Tail_Left','Belt_Tail_Right']:
  o=bpy.data.objects[name];basis=o.data.shape_keys.key_blocks[0];weights=[max(0,min(1,(v.co.z-.83)/.12)) for v in basis.data]
  target=-front-.020;root_y=sum(v.co.y for v in list(basis.data)[:7])/7;dy=target-root_y
  for key in o.data.shape_keys.key_blocks:
   for v,t in zip(key.data,weights):v.co.y+=dy*t*t*(3-2*t)
  for v,p in zip(o.data.vertices,basis.data):v.co=p.co
 r.data.pose_position='POSE';scene.frame_set(1);bpy.context.view_layer.update()
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 for f in [1,170,179,216]:
  scene.frame_set(f);build.view.camera(scene,(3,-1,1.55),(0,-.02,1.01),.83);scene.render.filepath=str(OUT/f'Waist_{f}.png');bpy.ops.render.render(write_still=True)
 (OUT/'fit.json').write_text(json.dumps({'profile_radius_m':profile,'band_clearance_m':.006,'knot_shift_y_m':shift},indent=2));log('REVIEW READY')
try:run()
except:log(traceback.format_exc());raise
