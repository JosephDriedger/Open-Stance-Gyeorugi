"""Restore rounded ear topology and separate collar fabric from the neck."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_sparring_fit as fit
ROOT=fit.ROOT
OUT=ROOT/'Resources/Models/CollarEarRepair'
def repair(scene):
 if scene.get('CollarEarRepair')=='2026-10-20':return {'already_repaired':True}
 rig=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
 kind=rig.name.removeprefix('RIG_Body_'); source=json.loads((OUT/'Prepared'/(kind+'.json')).read_text())
 filename=Path(bpy.data.filepath).stem
 count=24 if 'Far' in filename else 32 if 'Mid' in filename else 48
 cross=8 if count<48 else 16
 rows={}
 for o in scene.objects:
  if o.type!='MESH' or o.name not in source or len(o.data.vertices)>1000 or ('__Ear_Pad_Piping' in o.name and len(o.data.vertices)>100):continue
  data=source[o.name];ear='__Foam_Ear_' in o.name
  n,m=(count,cross) if ear else (count,4 if count<48 else 8)
  source_m=32 if ear else 8
  inv=o.matrix_world.inverted();points=[]
  for i in range(n):
   for j in range(m):points.append(inv@Vector(data['points'][(i*96//n)*source_m+j*source_m//m]))
  faces=[(i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m) for i in range(n) for j in range(m)]
  # Keep the source's winding: mirrored pads and piping have different winding.
  sf=data['faces'][0];sp=[Vector(data['points'][i]) for i in sf]
  reference=(sp[1]-sp[0]).cross(sp[2]-sp[0])
  wp=[o.matrix_world@points[i] for i in faces[0]]
  generated=(wp[1]-wp[0]).cross(wp[2]-wp[0])
  if generated.dot(reference)<0:faces=[tuple(reversed(f)) for f in faces]
  wp=[o.matrix_world@points[i] for i in faces[0]]
  assert (wp[1]-wp[0]).cross(wp[2]-wp[0]).dot(reference)>0,(o.name,'winding')
  mesh=bpy.data.meshes.new(o.name+'_Rounded');mesh.from_pydata(points,[],faces)
  for mat in o.data.materials:mesh.materials.append(mat)
  before=len(o.data.vertices);o.data=mesh;o.vertex_groups.clear();g=o.vertex_groups.new(name='head');g.add(list(range(len(points))),1,'REPLACE')
  for p in mesh.polygons:p.use_smooth=True
  rows[o.name]={'before':before,'after':len(points)}
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 poses={o:o.data.pose_position for o in scene.objects if o.type=='ARMATURE'}
 for o in poses:o.data.pose_position='REST'
 bpy.context.view_layer.update()
 surfaces=[fit.tree(bpy.data.objects[n],n=='Head') for n in ['Body','Head'] if bpy.data.objects.get(n)]
 for name in ['Jacket','Jacket_WhiteVNeck']:
  o=bpy.data.objects.get(name)
  if not o:continue
  ds=[]
  for v in o.data.vertices:
   p=o.matrix_world@v.co;d=Vector()
   if abs(p.x)<.145*scale and p.z>1.39*scale:
    for surface in surfaces:
     hit,normal,_,distance=surface.find_nearest(p+d)
     if hit is not None and distance<.022*scale:
      separation=(p+d-hit).dot(normal)
      if separation<.007*scale:d+=normal*min(.024*scale,.007*scale-separation)
   ds.append(d)
  # Blend offsets, preserving the width of the separate collar band.
  points=[o.matrix_world@v.co for v in o.data.vertices]
  neighbors=[set() for _ in points]
  for e in o.data.edges:
   a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
  for _ in range(4):
   prev=[d.copy() for d in ds]
   for i,ns in enumerate(neighbors):
    p=points[i]
    if ns and abs(p.x)<.145*scale and p.z>1.39*scale:
     ds[i]=prev[i].lerp(sum((prev[n] for n in ns),Vector())/len(ns),.5)
  for i,p in enumerate(points):
   if abs(p.x)<.145*scale and p.z>1.39*scale:
    for surface in surfaces:
     hit,normal,_,distance=surface.find_nearest(p+ds[i])
     if hit is not None and distance<.022*scale:
      sep=(p+ds[i]-hit).dot(normal)
      if sep<.007*scale:ds[i]+=normal*min(.024*scale,.007*scale-sep)
  fit.old.shift(o,ds);rows[name]={'moved':sum(d.length>1e-6 for d in ds),'max_offset':max(d.length for d in ds)}
 for o,pose in poses.items():o.data.pose_position=pose
 bpy.context.view_layer.update();scene['CollarEarRepair']='2026-10-20'
 return rows
if __name__=='__main__':
 import audit_sparring_styles as a
 import traceback
 try:
  for kind in ['Stocky','Tall']:
   s,r,z,src=a.load(kind,'Gameplay_High');d=OUT/'PilotV3'/kind;d.mkdir(parents=True,exist_ok=True)
   for state in ['Before','After']:
    if state=='After':(d/'repair.json').write_text(json.dumps(repair(s),indent=2))
    for j in range(2):
     r['JacketStyle']=j;r['HelmetDesign']=0;r['HairStyle']=0;r['Wear_Helmet']=False;r['Wear_Protector']=False;a.build.refresh(r)
     a.render(s,r,z,d,f'{state}_Collar{j}',(.5,.8,1.83),(0,0,1.47),.42,640,640)
    r['JacketStyle']=0;r['HelmetDesign']=1;r['HairStyle']=0;r['Wear_Helmet']=True;a.build.refresh(r)
    a.render(s,r,z,d,state+'_Ear',(.9,.25,1.72),(0,0,1.65),.42,640,640)
   bpy.ops.wm.save_as_mainfile(filepath=str(d/'Pilot.blend'),compress=True)
  (OUT/'pilot_complete.txt').write_text('Complete')
 except:(OUT/'pilot_error.txt').write_text(traceback.format_exc());raise

