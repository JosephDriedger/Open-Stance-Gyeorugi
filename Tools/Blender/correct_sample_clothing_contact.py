import bpy,sys,json,math,traceback
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
def ramp(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def run():
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];objects=[bpy.data.objects[n] for n in ['Jacket','Belt']]
 r.animation_data.action=bpy.data.actions['Sample_Demo']
 for o in objects:
  original=json.loads(o['BeforeKickClothingWeights'])
  for v,weights in zip(o.data.vertices,original):
   for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
   for n,w in weights:(o.vertex_groups.get(n) or o.vertex_groups.new(name=n)).add([v.index],w,'REPLACE')
  if o.data.shape_keys:
   for key in list(o.data.shape_keys.key_blocks):
    if key.name.startswith('KickContact_'):o.shape_key_remove(key)
  else:o.shape_key_add(name='Basis')
  o['PreserveExportShapeKeys']=True
  o['KickCorrection']='Baked sample-specific cloth contact; 341-bone body skeleton unchanged.'
 for f in range(1,73):
  scene.frame_set(144+f);bpy.context.view_layer.update()
  load=ramp(12,26,f)*(1-ramp(52,66,f))
  if load<.001:continue
  deps=bpy.context.evaluated_depsgraph_get();pants=bpy.data.objects['Pants'];ev=pants.evaluated_get(deps);pm=ev.to_mesh()
  tree=BVHTree.FromPolygons([pants.matrix_world@v.co for v in pm.vertices],[list(p.vertices) for p in pm.polygons]);ev.to_mesh_clear()
  for o in objects:
   solids=[m for m in o.modifiers if m.type=='SOLIDIFY']
   for m in solids:m.show_viewport=False
   bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
   world=[o.matrix_world@v.co for v in mesh.vertices];ev.to_mesh_clear()
   assert len(world)==len(o.data.vertices)
   delta=[];allowed=[]
   for v,p in zip(o.data.vertices,world):
    rest=o.matrix_world@v.co
    strength=(1-ramp(.96,1.03,rest.z))*(1-ramp(-.02,.10,rest.y))*ramp(-.18,-.07,rest.x)
    allowed.append(strength)
    dy=-max(0,.97-rest.z)*.9*load*strength
    pos=p+Vector((0,dy,0));hit=tree.ray_cast(Vector((pos.x,pos.y,1.45)),Vector((0,0,-1)),1.1)[0]
    dz=0
    if hit and hit.z>.65:dz=max(0,hit.z+(.042 if o.name=='Belt' else .021)-p.z)*load*strength
    delta.append(Vector((0,dy,dz)))
   neighbors=[[] for _ in o.data.vertices]
   for e in o.data.edges:a,b=e.vertices;neighbors[a].append(b);neighbors[b].append(a)
   for it in range(12):
    smoothed=[]
    for i,d in enumerate(delta):
     ns=neighbors[i]
     avg=sum((delta[j] for j in ns),Vector())/len(ns) if ns else d
     smoothed.append(Vector((0,d.y,max(d.z,avg.z*.90*allowed[i]))))
    delta=smoothed
   key=o.shape_key_add(name=f'KickContact_{f:02d}',from_mix=False)
   transforms={b.name:r.matrix_world@b.matrix@b.bone.matrix_local.inverted()@r.matrix_world.inverted()@o.matrix_world for b in r.pose.bones}
   for i,(v,d) in enumerate(zip(o.data.vertices,delta)):
    if d.length<1e-7:continue
    mat=Matrix(((0,0,0),(0,0,0),(0,0,0)))
    total=0
    for g in v.groups:
     name=o.vertex_groups[g.group].name
     if name in transforms:mat+=transforms[name].to_3x3()*g.weight;total+=g.weight
    if total:key.data[i].co=v.co+mat.inverted_safe()@d
   for frame,value in [(1,0),(144+f-1,0),(144+f,1),(144+f+1,0),(216,0)]:
    key.value=value;key.keyframe_insert('value',frame=frame)
   key.value=0
   for m in solids:m.show_viewport=True
  if f%10==0:log('CLOTH FRAME '+str(f))
 scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Sparring_Samples.blend'))
 build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 for f in [170,179,189]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Contact_Side_{f}.png');bpy.ops.render.render(write_still=True)
 log('CONTACT REVIEW READY')
try:run()
except:log(traceback.format_exc());raise
