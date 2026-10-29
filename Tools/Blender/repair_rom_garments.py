"""Stage reusable garment repairs without changing production files."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));import audit_fighter_range as audit
ROOT=audit.ROOT;OUT=ROOT/'Resources/Models/ROMRepair';OUT.mkdir(exist_ok=True)
PARTS=['Jacket','Belt','Belt_Waistband','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back','Belt_Tail_Left','Belt_Tail_Right']
def log(s):
 with (OUT/'repair.log').open('a') as f:f.write(str(s)+'\n')
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
def prep():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'))
 ref=points(bpy.data.objects['Jacket']);belt=points(bpy.data.objects['Belt'])
 meta={'shirt':[list(p) for p in ref],'belt_width':max(p.x for p in belt)-min(p.x for p in belt),'belt_depth':max(p.y for p in belt)-min(p.y for p in belt)}
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend'));r=bpy.data.objects['RIG_Body_Medium'];r.data.pose_position='REST';bpy.context.view_layer.update();meta['pelvis']=list(r.matrix_world@r.data.bones['pelvis'].head_local)
 objects=[]
 for name in PARTS:
  o=bpy.data.objects[name]
  if o.data.shape_keys:o.shape_key_clear()
  world=o.matrix_world.copy();ws=max(world.to_scale());coords=points(o);o.parent=None;o.matrix_world=Matrix()
  for v,p in zip(o.data.vertices,coords):v.co=p
  for m in o.modifiers:
   if m.type=='SOLIDIFY':m.thickness*=ws
  objects.append(o)
 bpy.data.libraries.write(str(OUT/'Garment_Template.blend'),set(objects),fake_user=True,compress=True);(OUT/'template.json').write_text(json.dumps(meta));log('TEMPLATE READY')
def skin_matrix(r,o,v):
 m=Matrix(((0,0,0,0),)*4);total=0
 for g in v.groups:
  name=o.vertex_groups[g.group].name
  if name not in r.pose.bones:continue
  t=r.matrix_world@r.pose.bones[name].matrix@r.data.bones[name].matrix_local.inverted()@r.matrix_world.inverted();m+=t*g.weight;total+=g.weight
 return m*(1/total) if total else Matrix()
def mesh_tree(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();tree=BVHTree.FromPolygons([o.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);ev.to_mesh_clear();return tree
def repair(kind):
 source=ROOT/'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend' if kind=='Updated_Medium' else ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));old_action=r.animation_data.action if r.animation_data else None;r.animation_data_create();r.animation_data.action=None
 for track in r.animation_data.nla_tracks:track.mute=True
 for p in r.pose.bones:p.matrix_basis=Matrix();p.rotation_mode='QUATERNION'
 r.data.pose_position='REST';bpy.context.view_layer.update();scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.57778847
 meta=json.loads((OUT/'template.json').read_text());srcshirt=[Vector(p) for p in meta['shirt']];oldshirt=bpy.data.objects['Jacket'];dstshirt=points(oldshirt);oldbelt=points(bpy.data.objects['Belt']);pelvis=r.matrix_world@r.data.bones['pelvis'].head_local
 if kind=='Updated_Medium':sx=sy=1
 else:sx=(max(p.x for p in oldbelt)-min(p.x for p in oldbelt))/meta['belt_width'];sy=(max(p.y for p in oldbelt)-min(p.y for p in oldbelt))/meta['belt_depth']
 tree=KDTree(len(srcshirt))
 for i,p in enumerate(srcshirt):tree.insert(p,i)
 tree.balance()
 selected_parts=[name for name in PARTS if kind!='Updated_Medium' or not name.startswith('Belt_Tail_')]
 for name in selected_parts:
  o=bpy.data.objects.get(name)
  if o:bpy.data.objects.remove(o,do_unlink=True)
 before=set(bpy.data.objects)
 with bpy.data.libraries.load(str(OUT/'Garment_Template.blend'),link=False) as (a,b):b.objects=list(selected_parts)
 for o in b.objects:
  s.collection.objects.link(o);o.name=o.name.split('.')[0]
  for v in o.data.vertices:
   q=v.co.copy()
   if o.name=='Jacket':
    blend=max(0,min(1,(abs(q.x)-.22)/.25));local_sx=sx*(1-blend)+blend
    v.co=Vector((q.x*local_sx,q.y*sy,pelvis.z+(q.z-meta['pelvis'][2])*scale))
   else:v.co=Vector((q.x*sx,q.y*sy,pelvis.z+(q.z-meta['pelvis'][2])*scale))
  for m in o.modifiers:
   if m.type=='ARMATURE':m.object=r
  for owner in [o,o.data.shape_keys]:audit.build.redirect(owner,r)
  # All uniform parts follow the existing jacket visibility switch.
  for channel in ['hide_render','hide_viewport']:
   try:o.driver_remove(channel)
   except:pass
   d=o.driver_add(channel).driver;v=d.variables.new();v.name='wear';v.targets[0].id=r;v.targets[0].data_path='["Wear_Jacket"]';d.expression='not wear'
 for o in list(bpy.data.objects):
  if o not in before and o not in b.objects and o.type=='ARMATURE':bpy.data.objects.remove(o,do_unlink=True)
 # Mask covered skin, including the underarm strips missed by the previous mask.
 body=bpy.data.objects['Body'];group=body.vertex_groups.get('CoveredBy_Jacket');arm=r.matrix_world@r.data.bones['upperarm_l'].head_local;covered=[]
 for v in body.data.vertices:
  q=body.matrix_world@v.co
  if abs(q.x)<arm.x+.065*scale and pelvis.z+.08*scale<q.z<arm.z+.055*scale:covered.append(v.index)
 group.add(covered,1,'REPLACE')
 # The existing cotton surfaces overlap at the armpit; mask hidden skin
 # rather than add a duplicate shell that can poke through at rest.
 # Correct the trousers at the fitted waistband without changing lower-leg weights.
 pants=bpy.data.objects['Pants'];pants_inv=pants.matrix_world.inverted();band=bpy.data.objects['Belt_Waistband'];profile=[]
 for i in range(128):profile.append(band.data.vertices[i].co.xy.length-.012*scale)
 def radius(q):
  a=math.atan2(q.x,-q.y)%math.tau;t=a/math.tau*128;i=int(t);return profile[i]*(1-(t-i))+profile[(i+1)%128]*(t-i)
 ztop=pelvis.z+(.945-meta['pelvis'][2])*scale;zlow=ztop-.075*scale;pg=pants.vertex_groups.get('pelvis')
 for v in pants.data.vertices:
  q=pants.matrix_world@v.co;t=max(0,min(1,(q.z-zlow)/(ztop-zlow)));t=t*t*(3-2*t)
  if not t:continue
  d=Vector((q.x,q.y,0)).normalized();target=d*min(q.xy.length,radius(q));q.x+=(target.x-q.x)*t;q.y+=(target.y-q.y)*t;v.co=pants_inv@q
  old=[(g.group,g.weight) for g in v.groups];prior=next((w for i,w in old if i==pg.index),0)
  for i,w in old:pants.vertex_groups[i].add([v.index],w*(1-t),'REPLACE')
  pg.add([v.index],prior*(1-t)+t,'REPLACE')
 # Portable cotton materials and correctly scaled thickness for the original pants.
 pants.data.materials.clear();pants.data.materials.append(bpy.data.objects['Jacket'].data.materials[0])
 for m in pants.modifiers:
  if m.type=='SOLIDIFY':m.thickness=.0014/max(pants.matrix_world.to_scale())
 # Fit each preset's lower panels to its actual trousers, keeping the top
 # rows unchanged beneath the fitted belt.
 bpy.context.view_layer.update();rest_tree=mesh_tree(pants)
 for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  o=bpy.data.objects[name];cols=41 if name=='Jacket_Back' else 25
  for v in o.data.vertices:
   row=v.index//cols
   if row<4:continue
   q=v.co.copy();d=Vector((q.x,q.y,0)).normalized();origin=d*.5*scale;origin.z=q.z
   hit=rest_tree.ray_cast(origin,-d,.5*scale)[0]
   if hit is not None:
    radius_target=max(q.xy.length,hit.xy.length+.012*scale)
    q.x,q.y=(d*radius_target).xy;v.co=q
 # Separate overlapping wrap edges by a few millimetres to avoid coincident faces.
 for name,offset in [('Jacket_Front_Left',.0015),('Jacket_Back',-.002),('Jacket_Front_Right',.0005)]:
  for v in bpy.data.objects[name].data.vertices:
   d=Vector((v.co.x,v.co.y,0)).normalized();v.co+=d*offset*scale
 bodypants=body.vertex_groups.get('CoveredBy_Pants')
 for v in body.data.vertices:
  q=body.matrix_world@v.co
  if pelvis.z-.25*scale<q.z<pelvis.z+.025*scale and abs(q.x)<.25*sx:bodypants.add([v.index],1,'REPLACE')
 r.data.pose_position='POSE';audit.pose(r,'Deep_Squat',scale);bpy.context.view_layer.update()
 # Smooth the lower panel surface in the failed squat, then store a pose-driven
 # corrective in pre-skin coordinates rather than a frame-specific patch.
 # Soften the trouser crease first, otherwise jacket contact reproduces it.
 source_world=points(pants);transforms_p=[skin_matrix(r,pants,v) for v in pants.data.vertices]
 posed_p=[m@q for m,q in zip(transforms_p,source_world)];adj=[set() for _ in posed_p]
 for e in pants.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 smooth_weights=[]
 for q in source_world:
  z=(q.z-pelvis.z)/scale
  smooth_weights.append(max(0,min(1,(z+.29)/.09,(.05-z)/.08)))
 for _ in range(24):
  prev=[q.copy() for q in posed_p]
  for i,neighbors in enumerate(adj):
   if neighbors and smooth_weights[i]:posed_p[i]=prev[i].lerp(sum((prev[j] for j in neighbors),Vector())/len(neighbors),.65*smooth_weights[i])
 pants.shape_key_add(name='Basis');pk=pants.shape_key_add(name='Squat_Fold_Soften')
 for v,q,m in zip(pk.data,posed_p,transforms_p):v.co=pants.matrix_world.inverted()@m.inverted()@q
 driver=pk.driver_add('value').driver
 for side in 'lr':
  v=driver.variables.new();v.name=side;v.targets[0].id=r;v.targets[0].data_path=f'pose.bones["thigh_{side}"].rotation_quaternion[0]'
 target_angle=min(2*math.acos(min(1,abs(r.pose.bones['thigh_'+side].rotation_quaternion.w))) for side in 'lr')
 driver.expression=f'max(0,min(1,(min(2*acos(min(1,abs(l))),2*acos(min(1,abs(r))))-0.65)/{max(.1,target_angle-.65):.8f}))'
 pants['PreserveExportShapeKeys']=True;bpy.context.view_layer.update()
 trouser_tree=mesh_tree(pants)
 for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
  o=bpy.data.objects[name];cols=41 if name=='Jacket_Back' else 25;rest=[v.co.copy() for v in o.data.vertices];transforms=[skin_matrix(r,o,v) for v in o.data.vertices];posed=[m@p for m,p in zip(transforms,rest)]
  for repeat in range(16):
   prev=[p.copy() for p in posed]
   for row in range(4,24):
    for col in range(1,cols-1):
     i=row*cols+col;posed[i]=prev[i]*.5+(prev[i-1]+prev[i+1]+prev[i-cols]+prev[i+cols])*.125
   for i,p in enumerate(posed):
    if i<cols*4:continue
    hit,n,_,dist=trouser_tree.find_nearest(p)
    if hit is not None and dist<.1*scale and (p-hit).dot(n)<.006*scale:posed[i]=hit+n*.008*scale
  o.shape_key_add(name='Basis');key=o.shape_key_add(name='Squat_Clearance')
  for v,p,m in zip(key.data,posed,transforms):v.co=m.inverted()@p
  driver=key.driver_add('value').driver
  for side in 'lr':
   v=driver.variables.new();v.name=side;v.targets[0].id=r;v.targets[0].data_path=f'pose.bones["thigh_{side}"].rotation_quaternion[0]'
  target_angle=min(2*math.acos(min(1,abs(r.pose.bones['thigh_'+side].rotation_quaternion.w))) for side in 'lr')
  driver.expression=f'max(0,min(1,(min(2*acos(min(1,abs(l))),2*acos(min(1,abs(r))))-0.65)/{max(.1,target_angle-.65):.8f}))'
  o['PreserveExportShapeKeys']=True
 for p in r.pose.bones:p.matrix_basis=Matrix()
 s.frame_set(1);r.animation_data.action=old_action
 # Reusable files contain no sample-only cloth bake; the prior authored body actions remain.
 directory=OUT/kind;directory.mkdir(exist_ok=True);s['GarmentRevision']='ROM repair 2026-10-10';r.data.pose_position='POSE';bpy.context.view_layer.update()
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/('Medium_Sparring_Samples.blend' if kind=='Updated_Medium' else 'Gameplay_High.blend')))
 # Render the failures and nearby movements with the same audit pose generator.
 r.animation_data.action=None;s.render.resolution_x=640;s.render.resolution_y=720;s.cycles.samples=8
 for gear in [False,True]:
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
  audit.build.refresh(r)
  for label in ['Neutral','Arms_Overhead','Front_Kick_L','Deep_Squat']:
   audit.pose(r,label,scale);bpy.context.view_layer.update();audit.build.view.camera(s,(3*scale,-1*scale,1.55*scale),(0,-.05*scale,1.0*scale),1.25*scale)
   s.render.filepath=str(directory/f'{"Gear" if gear else "Dobok"}_{label}.png');bpy.ops.render.render(write_still=True)
 log(kind+' REVIEW READY')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:]
  if args==['prepare']:prep()
  else:
   for kind in args:repair(kind)
 except:log(traceback.format_exc());raise


