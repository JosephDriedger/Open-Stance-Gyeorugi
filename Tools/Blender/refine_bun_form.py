"""Replace the disk-like bun with a rounded, combed coil; preserve wardrobe rig."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as audit
ROOT=audit.ROOT;OUT=ROOT/'Resources/Models/HairFormRefinement';OUT.mkdir(exist_ok=True)

def repair(scene):
 if scene.get('HairFormRefinement')=='2026-10-19':return {'already_repaired':True}
 rig=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
 core=next((o for o in scene.objects if o.name.split('.')[0]=='Hair_Compact_Bun__Coiled_Bun_Core'),None)
 fibers=next((o for o in scene.objects if o.name.split('.')[0]=='Hair_Compact_Bun__Coiled_Bun'),None)
 if not core or not fibers:return {'no_bun':True}
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 keys=core.data.shape_keys.key_blocks
 def bounds(block):
  ps=[core.matrix_world@v.co for v in block.data];lo=Vector(tuple(min(p[i] for p in ps) for i in range(3)));hi=Vector(tuple(max(p[i] for p in ps) for i in range(3)))
  return (lo+hi)*.5,(hi-lo)*.5
 center,radius=bounds(keys[0]);fitted,_=bounds(keys['HelmetFit']);delta=fitted-center
 delta.y-=.030*scale
 center.y-=.012*scale
 # Existing attachment and dimensions remain, with a little more depth and less perfect circular symmetry.
 radius.x*=1.10;radius.y*=1.20;radius.z*=.92
 # Fit the attachment against each preset's actual head/neck, not a shared offset.
 import repair_sparring_fit as surfaces
 poses={o:o.data.pose_position for o in scene.objects if o.type=='ARMATURE'}
 for o in poses:o.data.pose_position='REST'
 bpy.context.view_layer.update();tree=surfaces.tree(bpy.data.objects['Head'],True)
 fitcenter=center+delta
 for target in [center,fitcenter]:
  hit=tree.ray_cast(Vector((target.x,.4*scale,target.z)),Vector((0,-1,0)),.6*scale)[0]
  if hit is not None:target.y=hit.y+radius.y-.004*scale
 delta=fitcenter-center
 for o,value in poses.items():o.data.pose_position=value
 bpy.context.view_layer.update()

 def point(a,p,offset=0):
  ripple=1+.05*math.cos(10*a+3*p)*math.sin(p)+.025*math.sin(3*a)*math.sin(p)**2
  q=Vector((radius.x*math.sin(p)*math.cos(a)*ripple,radius.y*math.cos(p)*ripple,radius.z*math.sin(p)*math.sin(a)*ripple))
  normal=Vector((q.x/radius.x**2,q.y/radius.y**2,q.z/radius.z**2)).normalized()
  return center+q+normal*offset,normal
 def replace(o,points,faces):
  mats=list(o.data.materials);mesh=bpy.data.meshes.new(o.name+'_RoundedCoil');inv=o.matrix_world.inverted();mesh.from_pydata([inv@p for p in points],[],faces);mesh.update();o.data=mesh
  for m in mats:mesh.materials.append(m)
  for poly in mesh.polygons:poly.use_smooth=True
  o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(points))),1,'REPLACE')
  o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
  for v,p in zip(key.data,points):v.co=inv@(p+delta)
  driver=key.driver_add('value').driver;var=driver.variables.new();var.name='helmet';var.targets[0].id=rig;var.targets[0].data_path='["Wear_Helmet"]';driver.expression='1 if helmet else 0'
  o['HairFormRefinement']='Rounded coil with scalp-facing attachment and helmet offset'
 # Scale strand count with the existing LOD instead of using Preview density everywhere.
 high=len(fibers.data.vertices)>10000;cols,rows=(48,24) if high else (24,16)
 n,steps=(180,24) if high else (56,16)
 level=Path(bpy.data.filepath).stem
 if level=='Crowd_Far':cols,rows,n,steps=12,8,12,10
 elif level=='Crowd_Near':cols,rows,n,steps=16,12,24,12
 elif level=='Gameplay_Far':cols,rows,n,steps=24,16,32,14
 points=[];faces=[]
 for j in range(rows+1):
  p=.001+(math.pi-.002)*j/rows
  for i in range(cols):points.append(point(math.tau*i/cols,p)[0])
 for j in range(rows):
  for i in range(cols):faces.append((j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i))
 faces += [tuple(reversed(range(cols))),tuple(rows*cols+i for i in range(cols))]
 replace(core,points,faces)
 points=[];faces=[]
 for strand in range(n):
  phase=math.tau*strand/n;start=len(points)
  for j in range(steps):
   t=j/(steps-1);end=.025+.10*(1+math.sin(strand*2.39))*.5;p=2.8-(2.8-end)*t;a=phase+1.8*t
   q,normal=point(a,p,.00035*scale);tangent=Vector((-math.sin(a),0,math.cos(a)));across=normal.cross(tangent).normalized()
   thickness=.00024*scale*(.7+.3*math.sin(math.pi*t))
   for k in range(3):points.append(q+thickness*(normal*math.cos(math.tau*k/3)+across*math.sin(math.tau*k/3)))
   if j:
    for k in range(3):faces.append((start+(j-1)*3+k,start+(j-1)*3+(k+1)%3,start+j*3+(k+1)%3,start+j*3+k))
 replace(fibers,points,faces)
 tie=next((o for o in scene.objects if o.name.split('.')[0]=='Hair_Compact_Bun__Hair_Tie'),None)
 if tie:
  points=[];faces=[];rings=48;sides=6
  for i in range(rings):
   a=math.tau*i/rings;q=center+Vector((radius.x*.72*math.cos(a),-radius.y*.72,radius.z*.72*math.sin(a)))
   radial=Vector((math.cos(a),0,math.sin(a)))
   for j in range(sides):points.append(q+.0015*scale*(radial*math.cos(math.tau*j/sides)+Vector((0,math.sin(math.tau*j/sides),0))))
  for i in range(rings):
   for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%rings)*sides+(j+1)%sides,((i+1)%rings)*sides+j))
  replace(tie,points,faces)
 scene['HairFormRefinement']='2026-10-19'
 return {'lod_budgeted':True,'bun_core_vertices':len(core.data.vertices),'bun_fiber_vertices':len(fibers.data.vertices),'helmet_translation':list(delta)}

if __name__=='__main__':
 try:
  for kind,level in [('Medium','Preview'),('Female_Athletic','Gameplay_High')]:
   s,r,z,src=audit.load(kind,level);changes=repair(s);d=OUT/'PilotF'/kind;d.mkdir(parents=True,exist_ok=True)
   s.cycles.samples=32;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(d/(level+'.blend')),compress=True)
   r['HairStyle']=5
   for gear in [False,True]:
    for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
    r['HelmetDesign']=1;audit.build.refresh(r)
    for side,pos in [('Rear',(.45,1,1.8)),('Side',(.9,.35,1.78))]:audit.render(s,r,z,d,f'{int(gear)}_{side}',pos,(0,.05,1.65),.45,640,640)
   (d/'repair.json').write_text(json.dumps(changes,indent=2))
  (OUT/'pilot_complete.txt').write_text('Complete')
 except:(OUT/'pilot_error.log').write_text(traceback.format_exc());raise
