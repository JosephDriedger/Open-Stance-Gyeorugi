"""Fit the sleeve shells, low-LOD scalp and lower protector without changing rigs."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_fighter_range as audit
ROOT=Path('D:/Open-Stance-Gyeorugi');OUT=ROOT/'Resources/Models/VisualFitRepair';OUT.mkdir(exist_ok=True)
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def shift(o,deltas):
 inv=o.matrix_world.to_3x3().inverted()
 if o.data.shape_keys:
  for key in o.data.shape_keys.key_blocks:
   for v,d in zip(key.data,deltas):v.co+=inv@d
  for v,k in zip(o.data.vertices,o.data.shape_keys.key_blocks[0].data):v.co=k.co
 else:
  for v,d in zip(o.data.vertices,deltas):v.co+=inv@d
 o.data.update()
def repair(scene):
 if scene.get('VisualFitRepair')=='2026-10-16':return {'already_repaired':True}
 r=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 body=bpy.data.objects['Body'];points=[body.matrix_world@v.co for v in body.data.vertices]
 tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in body.data.polygons])
 segments=[]
 for side in ['l','r']:
  for start,end in [('upperarm','lowerarm'),('lowerarm','hand')]:
   a=r.matrix_world@r.data.bones[start+'_'+side].head_local;b=r.matrix_world@r.data.bones[end+'_'+side].head_local
   segments.append((a,b))
 sleeves={}
 for name in ['Jacket','Jacket_WhiteVNeck']:
  o=bpy.data.objects.get(name)
  if not o:continue
  deltas=[]
  for v in o.data.vertices:
   q=o.matrix_world@v.co
   if abs(q.x)<.24*scale:deltas.append(Vector());continue
   choices=[]
   for a,b in segments:
    axis=b-a;t=max(0,min(1,(q-a).dot(axis)/axis.length_squared));c=a+t*axis;choices.append(((q-c).length,c))
   radius,c=min(choices,key=lambda x:x[0]);direction=(q-c).normalized()
   hit=tree.ray_cast(c,direction,.16*scale)[0]
   delta=Vector()
   if hit is not None:
    needed=(hit-c).length+.018*scale
    if radius<needed:delta=direction*(needed-radius)*smooth((abs(q.x)/scale-.24)/.06)
   deltas.append(delta)
  # Spread clearance to nearby faces, without averaging away required offsets.
  adj=[set() for _ in deltas]
  for e in o.data.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
  for _ in range(4):
   old=[d.copy() for d in deltas]
   for i,ns in enumerate(adj):
    if ns:
     avg=sum((old[j] for j in ns),Vector())/len(ns)
     if avg.length>old[i].length:deltas[i]=old[i]*.5+avg*.5
  shift(o,deltas);sleeves[name]={'max_offset_m':max(d.length for d in deltas),'vertices_adjusted':sum(d.length>1e-6 for d in deltas)}
 # Keep shell, binding and stitching together. Flatten only the low front flare.
 protector_count=0
 for o in scene.objects:
  if o.type!='MESH' or not o.name.startswith(('Quilted_Lace_Back__','Smooth_Buckle_Back__')):continue
  deltas=[]
  for v in o.data.vertices:
   p=o.matrix_world@v.co;amount=.092*scale*smooth((1.23-p.z/scale)/.27)*smooth((-p.y/scale-.07)/.10)
   deltas.append(Vector((0,amount,0)))
  shift(o,deltas);protector_count+=1
 # Coarse cap chords cut through the scalp; add just enough sampling and clearance.
 scalp=next((o for o in scene.objects if 'Hair_Crew_Cut__Scalp_Coverage' in o.name),None)
 hair=[]
 if scalp and len(scalp.data.vertices)<=608:
  path=Path(__file__).with_name('repair_hair_surface.py');code=path.read_text().split("if __name__=='__main__':")[0]
  code=code.replace('608:(32,19),416:(32,13),160:(16,10)','608:(32,19),416:(32,19),160:(32,19)').replace('d*.0015*scale','d*.004*scale').replace('d*.0008*scale','d*.003*scale')
  scope={'__file__':str(path),'__name__':'visual_fit_hair'};exec(compile(code,str(path),'exec'),scope);hair=scope['repair'](scene)
 scene['VisualFitRepair']='2026-10-16'
 return {'sleeves':sleeves,'protector_parts':protector_count,'coarse_hair':hair}
def pilot(kind,level):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite'/kind/(level+'.blend')))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];rows=repair(s)
 d=OUT/'Pilots'/kind;d.mkdir(parents=True,exist_ok=True)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(d/(level+'.blend')),compress=True)
 r.animation_data_create();r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 s.cycles.samples=12;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 for gear in [False,True]:
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
  r['JacketStyle']=int(gear);audit.build.refresh(r)
  for label in (['Neutral','Knee_L','Arms_Overhead'] if not level.startswith('Crowd') else ['Crowd']):
   if label=='Crowd':r.animation_data.action=bpy.data.actions['Crowd_StandingIdle'];s.frame_set(16)
   else:audit.pose(r,label,scale)
   for view,pos in [('Front',(1,-4,1.6)),('Back',(0,4,1.6)),('Side',(4,0,1.6))]:
    audit.build.view.camera(s,tuple(c*scale for c in pos),(0,0,.96*scale),2.35*scale)
    s.render.filepath=str(d/f'{level}_{int(gear)}_{label}_{view}.png');bpy.ops.render.render(write_still=True)
 (d/(level+'_repair.json')).write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
 try:
  for kind,level in [('Compact','Gameplay_High'),('Tall','Gameplay_High'),('Compact','Crowd_Far'),('Medium','Gameplay_High')]:pilot(kind,level)
 except:(OUT/'pilot_error.log').write_text(traceback.format_exc());raise
