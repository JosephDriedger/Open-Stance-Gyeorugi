"""Staged follow-up repairs; retain skeleton, anatomy and authored actions."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import repair_sparring_fit as fit
import repair_visual_fit as util
import audit_sparring_styles as review
import repair_rom_garments as rom
ROOT=fit.ROOT
OUT=ROOT/'Resources/Models/FollowupFix'
OUT.mkdir(exist_ok=True)

def relax(points,mesh,weights,iterations=12):
 adj=[set() for _ in points]
 for e in mesh.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 for _ in range(iterations):
  prev=[p.copy() for p in points]
  for i,ns in enumerate(adj):
   if ns and weights[i]>0:points[i]=prev[i].lerp(sum((prev[j] for j in ns),Vector())/len(ns),.45*weights[i])
 return points

def repair(scene):
 if scene.get('FollowupFix')=='2026-10-21':return {'already_repaired':True}
 r=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 states={o:o.data.pose_position for o in scene.objects if o.type=='ARMATURE'}
 for o in states:o.data.pose_position='REST'
 bpy.context.view_layer.update();rows={}
 # The protector is padded equipment: prevent adjacent spine segments denting it.
 for o in scene.objects:
  if o.type!='MESH' or not o.name.startswith(('Quilted_Lace_Back__','Smooth_Buckle_Back__')):continue
  pts=[o.matrix_world@v.co for v in o.data.vertices]
  # Remove the low-front concavity with the same field on shell, trim and seams.
  util.shift(o,[Vector((0,-.028*scale*math.exp(-((p.z/scale-1.09)/.055)**2)*util.smooth((-p.y/scale-.06)/.08),0)) for p in pts])
  bones=[g for g in o.vertex_groups if g.name in r.data.bones]
  for g in bones:o.vertex_groups.remove(g)
  # One common lower-shell transform; yoke follows upper chest gradually.
  low=o.vertex_groups.get('spine_02') or o.vertex_groups.new(name='spine_02')
  mid=o.vertex_groups.get('spine_03') or o.vertex_groups.new(name='spine_03')
  high=o.vertex_groups.get('spine_05') or o.vertex_groups.new(name='spine_05')
  for v,p in zip(o.data.vertices,pts):
   t=util.smooth((p.z/scale-1.03)/.17)
   u=util.smooth((p.z/scale-1.25)/.15)
   low.add([v.index],1-t,'REPLACE')
   if t*(1-u):mid.add([v.index],t*(1-u),'REPLACE')
   if t*u:high.add([v.index],t*u,'REPLACE')
 # Continuous crown taper instead of the cylindrical rear silhouette.
 for o in scene.objects:
  if o.type!='MESH' or not o.name.startswith(tuple(n+'__' for n in review.build.HELMETS)):continue
  ds=[]
  for v in o.data.vertices:
   p=o.matrix_world@v.co;q=p.copy()
   crown=util.smooth((p.z/scale-1.68)/.11)
   q.x*=1-.14*crown
   q.y=.002*scale+(p.y-.002*scale)*(1-.12*crown)
   rear=util.smooth((p.y/scale-.015)/.075)
   q.y-=.006*scale*rear*(1-crown)
   ds.append(q-p)
  util.shift(o,ds)
 # Refine coarse cap tessellation before projecting it outside the evaluated scalp.
 surface=fit.tree(bpy.data.objects['Head'],True)
 center=Vector((0,.002,1.650))*scale
 hair=[]
 for o in list(scene.objects):
  if o.type!='MESH' or 'Scalp_Coverage' not in o.name:continue
  if len(o.data.vertices)<1300:
   hidden=o.hide_viewport
   drivers=[(d,d.mute) for d in o.animation_data.drivers if d.data_path=='hide_viewport'] if o.animation_data else []
   for d,_ in drivers:d.mute=True
   o.hide_viewport=False
   bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
   bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.subdivide(number_cuts=1,smoothness=0);bpy.ops.object.mode_set(mode='OBJECT')
   o.hide_viewport=hidden
   for d,m in drivers:d.mute=m
  inv=o.matrix_world.inverted();keys=o.data.shape_keys
  blocks=list(keys.key_blocks) if keys else [o.data]
  count=0
  for block in blocks:
   data=block.data if keys else block.vertices
   for v in data:
    p=o.matrix_world@v.co;axis=(p-center).normalized()
    hit=surface.ray_cast(center+axis*.35*scale,-axis,.35*scale)[0]
    if hit is None:continue
    clearance=.004*scale if keys and block.name=='HelmetFit' else .005*scale
    need=(hit-center).length+clearance
    if (p-center).length<need:v.co=inv@(center+axis*need);count+=1
  if keys:
   for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
  hair.append({'name':o.name,'vertices':len(o.data.vertices),'adjusted':count})
 rows['hair']=hair
 for o,state in states.items():o.data.pose_position=state
 bpy.context.view_layer.update()
 # Single-leg corrections complement the existing two-leg squat morph.
 action=r.animation_data.action if r.animation_data else None
 r.animation_data_create();r.animation_data.action=None
 tracks=[(t,t.mute) for t in r.animation_data.nla_tracks]
 for t,_ in tracks:t.mute=True
 pose=[(p,p.matrix_basis.copy(),p.rotation_mode) for p in r.pose.bones]
 props={k:r[k] for k in ['BlenderCloth'] if k in r}
 r['BlenderCloth']=False
 key_states=[]
 for o in scene.objects:
  if o.type=='MESH' and o.data.shape_keys:
   ks=o.data.shape_keys
   key_states.append((ks,ks.animation_data.action if ks.animation_data else None,[(k,k.value) for k in ks.key_blocks]))
   if ks.animation_data:ks.animation_data.action=None
   for k in ks.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
 for side in 'lr':
  review.audit.pose(r,'Knee_'+side.upper(),scale)
  for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
   o=bpy.data.objects.get(name)
   if not o:continue
   rest=[o.matrix_world@v.co for v in o.data.vertices]
   mats=[rom.skin_matrix(r,o,v) for v in o.data.vertices]
   pts=[m@p for m,p in zip(mats,rest)]
   sign=1 if side=='l' else -1
   weights=[util.smooth((p.z/scale-.65)/.12)*util.smooth((.97-p.z/scale)/.055)*util.smooth((sign*p.x/scale+.025)/.075) for p in rest]
   target=relax([p.copy() for p in pts],o.data,weights,20 if name=='Pants' else 14)
   if name!='Pants':
    tree=rom.mesh_tree(bpy.data.objects['Pants'])
    for i,p in enumerate(target):
     if weights[i]<.1:continue
     hit,n,_,dist=tree.find_nearest(p)
     if hit is not None and dist<.07*scale and (p-hit).dot(n)<.006*scale:target[i]=hit+n*.008*scale
   if not o.data.shape_keys:o.shape_key_add(name='Basis')
   key=o.shape_key_add(name='HipFlex_Clearance_'+side)
   inv=o.matrix_world.inverted()
   for v,p,m in zip(key.data,target,mats):v.co=inv@m.inverted_safe()@p
   d=key.driver_add('value').driver
   for s in 'lr':
    var=d.variables.new();var.name=s;var.targets[0].id=r;var.targets[0].data_path=f'pose.bones["thigh_{s}"].rotation_quaternion[0]'
   other='r' if side=='l' else 'l'
   angle=2*math.acos(min(1,abs(r.pose.bones['thigh_'+side].rotation_quaternion.w)))
   d.expression=f'max(0,min(1,(2*acos(min(1,abs({side})))-0.5)/{max(.2,angle-.5):.8f}))*max(0,1-max(0,(2*acos(min(1,abs({other})))-0.5)/0.4))'
   o['PreserveExportShapeKeys']=True
   bpy.context.view_layer.update()
 for ks,a,vals in key_states:
  if ks.animation_data:ks.animation_data.action=a
  for k,value in vals:k.value=value
 for p,m,mode in pose:p.rotation_mode=mode;p.matrix_basis=m
 r.animation_data.action=action
 for t,m in tracks:t.mute=m
 for k,v in props.items():r[k]=v
 scene['FollowupFix']='2026-10-21';bpy.context.view_layer.update()
 return rows

if __name__=='__main__':
 try:
  for kind,level in [('Medium','Gameplay_High'),('Tall','Crowd_Far'),('LeanTall','Crowd_Near')]:
   s,r,z,src=review.load(kind,level);rows=repair(s);d=OUT/'Pilot4'/kind;d.mkdir(parents=True,exist_ok=True)
   bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(d/(level+'.blend')),compress=True)
   s.cycles.samples=16
   if level.startswith('Crowd'):
    r['Wear_Helmet']=False;r['HairStyle']=4 if kind=='Tall' else 3;review.build.refresh(r)
    review.render(s,r,z,d,'Hair',(.4,-1,1.9),(0,0,1.65),.5,480,480)
   else:
    for pose in ['Knee_L','Front_Kick_L','Deep_Squat','Neutral']:
     for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=True
     review.build.refresh(r);review.audit.pose(r,pose,z)
     review.render(s,r,z,d,pose,(4,-.8,1.7) if pose in ['Knee_L','Front_Kick_L'] else (1.3,-4,1.8),(0,0,.96),2.35,640,720)
   (d/'repair.json').write_text(json.dumps(rows,indent=2))
  (OUT/'pilot_complete.txt').write_text('complete')
 except:(OUT/'error.log').write_text(traceback.format_exc());raise

