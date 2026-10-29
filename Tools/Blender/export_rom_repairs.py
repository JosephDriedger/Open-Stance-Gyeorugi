import bpy,sys,math,json,traceback,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent));import repair_rom_garments as repair
build=repair.audit.build;ROOT=repair.ROOT;OUT=repair.OUT
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def curves(a):
 return list(a.fcurves) if hasattr(a,'fcurves') else [fc for l in a.layers for s in l.strips for b in s.channelbags for fc in b.fcurves]
def log(s):
 with (OUT/'exports.log').open('a') as f:f.write(str(s)+'\n')
def run():
 files=[]
 for kind in KINDS:
  folder=OUT/kind;bpy.ops.wm.open_mainfile(filepath=str(folder/'Gameplay_High.blend'));r=bpy.data.objects['RIG_Body_'+kind];r.animation_data.action=None
  for gear in [False,True]:
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
   build.refresh(r);path=folder/('Gameplay_High_'+('Sparring' if gear else 'Dobok')+'.fbx');build.export(r,path,False);files.append(path)
  log(kind+' exported')
 folder=OUT/'Updated_Medium';path=folder/'Medium_Sparring_Samples.blend';bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];pants=bpy.data.objects['Pants'];r.animation_data.action=bpy.data.actions['Sample_Demo']
 panels=[bpy.data.objects[n] for n in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']]
 for f in range(145,217):
  s.frame_set(f);bpy.context.view_layer.update();tree=repair.mesh_tree(pants)
  for o in panels:
   cols=41 if o.name=='Jacket_Back' else 25;rest=[v.co.copy() for v in o.data.vertices];transforms=[repair.skin_matrix(r,o,v) for v in o.data.vertices];posed=[m@q for m,q in zip(transforms,rest)]
   for repeat in range(3):
    prev=[p.copy() for p in posed]
    if repeat:
     for row in range(4,24):
      for col in range(1,cols-1):
       i=row*cols+col;posed[i]=prev[i]*.65+(prev[i-1]+prev[i+1]+prev[i-cols]+prev[i+cols])*.0875
    for i,p in enumerate(posed):
     if i<cols*4:continue
     hit,n,_,dist=tree.find_nearest(p)
     if hit is not None and dist<.1 and (p-hit).dot(n)<.006:posed[i]=hit+n*.008
   key=o.shape_key_add(name=f'ClothBake_{f-144:02d}')
   for v,p,m in zip(key.data,posed,transforms):v.co=m.inverted()@p
   for frame,value in [(1,0),(f-1,0),(f,1),(f+1,0),(218,0)]:key.value=value;key.keyframe_insert('value',frame=frame)
   key.value=0
 s.frame_start=1;s.frame_end=216;s.frame_set(1);build.view.camera(s,(2.5,-4,2),(0,-.15,.94),2.3);bpy.ops.wm.save_as_mainfile(filepath=str(path));log('Sample garment motion baked')
 cloth=panels+[bpy.data.objects[n] for n in ['Belt_Tail_Left','Belt_Tail_Right']];keys=[o.data.shape_keys for o in cloth];actions=[k.animation_data.action for k in keys]
 for k in keys:
  k.animation_data.action=None
  for block in k.key_blocks:
   if block.name.startswith('ClothBake'):block.value=0
 for clip in ['Guard_Idle','Straight_Punches']:
  r.animation_data.action=bpy.data.actions['Sample_'+clip];s.frame_start=1;s.frame_end=72;s.frame_set(1);export=folder/(clip+'.fbx');build.export(r,export,True);files.append(export)
 for k,a in zip(keys,actions):
  a=a.copy();k.animation_data.action=a
  for fc in curves(a):
   for p in fc.keyframe_points:p.co.x-=144;p.handle_left.x-=144;p.handle_right.x-=144
 r.animation_data.action=bpy.data.actions['Sample_Front_Kick'];s.frame_set(1);build.view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25);bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Front_Kick.blend'));export=folder/'Front_Kick.fbx';build.export(r,export,True);files.append(export)
 # Verify the shipped FBXs by importing the exported files, not in-memory copies.
 report=[]
 for p in files:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p));rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341,p
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert any(o.name.startswith('Belt_Waistband') for o in meshes)
  corrections={}
  for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
   o=next(o for o in meshes if o.name.split('.')[0]==name);assert o.data.shape_keys,name;assert any(k.name.startswith('Squat_') for k in o.data.shape_keys.key_blocks),name;corrections[name]=len(o.data.shape_keys.key_blocks)
  if not p.name.startswith('Gameplay'):
   assert rigs[0].animation_data.action and rigs[0].animation_data.action.frame_range[1]>=72
   if p.name=='Front_Kick.fbx':
    for f in [1,26,35,72]:
     bpy.context.scene.frame_set(f)
     for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
      o=next(o for o in meshes if o.name.split('.')[0]==name);assert abs(sum(k.value for k in o.data.shape_keys.key_blocks if k.name.startswith('ClothBake'))-1)<.02
  report.append({'file':str(p.relative_to(OUT)),'sha256':digest(p),'bones':341,'corrective_keys':corrections,'reimport_passed':True})
 (OUT/'export_validation.json').write_text(json.dumps({'files':report,'passed':True},indent=2));log('EXPORTS VERIFIED')
 # Reimported sample kick visual QA under the same lighting.
 for f in [1,26,35]:
  bpy.ops.wm.open_mainfile(filepath=str(folder/'Medium_Sparring_Samples.blend'))
  for o in list(bpy.data.objects):
   if o.type in {'ARMATURE','MESH'} and o.name not in {'Mat','MatBorder'}:bpy.data.objects.remove(o,do_unlink=True)
  bpy.ops.import_scene.fbx(filepath=str(folder/'Front_Kick.fbx'));s=bpy.context.scene;s.frame_set(f);s.render.resolution_x=640;s.render.resolution_y=720;s.cycles.samples=8;build.view.camera(s,(4,-.8,1.65),(0,-.3,.95),2.25);s.render.filepath=str(folder/f'FBX_Kick_{f}.png');bpy.ops.render.render(write_still=True)
 log('COMPLETE')
try:run()
except:log(traceback.format_exc());raise
