"""Rebuild current nine presets into staged animation, gameplay and crowd assets.
Never changes the user's interactive Blender session or original deliverables.
"""
import bpy,sys,json,math,traceback
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
import build_character_variations as hair
import build_character_suite as suite
import finish_character_suite as finish
import build_single_helmet_study as view
ROOT=suite.ROOT;OUT=ROOT/'Resources/Models/UpdatedBuild';OUT.mkdir(exist_ok=True)
SIZES=['Medium','Compact','Stocky','LeanTall','Tall'];PRESETS=SIZES+[p[0] for p in hair.PRESETS]
HELMETS=['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown'];PROTECTORS=['Quilted_Lace_Back','Smooth_Buckle_Back']
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def refresh(rig):
 rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
def measurements(rig):
 head=bpy.data.objects['Head'];body=bpy.data.objects['Body'];h=(rig.matrix_world@rig.data.bones['head'].head_local).z
 hp=[head.matrix_world@v.co for v in head.data.vertices];rib=(rig.matrix_world@rig.data.bones['spine_04'].head_local).z
 band=[body.matrix_world@v.co for v in body.data.vertices if abs((body.matrix_world@v.co).z-rib)<.022]
 return dict(head_z=h,head_top=max(p.z for p in hp),head_width=max(p.x for p in hp)-min(p.x for p in hp),rib_width=max(p.x for p in band)-min(p.x for p in band),rib_depth=max(p.y for p in band)-min(p.y for p in band))
def prepare():
 for label,path,prefixes in [('Gear','ProtectorReferenceV2/Chest_Protector_Library.blend',tuple(s+'__' for s in HELMETS+PROTECTORS)),('Hair','CharacterVariations/Male_Athletic/Character.blend',('Hair_','Eyebrows_'))]:
  bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models'/path));rig=bpy.data.objects['RIG_Body_Medium'];objects=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(prefixes)]
  assert objects
  (OUT/(label+'_measurements.json')).write_text(json.dumps(measurements(rig)))
  bpy.data.libraries.write(str(OUT/(label+'_Library.blend')),set(objects),fake_user=True,compress=True)
  log('Prepared '+label)
def redirect(owner,rig):
 if owner and owner.animation_data:
  for d in owner.animation_data.drivers:
   for v in d.driver.variables:
    for t in v.targets:
     if isinstance(t.id,bpy.types.Object) and t.id.type=='ARMATURE':t.id=rig
def append_parts(label,rig,target):
 src=json.loads((OUT/(label+'_measurements.json')).read_text());old=set(bpy.data.objects)
 with bpy.data.libraries.load(str(OUT/(label+'_Library.blend')),link=False) as (a,b):
  b.objects=[n for n in a.objects if n.startswith(('Hair_','Eyebrows_') if label=='Hair' else tuple(s+'__' for s in HELMETS+PROTECTORS))]
 for o in b.objects:
  name=o.name.split('.')[0];o.name=name
  cat='Protector' if any(name.startswith(s+'__') for s in PROTECTORS) else 'Helmet' if any(name.startswith(s+'__') for s in HELMETS) else 'Eyebrows' if name.startswith('Eyebrows_') else 'Hair'
  style=name.split('__')[0];coll=bpy.data.collections.get(style) or bpy.data.collections.new(style)
  if coll.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(coll)
  coll.objects.link(o)
  world=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix()
  hz=(target['head_top']-target['head_z'])/(src['head_top']-src['head_z']);hx=target['head_width']/src['head_width'];zs=target['head_z']/src['head_z']
  sx=(target['rib_width']+.10*zs)/(src['rib_width']+.10);sy=(target['rib_depth']+.10*zs)/(src['rib_depth']+.10)
  def transform(vertices):
   for v in vertices:
    p=world@v.co
    v.co=Vector((p.x*sx,p.y*sy,p.z*zs)) if cat=='Protector' else Vector((p.x*hx,p.y*hx,target['head_z']+(p.z-src['head_z'])*hz))
  if o.data.shape_keys:
   for key in o.data.shape_keys.key_blocks:transform(key.data)
   for vertex,point in zip(o.data.vertices,o.data.shape_keys.key_blocks[0].data):vertex.co=point.co
   redirect(o.data.shape_keys,rig)
  else:transform(o.data.vertices)
  if cat=='Eyebrows':
   o.vertex_groups.clear()
   for m in list(o.modifiers):
    if m.type=='ARMATURE':o.modifiers.remove(m)
   hair.bind_eyebrows(o,bpy.data.objects['Head'])
  else:suite.bind(o,rig)
  redirect(o,rig)
  for mat in o.data.materials:
   if mat and mat.use_nodes:redirect(mat.node_tree,rig)
  o['CurrentCategory']=cat
 for o in list(bpy.data.objects):
  if o not in old and o not in b.objects and o.type=='ARMATURE':bpy.data.objects.remove(o,do_unlink=True)
def preview(kind):
 directory=OUT/kind;directory.mkdir(exist_ok=True)
 source=ROOT/('Resources/Models/Animation/OpenStance_'+kind+'_Animation.blend' if kind in SIZES else 'Resources/Models/CharacterVariations/'+kind+'/Character.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
 rig=next(o for o in scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));face=next(o for o in scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Face_'))
 rig.name='RIG_Body_'+kind;face.name='RIG_Face_'+kind;scene.name='Fighter_'+kind
 if kind in SIZES and scene.get('AssetRevision')!='Updated specifications - 2026-10-05':
  target=measurements(rig)
  for o in list(bpy.data.objects):
   if o.type=='MESH' and o.name.startswith(('Helmet','Protector','Hair_','Eyebrows')):bpy.data.objects.remove(o,do_unlink=True)
  for prop,val in {'HairStyle':0,'HairColor':1,'EyebrowStyle':0,'Wear_Eyebrows':True,'HelmetDesign':0,'ProtectorDesign':0,'Wear_Hair':True,'MatchSide':0}.items():rig[prop]=val
  append_parts('Gear',rig,target);append_parts('Hair',rig,target)
 for prop,names in [('HairStyle',hair.STYLES),('EyebrowStyle',hair.EYEBROW_STYLES),('HelmetDesign',HELMETS),('ProtectorDesign',PROTECTORS)]:
  rig.id_properties_ui(prop).update(min=0,max=len(names)-1,description='; '.join(f'{i}: {n}' for i,n in enumerate(names)))
 # Keep existing rig rest transforms, animation channels and 41 marker guides.
 assert len(rig.data.bones)==341 and len(face.data.bones)==874
 assert len([o for o in scene.objects if o.get('MarkerLabel')])==41
 for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[prop]=False
 rig['Wear_Jacket']=True;rig['Wear_Pants']=True;rig['Wear_Hair']=True
 scene['AssetRevision']='Updated specifications - 2026-10-05';rig['CharacterPreset']=kind
 refresh(rig)
 for img in bpy.data.images:
  if img.source=='FILE' and not img.packed_file:
   try:img.pack()
   except:pass
 z=measurements(rig)['head_z']/1.578
 view.camera(scene,(.8*z,-2*z,1.55*z),(0,0,.91*z),2.06*z);scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
 from repair_garment_openings import repair as repair_openings
 repair_openings(scene)
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/'Preview.blend'),compress=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/('OpenStance_'+kind+'_Animation.blend')),compress=True)
 scene.render.filepath=str(directory/'Updated_Dobok.png');bpy.ops.render.render(write_still=True)
 for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[prop]=True
 refresh(rig);scene.render.filepath=str(directory/'Updated_Sparring.png');bpy.ops.render.render(write_still=True)
 log(kind+' preview complete')

def reduce_mesh(o,budget):
 """Reduce geometry while preserving the fitted helmet shape through interpolation."""
 if suite.tris(o)<=budget:return
 keys=o.data.shape_keys;key_data=[];tree=None;driver_info=[]
 if keys:
  basis=[v.co.copy() for v in keys.key_blocks[0].data];tree=KDTree(len(basis))
  for i,p in enumerate(basis):tree.insert(p,i)
  tree.balance()
  for key in list(keys.key_blocks)[1:]:key_data.append((key.name,[v.co-basis[i] for i,v in enumerate(key.data)]))
  if keys.animation_data:
   for d in keys.animation_data.drivers:
    driver_info.append((d.data_path,d.driver.expression,[(v.name,v.targets[0].id,v.targets[0].data_path) for v in d.driver.variables]))
  o.shape_key_clear()
  for vertex,point in zip(o.data.vertices,basis):vertex.co=point
 # Collapse alone cannot meet a strand budget: each disconnected fiber has a
 # minimum topology. Thin entire fibers evenly before collapsing anything.
 if o.name.startswith(('Hair_','Eyebrows_')) and not any(s in o.name for s in ['Scalp_Coverage','Core','Tie']):
  import bmesh
  bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);components=[]
  for seed in list(bm.verts):
   if seed not in remaining:continue
   remaining.remove(seed);stack=[seed];component=[]
   while stack:
    v=stack.pop();component.append(v)
    for e in v.link_edges:
     n=e.other_vert(v)
     if n in remaining:remaining.remove(n);stack.append(n)
   components.append(component)
  if len(components)>20:
   count=max(2,int(len(components)*budget/suite.tris(o)))
   keep={int(i*len(components)/count) for i in range(min(count,len(components)))}
   bmesh.ops.delete(bm,geom=[v for i,c in enumerate(components) if i not in keep for v in c],context='VERTS')
   bm.to_mesh(o.data)
  bm.free()
 # Use the ordinary collapse path, not the legacy Hair_ special-case cap builder.
 name=o.name;o.name='LOD_'+name;suite.decimate(o,budget);o.name=name
 if key_data:
  o.shape_key_add(name='Basis')
  for name,delta in key_data:
   key=o.shape_key_add(name=name)
   for v in key.data:
    nearest=tree.find_n(v.co,3);weights=[1/max(d,.00001)**2 for _,_,d in nearest];total=sum(weights)
    v.co+=sum((delta[i]*w/total for (_,i,_),w in zip(nearest,weights)),Vector())
  for path,expr,variables in driver_info:
   d=o.data.shape_keys.driver_add(path).driver;d.expression=expr
   for name,target,path in variables:
    v=d.variables.new();v.name=name;v.targets[0].id=target;v.targets[0].data_path=path

def portable_materials():
 """Give export copies simple image/color materials, avoiding shader misinterpretation."""
 originals={}
 converted={}
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':continue
  originals[o]=list(o.data.materials)
  for i,mat in enumerate(list(o.data.materials)):
   if not mat or not mat.use_nodes:continue
   if mat.get('PortableFabric'):continue
   name=mat.name.split('.')[0];cache=converted.get(mat)
   if cache:o.data.materials[i]=cache;continue
   bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   if not bs:continue
   cache=bpy.data.materials.new('EXPORT_'+mat.name);cache.use_nodes=True;nodes=cache.node_tree.nodes;links=cache.node_tree.links;dest=nodes.get('Principled BSDF')
   converted[mat]=cache
   dest.inputs['Base Color'].default_value=bs.inputs['Base Color'].default_value
   dest.inputs['Alpha'].default_value=bs.inputs['Alpha'].default_value
   if bs.inputs['Alpha'].default_value<1:cache.surface_render_method='DITHERED'
   # Preserve authored surface response instead of flattening skin, hair and
   # protective foam to the same roughness on every export.
   for socket in ['Roughness','Metallic','Specular IOR Level','Sheen Weight']:
    dest.inputs[socket].default_value=bs.inputs[socket].default_value
   path=OUT/'Textures'/(name+'.png');image=None
   if path.exists():image=bpy.data.images.load(str(path),check_existing=True)
   elif bs.inputs['Base Color'].is_linked:
    origin=bs.inputs['Base Color'].links[0].from_node
    if origin.type=='TEX_IMAGE':image=origin.image
   if image:
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(tex.outputs['Color'],dest.inputs['Base Color'])
    if not image.packed_file:
     try:image.pack()
     except:pass
   cache.diffuse_color=dest.inputs['Base Color'].default_value
   if bs.inputs['Alpha'].is_linked:
    origin=bs.inputs['Alpha'].links[0].from_node
    if origin.type=='TEX_IMAGE' and origin.image:
     tex=nodes.new('ShaderNodeTexImage');tex.image=origin.image
     links.new(tex.outputs['Alpha'],dest.inputs['Alpha']);cache.surface_render_method='DITHERED'
     if not tex.image.packed_file:tex.image.pack()
   # FBX understands a tangent normal image feeding a Normal Map node. Keep
   # this authored detail instead of silently dropping it from export copies.
   if bs.inputs['Normal'].is_linked:
    origin=bs.inputs['Normal'].links[0].from_node
    if origin.type=='NORMAL_MAP' and origin.space=='TANGENT' and origin.inputs['Color'].is_linked:
     source=origin.inputs['Color'].links[0].from_node
     if source.type=='TEX_IMAGE' and source.image:
      tex=nodes.new('ShaderNodeTexImage');tex.image=source.image
      tex.extension=source.extension;tex.interpolation=source.interpolation
      normal=nodes.new('ShaderNodeNormalMap');normal.space='TANGENT';normal.uv_map=origin.uv_map
      normal.inputs['Strength'].default_value=origin.inputs['Strength'].default_value
      links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],dest.inputs['Normal'])
      if not tex.image.packed_file:tex.image.pack()
   o.data.materials[i]=cache
 return originals

def resample_scalp(o,head,rig,level):
 """Use a single regular scalp surface; collapsing a thin double shell clips."""
 from mathutils.bvhtree import BVHTree
 source=o.data.shape_keys.key_blocks;basis=[p.co.copy() for p in source['Basis'].data];fitted=[p.co.copy() for p in source['HelmetFit'].data]
 assert len(basis)>=4736,'Expected generated 128-column scalp grid'
 column_step,row_step={'Gameplay_High':(2,2),'Gameplay_Mid':(4,2),'Gameplay_Far':(4,3),'Crowd_Near':(4,3),'Crowd_Far':(8,4)}[level]
 rows=list(range(0,37,row_step));cols=list(range(0,128,column_step));indices=[r*128+c for r in rows for c in cols]
 headpoints=[head.matrix_world@v.co for v in head.data.vertices];tree=BVHTree.FromPolygons(headpoints,[tuple(p.vertices) for p in head.data.polygons]);inv=o.matrix_world.inverted()
 def fitted_points(source,clearance):
  result=[]
  for i in indices:
   p=o.matrix_world@source[i];hit,normal,_,distance=tree.find_nearest(p)
   if hit is not None:
    separation=(p-hit).dot(normal)
    if separation<clearance:p+=normal*(clearance-separation)
   result.append(inv@p)
  return result
 positions=fitted_points(basis,.0035);fitpositions=fitted_points(fitted,.002)
 faces=[];width=len(cols)
 for r in range(len(rows)-1):
  for c in range(width):faces.append(((r+1)*width+c,(r+1)*width+(c+1)%width,r*width+(c+1)%width,r*width+c))
 mats=list(o.data.materials);data=bpy.data.meshes.new(o.name+'_Surface');data.from_pydata(positions,[],faces);data.update();o.data=data
 for m in mats:data.materials.append(m)
 for p in data.polygons:p.use_smooth=True
 o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(data.vertices))),1,'REPLACE')
 o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
 for v,p in zip(key.data,fitpositions):v.co=p
 d=key.driver_add('value').driver;v=d.variables.new();v.name='helmet';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Helmet"]';d.expression='1 if helmet else 0'
def restore_materials(originals):
 for o,mats in originals.items():
  indices=[polygon.material_index for polygon in o.data.polygons]
  o.data.materials.clear()
  for mat in mats:o.data.materials.append(mat)
  for polygon,index in zip(o.data.polygons,indices):polygon.material_index=index
def meshes():return [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.get('SimulationOnly') and any(m.type=='ARMATURE' for m in o.modifiers)]
def export(rig,path,animation=False):
 from repair_uniform_export_data import fabric_uv
 cloth_enabled=rig.get('BlenderCloth',False)
 if 'BlenderCloth' in rig:rig['BlenderCloth']=False;rig.update_tag();bpy.context.view_layer.update()
 for o in meshes():
  if o.data.uv_layers.get('NaturalHairlineUV'):o['ExportUV']='NaturalHairlineUV'
  elif o.data.uv_layers.get('HairCoverageUV'):o['ExportUV']='HairCoverageUV'
  elif o.name.startswith(('Body','Head')) and o.data.uv_layers.get('DiffuseUV'):o['ExportUV']='DiffuseUV';o['ExportNormalizeUVTile']=True
  elif fabric_uv(o):pass
  elif o.get('ExportUV')=='UVWeave' and o.data.uv_layers.get('UVWeave'):pass
  elif o.data.uv_layers.get('UVMap'):o['ExportUV']='UVMap'
 mats=portable_materials()
 try:finish.export(rig,meshes(),path,animation)
 finally:
  restore_materials(mats)
  if 'BlenderCloth' in rig:rig['BlenderCloth']=cloth_enabled;rig.update_tag();bpy.context.view_layer.update()

def profile(kind,level):
 directory=OUT/kind;bpy.ops.wm.open_mainfile(filepath=str(directory/'Preview.blend'));rig=bpy.data.objects['RIG_Body_'+kind];scene=bpy.context.scene;crowd=level.startswith('Crowd')
 rig.animation_data.action=None
 for tr in rig.animation_data.nla_tracks:tr.mute=True
 for p in rig.pose.bones:p.matrix_basis=Matrix()
 limits={'Gameplay_High':(20000,28000,16000,30000,22000,2800),'Gameplay_Mid':(10000,14000,6500,15000,11000,1200),'Gameplay_Far':(5000,6000,2200,6000,10000,400),'Crowd_Near':(2200,2400,1000,0,0,250),'Crowd_Far':(800,700,350,0,0,100)}
 bodyb,headb,hairb,helmetb,guardb,browb=limits[level]
 visible=meshes();groups={}
 for o in visible:
  n=o.name
  category='Helmet' if any(n.startswith(s+'__') for s in HELMETS) else 'Protector' if any(n.startswith(s+'__') for s in PROTECTORS) else 'Hair' if n.startswith('Hair_') else 'Eyebrows' if n.startswith('Eyebrows_') else n.split('_')[0]
  o['CurrentCategory']=category
  key=n.split('__')[0] if category in ['Helmet','Protector','Hair'] else n
  groups.setdefault((category,key),[]).append(o)
 for (category,key),objects in groups.items():
  log(kind+' '+level+' reducing '+key)
  target={'Body':bodyb,'Head':headb,'Hair':hairb,'Eyebrows':browb,'Helmet':helmetb,'Protector':guardb,'Jacket':int(bodyb*.76),'Pants':int(bodyb*.60),'Belt':max(180,int(bodyb*.14)),'Gloves':0 if crowd else int(bodyb*.5),'FootGuards':0 if crowd else int(bodyb*.5)}.get(category,1000)
  total=sum(suite.tris(o) for o in objects)
  for o in objects:
   if target==0:bpy.data.objects.remove(o,do_unlink=True);continue
   if category in ['Hair','Eyebrows']:
    o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(o.data.vertices))),1,'REPLACE')
   budget=max(30,round(target*suite.tris(o)/max(total,1)))
   if category=='Hair' and 'Scalp_Coverage' in o.name:
    budget=max(budget,{'Gameplay_High':2000,'Gameplay_Mid':1200,'Gameplay_Far':800,'Crowd_Near':800,'Crowd_Far':500}[level])
   if category=='Hair' and 'Scalp_Coverage' in o.name:resample_scalp(o,bpy.data.objects['Head'],rig,level)
   else:reduce_mesh(o,budget)
   suite.weights(o,rig,4)
 # Removing face rig after head rebinding prevents duplicate skeletons in FBX.
 face=bpy.data.objects.get('RIG_Face_'+kind)
 if face:bpy.data.objects.remove(face,do_unlink=True)
 for o in list(bpy.data.objects):
  if o.get('MarkerLabel'):bpy.data.objects.remove(o,do_unlink=True)
 # Keep trousers continuous under the jacket, especially for seated poses.
 pants=bpy.data.objects['Pants']
 for m in list(pants.modifiers):
  if m.type=='MASK':pants.modifiers.remove(m)
 for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[key]=not crowd
 rig['Wear_Hair']=True;rig['Wear_Eyebrows']=True;refresh(rig)
 clips=[]
 if crowd:
  suite.reduce_rig(rig,meshes());finish.crowd_shoes(rig);clips=finish.actions(rig)
 refresh(rig)
 from repair_garment_openings import repair as repair_openings
 repair_openings(scene)
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/(level+'.blend')),compress=True)
 if crowd:
  export(rig,directory/(level+'.fbx'))
  if level=='Crowd_Near':
   for clip in clips:
    rig.animation_data.action=bpy.data.actions[clip];export(rig,directory/(clip+'.fbx'),True)
   rig.animation_data.action=None
 else:
  export(rig,directory/(level+'_Sparring.fbx'))
  for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[key]=False
  refresh(rig);export(rig,directory/(level+'_Dobok.fbx'))
  if level=='Gameplay_High':export(rig,directory/('OpenStance_'+kind+'_Mocap_Source.fbx'))
 count={o.name:suite.tris(o) for o in meshes() if not o.hide_render}
 (directory/(level+'_validation.json')).write_text(json.dumps({'profile':level,'preset':kind,'body_bones':len(rig.data.bones),'visible_base_triangles':sum(count.values()),'parts':count,'clips':clips,'real_capture_tested':False},indent=2))
 log(kind+' '+level+' complete')

if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
  if args==['prepare']:prepare()
  elif len(args)==2 and args[0]=='preview':preview(args[1])
  elif len(args)==3 and args[0]=='profile':profile(args[1],args[2])
  else:
   fresh='--fresh' in args;args=[a for a in args if a!='--fresh']
   for kind in args or PRESETS:
    if fresh or not (OUT/kind/'Preview.blend').exists():preview(kind)
    for level in ['Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:profile(kind,level)
 except:log(traceback.format_exc());raise
