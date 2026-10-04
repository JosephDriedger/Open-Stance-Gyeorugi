"""Unbranded helmet variants modeled from manufacturer photo references.
Run in background Blender. No interactive Blender session is touched.
"""
import bpy,bmesh,math,json,sys,traceback
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/CharacterSuite'
sys.path.insert(0,str(Path(__file__).parent))
import build_character_suite as suite
import finish_character_suite as finish
STYLES=['Padded_OpenFace','Vented_Foam','Perforated_Foam']
URLS=['https://centurymartialarts.com/products/custom-open-face-headgear','https://us.adidascombatsports.com/products/adidas-head-guard','https://www.daedo.com/products/pr-2055']
LOG=OUT/'helmets_build.log'
def log(x):
 with LOG.open('a') as f:f.write(str(x)+'\n')
def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):activate(o);bpy.ops.object.modifier_apply(modifier=m.name)
def mesh(name,verts,faces,material):
 d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
 o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o);d.materials.append(material)
 for p in d.polygons:p.use_smooth=True
 return o
def material(name,rig,rough,team=True):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=rough
 if 'Coat Weight' in bs.inputs:bs.inputs['Coat Weight'].default_value=.2 if rough<.3 else .06
 if team:
  for i,(blue,red) in enumerate(zip((.018,.09,.34),(.57,.013,.023))):
   d=bs.inputs['Base Color'].driver_add('default_value',i).driver;v=d.variables.new();v.name='x';v.targets[0].id=rig;v.targets[0].data_path='["MatchSide"]';d.expression=f'{blue}*(x==0)+{red}*(x==1)'
 else:bs.inputs['Base Color'].default_value=(.009,.011,.016,1)
 noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=480
 bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00015
 m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
 return m
def surface(theta,z):
 radial=math.sqrt(max(.00001,1-((z-1.64)/.135)**2)) if z>=1.64 else 1-.12*((1.64-z)/.15)**2
 return Vector((.102*radial*math.sin(theta),-.014-.125*radial*math.cos(theta),z))
def lower(theta,style):
 a=min(theta,math.tau-theta);t=max(0,min(1,(a-.63)/.34));t=t*t*(3-2*t)
 bottom=1.522+.034*max(0,-math.cos(theta))
 return (1.677 if style==0 else 1.672)*(1-t)+bottom*t
def bevel(o,width=.002,segments=3):
 m=o.modifiers.new('Rounded padding edges','BEVEL');m.width=width;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=.45;apply(o,m)
def hole(o,center,radius,axis='X'):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=1,depth=1,location=center)
 c=bpy.context.object
 if axis=='X':c.rotation_euler[1]=math.pi/2;c.scale=(radius[1],radius[0],.4)
 else:c.scale=(radius[0],radius[1],.3)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 m=o.modifiers.new('Actual ventilation opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=c;apply(o,m);bpy.data.objects.remove(c,do_unlink=True)
def tube(name,points,radius,mat):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=2;c.bevel_depth=radius;c.bevel_resolution=2
 s=c.splines.new('POLY');s.points.add(len(points)-1)
 for p,co in zip(s.points,points):p.co=(*co,1)
 o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o);c.materials.append(mat);activate(o);bpy.ops.object.convert(target='MESH');return bpy.context.object
def ribbon(name,points,width,mat):
 verts=[]
 for p in points:verts.extend([(p[0],p[1]-width/2,p[2]),(p[0],p[1]+width/2,p[2])])
 o=mesh(name,verts,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(points)-1)],mat)
 m=o.modifiers.new('Webbing thickness','SOLIDIFY');m.thickness=.002;apply(o,m);bevel(o,.0007,2);return o
def create(style,rig):
 foam=material('Helmet_'+STYLES[style],rig,.43 if style==0 else .26);black=material('Helmet_Webbing',rig,.85,False)
 seg=128;rows=48;verts=[];faces=[]
 for j in range(rows):
  t=j/rows
  for i in range(seg):
   theta=math.tau*i/seg;bottom=lower(theta,style);z=bottom+(1.775-bottom)*t;verts.append(surface(theta,z))
 for j in range(rows-1):
  for i in range(seg):n=(i+1)%seg;faces.append((j*seg+i,j*seg+n,(j+1)*seg+n,(j+1)*seg+i))
 pole=len(verts);verts.append((0,-.014,1.775))
 for i in range(seg):faces.append(((rows-1)*seg+i,(rows-1)*seg+(i+1)%seg,pole))
 shell=mesh('HelmetShell',verts,faces,foam)
 m=shell.modifiers.new('Foam thickness','SOLIDIFY');m.thickness=.012 if style else .015;m.offset=-1;apply(shell,m)
 # Crown cutouts leave a true supporting center bridge and forehead band.
 if style==0:hole(shell,(0,.005,1.87),(.065,.061),'Z')
 else:
  for x in [-.040,.040]:hole(shell,(x,-.030,1.84),(.026,.044),'Z')
 # Rounded face aperture: wider at the eye/cheek level, tapering at the jaw.
 outline=[(-.065,1.49),(-.073,1.54),(-.083,1.595),(-.083,1.635),(-.077,1.664),(-.068,1.677),(.068,1.677),(.077,1.664),(.083,1.635),(.083,1.595),(.073,1.54),(.065,1.49)]
 vs=[(x,y,z) for y in [-.30,-.04] for x,z in outline];n=len(outline)
 fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 cutter=mesh('Face aperture tool',vs,fs,foam);bevel(cutter,.009,5)
 m=shell.modifiers.new('Curved face opening','BOOLEAN');m.operation='DIFFERENCE';m.object=cutter;apply(shell,m);bpy.data.objects.remove(cutter,do_unlink=True)
 hole(shell,(0,-.007,1.615),(.018,.028))
 vents=[(-.055,1.666),(.002,1.686),(.055,1.661),(.073,1.612)]
 if style==2:vents += [(-.035,1.65),(.026,1.651),(.06,1.578),(.038,1.70)]
 if style:
  for y,z in vents:hole(shell,(0,y,z),(.008 if style==1 else .009,.009))
 bevel(shell,.0022,3)
 # Retopologize Boolean junctions before smoothing: large Boolean n-gons
 # otherwise create visibly flat patches on the curved coated-foam surface.
 m=shell.modifiers.new('Uniform foam topology','REMESH');m.mode='VOXEL';m.voxel_size=.0008;m.use_smooth_shade=True;apply(shell,m)
 m=shell.modifiers.new('Soft foam transitions','SMOOTH');m.factor=.5;m.iterations=8;apply(shell,m)
 shell.data.calc_loop_triangles();count=len(shell.data.loop_triangles)
 if count>45000:
  m=shell.modifiers.new('Preview topology budget','DECIMATE');m.ratio=45000/count;apply(shell,m)
 shell.data.materials.clear();shell.data.materials.append(foam)
 for p in shell.data.polygons:p.material_index=0
 pieces=[shell]
 for sign in [-1,1]:
  # Distinct raised ear rings, hollow through the shell.
  vs=[];fs=[];n=64
  for xscale,ry,rz in [(0,.035,.044),(.006,.035,.044),(.006,.018,.028),(0,.018,.028)]:
   for i in range(n):
    a=math.tau*i/n;vs.append((sign*(.103+xscale),-.007+ry*math.cos(a),1.615+rz*math.sin(a)))
  for ring in range(4):
   for i in range(n):fs.append((ring*n+i,ring*n+(i+1)%n,((ring+1)%4)*n+(i+1)%n,((ring+1)%4)*n+i))
  ear=mesh('Ear padding',vs,fs,foam);bevel(ear,.0015,2);pieces.append(ear)
  if style==0:
   pieces.append(tube('Ear seam',[(sign*.111,-.007+.028*math.cos(a*math.tau/64),1.615+.035*math.sin(a*math.tau/64)) for a in range(65)],.00065,black))
   pieces.append(tube('Ear bridge',[(sign*.11,-.036,1.615),(sign*.111,.022,1.615)],.004,black))
 # A fitted, flat webbing strap under the chin, separate from foam padding.
 points=[]
 for i in range(33):
  t=i/32;x=-.070+.140*t;points.append((x,-.093,1.517+.012*(abs(x)/.07)**2))
 pieces.append(ribbon('Chin strap',points,.022,black))
 if style==0:
  points=[surface(math.pi/2,1.75+(1.775-1.75)*math.sin(math.pi*i/32)) for i in range(33)]
  points=[(-.065+.13*i/32,.005,1.75+.024*math.sin(math.pi*i/32)) for i in range(33)]
  pieces.append(ribbon('Crown webbing',points,.027,black))
 activate(shell)
 for p in pieces:p.select_set(True)
 bpy.ops.object.join();shell.name='Helmet_'+STYLES[style]
 used=sorted(set(p.material_index for p in shell.data.polygons));mats=[shell.data.materials[i] or foam for i in used];indices=[used.index(p.material_index) for p in shell.data.polygons]
 shell.data.materials.clear()
 for mat in mats:shell.data.materials.append(mat)
 for p,index in zip(shell.data.polygons,indices):p.material_index=index
 for p in shell.data.polygons:p.use_smooth=True
 # Native portable UV layer for future painting/baking.
 activate(shell);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
 return shell
def install(kind,profile):
 path=OUT/kind/(profile+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind]
 for o in list(bpy.data.objects):
  if o.type=='MESH' and o.name.startswith('Helmet'):bpy.data.objects.remove(o,do_unlink=True)
 # Build from actual reference-derived source meshes once, then reuse across LODs.
 source=OUT/'HelmetLibrary.blend'
 if kind=='Medium' and profile=='Preview':
  objects=[create(i,rig) for i in range(3)]
  bpy.data.libraries.write(str(source),set(objects),fake_user=True,compress=True)
 else:
  with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('Helmet_')]
  objects=dst.objects
  for o in objects:
   bpy.context.scene.collection.objects.link(o)
   for mat in o.data.materials:
    if mat and mat.node_tree.animation_data:
     for d in mat.node_tree.animation_data.drivers:
      for v in d.driver.variables:
       for t in v.targets:t.id=rig
  # Source library dependency armature is unused after material target rebinding.
  for o in list(bpy.data.objects):
   if o.type=='ARMATURE' and o not in bpy.context.scene.objects.values() and o.name!=rig.name:bpy.data.objects.remove(o,do_unlink=True)
 head=bpy.data.objects['Head'];top=max((head.matrix_world@v.co).z for v in head.data.vertices)
 scale=top/1.7522676
 rig['HelmetStyle']=0;rig.id_properties_ui('HelmetStyle').update(min=0,max=2,description='0 Padded Open Face (Century reference); 1 Vented Foam (adidas reference); 2 Perforated Foam (Daedo reference)')
 for i,o in enumerate(sorted(objects,key=lambda o:STYLES.index(next(s for s in STYLES if s in o.name)))):
  o.name='Helmet_'+STYLES[i]
  for v in o.data.vertices:v.co*=scale
  if profile!='Preview':suite.decimate(o,{'Gameplay_High':30000,'Gameplay_Mid':18000,'Gameplay_Far':8500}[profile])
  o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(o.data.vertices))),1,'REPLACE');suite.bind(o,rig)
  o['ReferenceURL']=URLS[i];o['Design']='Unbranded visual interpretation; no product certification implied.'
  for attr in ['hide_render','hide_viewport']:
   suite.driver(o,attr,rig,'HelmetStyle',f'x != {i}');d=o.animation_data.drivers.find(attr).driver;v=d.variables.new();v.name='w';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Helmet"]';d.expression=f'(x!={i}) or (not w)'
 rig['Wear_Helmet']=True;rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 catalog=json.loads((OUT/kind/'catalog.json').read_text());catalog['variants']['Helmet']=[{'style':s,'object':'Helmet_'+s,'reference':u} for s,u in zip(STYLES,URLS)]
 if profile!='Preview':
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
  finish.export(rig,meshes,OUT/kind/(profile+'_Sparring.fbx'))
  counts={};deps=bpy.context.evaluated_depsgraph_get()
  for o in meshes:
   if not o.hide_render:
    e=o.evaluated_get(deps);m=e.to_mesh();m.calc_loop_triangles();counts[o.name]=len(m.loop_triangles);e.to_mesh_clear()
  catalog['profiles'][profile]['visible_evaluated_triangles']=counts;catalog['profiles'][profile]['visible_total']=sum(counts.values())
 (OUT/kind/'catalog.json').write_text(json.dumps(catalog,indent=2))
 if kind=='Medium' and profile=='Preview':
  scene=bpy.context.scene;cam=scene.camera;cam.location=(.55,-1.0,1.76);cam.rotation_euler=(Vector((0,-.01,1.64))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.48
  scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
  if scene.render.engine=='CYCLES':scene.cycles.samples=32
  for i,style in enumerate(STYLES):
   rig['HelmetStyle']=i;rig.update_tag();scene.frame_set(i+2);bpy.context.view_layer.update();scene.render.filepath=str(OUT/('Helmet_'+style+'.png'));bpy.ops.render.render(write_still=True)
 log((kind,profile,'complete'))
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Medium','Compact','Stocky','LeanTall','Tall']
  for kind in args:
   for profile in ['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far']:install(kind,profile)
 except:log(traceback.format_exc());raise
