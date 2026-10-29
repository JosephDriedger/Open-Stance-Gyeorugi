"""Feathered scalp coverage that retains existing hairstyle/helmet geometry."""
import bpy,sys,math,json,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
ROOT=Path('D:/Open-Stance-Gyeorugi');OUT=ROOT/'Resources/Models/HairClothRevision';OUT.mkdir(exist_ok=True)
def texture(crew):
 name='HairCoverage_Crew' if crew else 'HairCoverage_Long'
 image=bpy.data.images.get(name)
 if image:return image
 w,h=1024,512;rng=np.random.default_rng(451 if crew else 901)
 y,x=np.mgrid[0:h,0:w];v=y/(h-1);u=x/w
 # Irregular micro-density and a gradual, non-circular edge, rather than a cap.
 edge=.025+.017*np.sin(u*math.tau*7)+.010*np.sin(u*math.tau*23)
 fade=np.clip((v-edge)/.10,0,1);fade=fade*fade*(3-2*fade)
 noise=rng.random((h,w));fiber=(.5+.5*np.sin(x*2.1+y*.55+np.sin(y*.09)*1.5))
 alpha=fade*(.35+.60*noise if crew else .80+.20*noise)
 rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,:3]=.7+.3*fiber[:,:,None];rgba[:,:,3]=alpha
 image=bpy.data.images.new(name,width=w,height=h,alpha=True);image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG';image.save();image.pack();return image
def repair(scene):
 scene.cycles.transparent_max_bounces=64
 from build_character_variations import Hair
 rig=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 center=Vector((0,.002,1.650))*scale
 head=next(o for o in scene.objects if o.name=='Head')
 fit=Hair(head);fit.center=center
 bpy.context.view_layer.update()
 skin=rig.matrix_world@rig.pose.bones['head'].matrix@rig.data.bones['head'].matrix_local.inverted()@rig.matrix_world.inverted()
 unskin=skin.inverted();fit.center=skin@center;center=fit.center
 evaluated=head.evaluated_get(bpy.context.evaluated_depsgraph_get());surface=evaluated.to_mesh()
 fit.bvh=BVHTree.FromPolygons([head.matrix_world@v.co for v in surface.vertices],[tuple(p.vertices) for p in surface.polygons]);evaluated.to_mesh_clear()
 rows=[]
 for o in scene.objects:
  if o.type!='MESH' or 'Scalp_Coverage' not in o.name:continue
  if 'Crew_Cut' not in o.name:continue
  count=len(o.data.vertices)
  grids={9472:(128,37),4736:(128,37),1216:(64,19),608:(32,19),416:(32,13),160:(16,10)}
  if count not in grids:raise RuntimeError('Unrecognized scalp grid '+o.name+' '+str(count))
  cols,nrows=grids[count]
  from build_character_variations import STYLES
  style=next(i for i,n in enumerate(STYLES) if n in o.name);source=o.data.materials[0]
  coords=[];fitcoords=[];faces=[];inv=o.matrix_world.inverted()
  for row in range(nrows):
   for col in range(cols):
    a=math.tau*col/cols;p=.001+(fit.limit(a)-.001)*row/(nrows-1)
    d=Vector((math.sin(p)*math.sin(a),-math.sin(p)*math.cos(a),math.cos(p)))
    hit=fit.bvh.ray_cast(center,d)[0]
    if hit is None:hit=fit.bvh.find_nearest(center+Vector((d.x*.085,d.y*.11,d.z*.11))*scale)[0]
    assert hit is not None,('No head surface',o.name,row,col)
    q=hit+d*.0015*scale if style==0 else fit.point(a,p,style)
    coords.append(inv@unskin@q);fitcoords.append(inv@unskin@(hit+d*.0008*scale))
  for row in range(nrows-1):
   for col in range(cols):
    a=row*cols+col;b=row*cols+(col+1)%cols;faces.append((a,a+cols,b+cols,b))
  mesh=bpy.data.meshes.new(o.name+'_SingleSurface');mesh.from_pydata(coords,[],faces);mesh.update();o.data=mesh
  for p in mesh.polygons:p.use_smooth=True
  o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(coords))),1,'REPLACE')
  o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
  for v,p in zip(key.data,fitcoords):v.co=p
  driver=key.driver_add('value').driver;var=driver.variables.new();var.name='helmet';var.targets[0].id=rig;var.targets[0].data_path='["Wear_Helmet"]';driver.expression='1 if helmet else 0'
  uv=o.data.uv_layers.new(name='HairCoverageUV')
  o.data.uv_layers.active=uv
  from collections import Counter
  from mathutils.kdtree import KDTree
  limit=cols*nrows;edges=Counter()
  for polygon in o.data.polygons:
   ids=list(polygon.vertices)
   if any(i>=limit for i in ids):continue
   for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]+=1
  points=[o.matrix_world@v.co for v in o.data.vertices];ztop=max(p.z for p in points)
  boundary=set(range((nrows-1)*cols,nrows*cols))
  assert boundary,('Missing hairline boundary',o.name)
  tree=KDTree(len(boundary))
  for j,i in enumerate(boundary):tree.insert(points[i],j)
  tree.balance()
  distances=[tree.find(o.matrix_world@vertex.co)[2] for vertex in o.data.vertices]
  max_distance=max(distances)*1.025
  values=[]
  for vertex in o.data.vertices:
   q=o.matrix_world@vertex.co-center;a=math.atan2(q.x,-q.y);phi=math.atan2(math.hypot(q.x,q.y),q.z)
   distance=tree.find(o.matrix_world@vertex.co)[2]
   values.append(((a/math.tau)%1,max(.001,min(.998,distance/max_distance))))
  for p in o.data.polygons:
   values_face=[values[o.data.loops[li].vertex_index] for li in p.loop_indices]
   wrap=max(x[0] for x in values_face)-min(x[0] for x in values_face)>.5
   for li,(u,v) in zip(p.loop_indices,values_face):uv.data[li].uv=(u+1 if wrap and u<.5 else u,v)
  crew='Crew_Cut' in o.name
  mat=source.copy();mat.name='Feathered_'+o.name;mat.surface_render_method='DITHERED'
  bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.82
  bs.inputs['Specular IOR Level'].default_value=.18
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.name='Portable Hair Coverage';tex.image=texture(crew);tex.extension='REPEAT'
  coords=mat.node_tree.nodes.new('ShaderNodeUVMap');coords.uv_map=uv.name
  mat.node_tree.links.new(coords.outputs['UV'],tex.inputs['Vector']);mat.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
  o.data.materials.clear();o.data.materials.append(mat)
  for p in o.data.polygons:p.material_index=0
  mat['HairCoverageRevision']='2026-10-15';o['ExportUV']=uv.name
  rows.append({'object':o.name,'vertices':count,'crew':crew})
 return rows
if __name__=='__main__':
 try:
  bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/TPose/OpenStance_Medium_Tpose.blend'))
  s=bpy.context.scene;rows=repair(s);r=bpy.data.objects['RIG_Body_Medium'];r['HairStyle']=0;r.update_tag();s.frame_set(1)
  s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100;s.cycles.samples=32
  view.camera(s,(.12,-.32,2.05),(0,0,1.70),.36)
  bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Hair_Pilot.blend'),compress=True)
  s.render.filepath=str(OUT/'Hair_Top.png');bpy.ops.render.render(write_still=True)
  view.camera(s,(.18,-.55,1.78),(0,0,1.67),.38);s.render.filepath=str(OUT/'Hair_Front.png');bpy.ops.render.render(write_still=True)
  (OUT/'hair_pilot.json').write_text(json.dumps(rows,indent=2))
 except:(OUT/'hair_error.log').write_text(traceback.format_exc());raise
