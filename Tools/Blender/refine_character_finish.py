"""Natural hair boundaries, continuous ponytail LOD and folded belt knot."""
import bpy,sys,math,json,traceback
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
import repair_sparring_fit as previous
import audit_sparring_styles as audit
ROOT=previous.ROOT;OUT=ROOT/'Resources/Models/FinishRefinementV2';OUT.mkdir(exist_ok=True)

def coverage():
 name='Natural_Hairline_Coverage'
 if bpy.data.images.get(name):return bpy.data.images[name]
 w,h=1024,256;y,x=np.mgrid[0:h,0:w];u=x/w;v=y/(h-1)
 rng=np.random.default_rng(1204)
 edge=.04+.025*np.sin(u*math.tau*19)+.018*np.sin(u*math.tau*47)
 threshold=edge+.06*rng.random((1,w))
 alpha=np.clip((v-threshold)/.16,0,1);alpha=alpha*alpha*(3-2*alpha)
 rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,3]=alpha
 image=bpy.data.images.new(name,width=w,height=h,alpha=True);image.pixels.foreach_set(rgba.ravel());image.pack()
 return image

def hairline(o,scale):
 # Original caps use one grid or a grid plus its thickness copy.
 count=len(o.data.vertices);grids={9472:(128,37),4736:(128,37),1216:(64,19),608:(32,19),416:(32,13),160:(16,10)}
 if count not in grids:return {'skipped_topology':count}
 cols,rows=grids[count];size=cols*rows
 boundary=list(range((rows-1)*cols,size))
 points=[o.matrix_world@v.co for v in o.data.vertices]
 kd=KDTree(len(boundary))
 for j,i in enumerate(boundary):kd.insert(points[i],j)
 kd.balance();uv=o.data.uv_layers.get('NaturalHairlineUV') or o.data.uv_layers.new(name='NaturalHairlineUV');o.data.uv_layers.active=uv
 values=[((i%cols)/cols,min(.99,kd.find(p)[2]/(.020*scale))) for i,p in enumerate(points)]
 for poly in o.data.polygons:
  us=[values[o.data.loops[li].vertex_index][0] for li in poly.loop_indices];wrap=max(us)-min(us)>.5
  for li in poly.loop_indices:
   u,v=values[o.data.loops[li].vertex_index];uv.data[li].uv=(u+1 if wrap and u<.5 else u,v)
 mat=o.data.materials[0].copy();mat.name='Natural_Edge_'+o.name;mat.surface_render_method='DITHERED'
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=coverage();tex.extension='REPEAT'
 coords=mat.node_tree.nodes.new('ShaderNodeUVMap');coords.uv_map=uv.name
 mat.node_tree.links.new(coords.outputs['UV'],tex.inputs['Vector']);mat.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
 o.data.materials.clear();o.data.materials.append(mat)
 for p in o.data.polygons:p.material_index=0
 return {'edge_fade_mm':4,'vertices':count}

def pony_core(o,rig,scale):
 if any('Ponytail_Core' in x.name for x in bpy.context.scene.objects):return None
 key=o.data.shape_keys
 if not key:return None
 count=14;cols=16;faces=[]
 def shape(block):
  ps=np.array([tuple(v.co) for v in block.data]);low,high=ps[:,2].min(),ps[:,2].max();coords=[]
  for j in range(count+1):
   t=j/count;z=high-(high-low)*t
   near=ps[np.abs(ps[:,2]-z)<(high-low)/count*.8]
   if len(near)<3:near=ps[np.argsort(np.abs(ps[:,2]-z))[:12]]
   center=np.median(near[:,:2],axis=0);rx=max(.001*scale,np.quantile(np.abs(near[:,0]-center[0]),.83));ry=max(.001*scale,np.quantile(np.abs(near[:,1]-center[1]),.83))
   taper=1-.85*max(0,(t-.8)/.2)**2
   for i in range(cols):
    a=math.tau*i/cols;coords.append((center[0]+rx*math.cos(a)*taper,center[1]+ry*math.sin(a)*taper,z))
  return coords
 for j in range(count):
  for i in range(cols):faces.append((j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i))
 faces += [tuple(reversed(range(cols))),tuple(count*cols+i for i in range(cols))]
 mesh=bpy.data.meshes.new('Continuous_Ponytail_Core');mesh.from_pydata(shape(key.key_blocks[0]),[],faces);mesh.update()
 core=o.copy();core.data=mesh;core.name='Hair_Low_Ponytail__Ponytail_Core'
 for coll in o.users_collection:coll.objects.link(core)
 core.vertex_groups.clear();core.vertex_groups.new(name='head').add(list(range(len(mesh.vertices))),1,'REPLACE')
 core.data.materials.append(o.data.materials[0]);core.shape_key_add(name='Basis');fitted=core.shape_key_add(name='HelmetFit')
 for v,p in zip(fitted.data,shape(key.key_blocks['HelmetFit'])):v.co=p
 driver=fitted.driver_add('value').driver;v=driver.variables.new();v.name='helmet';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Helmet"]';driver.expression='1 if helmet else 0'
 for p in mesh.polygons:p.use_smooth=True
 return core.name

def knot(o,scale):
 if o.data.shape_keys:return {'skipped':'authored shape keys'}
 points=[o.matrix_world@v.co for v in o.data.vertices];z=(min(p.z for p in points)+max(p.z for p in points))*.5;y=min(p.y for p in points)+.003*scale
 verts=[];faces=[];inv=o.matrix_world.inverted();steps=12;cols=12
 for layer,angle in enumerate([-.48,.48]):
  start=len(verts);axis=Vector((math.cos(angle),0,math.sin(angle)));across=Vector((-math.sin(angle),0,math.cos(angle)))
  for j in range(steps+1):
   t=j/steps;center=Vector((0,y-layer*.004*scale,z))+axis*((t-.5)*.052*scale)
   center.y-=.003*scale*math.sin(math.pi*t)
   width=.011*scale*(.85+.15*abs(2*t-1))
   for i in range(cols):
    a=math.tau*i/cols;p=center+across*(width*math.cos(a))+Vector((0,.004*scale*math.sin(a),0));verts.append(inv@p)
  for j in range(steps):
   for i in range(cols):faces.append((start+j*cols+i,start+j*cols+(i+1)%cols,start+(j+1)*cols+(i+1)%cols,start+(j+1)*cols+i))
  faces += [tuple(start+i for i in reversed(range(cols))),tuple(start+steps*cols+i for i in range(cols))]
 mats=list(o.data.materials);mesh=bpy.data.meshes.new('Folded_Square_Belt_Knot');mesh.from_pydata(verts,[],faces);mesh.update();o.data=mesh
 for m in mats:mesh.materials.append(m)
 for mod in list(o.modifiers):
  if mod.type=='SOLIDIFY':o.modifiers.remove(mod)
 o.vertex_groups.clear();o.vertex_groups.new(name='pelvis').add(list(range(len(verts))),1,'REPLACE')
 for p in mesh.polygons:p.use_smooth=True
 uv=mesh.uv_layers.new(name='UVWeave')
 for loop in mesh.loops:
  p=verts[loop.vertex_index];uv.data[loop.index].uv=(p.x/.05,p.z/.05)
 return {'vertices':len(verts),'attachment':'pelvis'}

def clear_bare_hair(scene,scale):
 poses={o:o.data.pose_position for o in scene.objects if o.type=='ARMATURE'}
 for o in poses:o.data.pose_position='REST'
 bpy.context.view_layer.update();surface=previous.tree(bpy.data.objects['Head'],True);rows={}
 for o in scene.objects:
  if o.type!='MESH' or not o.name.startswith('Hair_') or not o.data.shape_keys:continue
  if any(n in o.name for n in ['__Ponytail','__Coiled_Bun','__Hair_Tie']):continue
  basis=o.data.shape_keys.key_blocks[0];inv=o.matrix_world.inverted();changed=0
  clearance=(.003 if 'Scalp_Coverage' in o.name else .0045)*scale
  for v in basis.data:
   p=o.matrix_world@v.co;center=Vector((0,.002,1.650))*scale;axis=(p-center).normalized()
   outer=surface.ray_cast(center+axis*(.35*scale),-axis,.35*scale)[0]
   if outer is not None and p.z>1.61*scale and (outer-p).length<.04*scale and (p-center).length<(outer-center).length+clearance:
    v.co=inv@(outer+axis*clearance);changed+=1
  rows[o.name]=changed
 for o,value in poses.items():o.data.pose_position=value
 bpy.context.view_layer.update();return rows

def repair(scene):
 if scene.get('FinishRefinementV2')=='2026-10-18':return {'already_repaired':True}
 rig=next(o for o in scene.objects if o.name.startswith('RIG_Body_'));scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578;rows={}
 scene.cycles.transparent_max_bounces=64
 rows['bare_hair_clearance']=clear_bare_hair(scene,scale)
 for o in list(scene.objects):
  if o.type!='MESH':continue
  if o.name.startswith('Hair_') and 'Scalp_Coverage' in o.name and 'Crew_Cut' not in o.name:rows[o.name]=hairline(o,scale)
  if o.name.split('.')[0]=='Hair_Low_Ponytail__Ponytail':rows['ponytail_core']=pony_core(o,rig,scale)
  if o.name=='Belt':rows['belt_knot']=knot(o,scale)
 scene['FinishRefinementV2']='2026-10-18'
 return rows

if __name__=='__main__':
 try:
  for kind,level in [('Medium','Preview'),('Female_Athletic','Gameplay_High')]:
   s,r,z,src=audit.load(kind,level);rows=repair(s);d=OUT/'PilotsC'/kind;d.mkdir(parents=True,exist_ok=True)
   bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(d/(level+'.blend')),compress=True);s.cycles.samples=24
   for gear in [False,True]:
    for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
    for style in [1,3,4,5]:
     r['HairStyle']=style;r['HelmetDesign']=1;audit.build.refresh(r)
     for side,pos in [('Front',(.5,-1,1.84)),('Rear',(.5,1,1.84))]:audit.render(s,r,z,d,f'{int(gear)}_Hair{style}_{side}',pos,(0,0,1.65),.55,640,640)
    audit.render(s,r,z,d,f'{int(gear)}_Belt',(.25,-2,1.2),(0,-.1,.98),.42,640,640)
   (d/'repair.json').write_text(json.dumps(rows,indent=2))
  (OUT/'pilot_complete.txt').write_text('Complete')
 except:(OUT/'pilot_error.log').write_text(traceback.format_exc());raise
