"""Preserve modular choices and validate the staged native files."""
import bpy,sys,json,math,traceback
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import build_character_suite as suite
ROOT=build.ROOT;OUT=build.OUT
def add_choices(rig):
 if 'MatchSide' not in rig:rig['MatchSide']=0
 rig.id_properties_ui('MatchSide').update(min=0,max=1,description='0 blue; 1 red')
 if 'HeadStyle' in rig:return
 specs={'Head':['Oval','BroadJaw','NarrowJaw'],'Jacket':['WhiteWrap','WhiteVNeck'],'Gloves':['Standard','PaddedKnuckle'],'FootGuards':['SensorSocks','PaddedInstep']}
 for part,styles in specs.items():
  original=bpy.data.objects.get(part)
  if original is None:continue
  prop=part+'Style';rig[prop]=0;rig.id_properties_ui(prop).update(min=0,max=len(styles)-1,description='; '.join(f'{i}: {s}' for i,s in enumerate(styles)))
  for index,style in enumerate(styles):
   o=original if index==0 else suite.duplicate(original,part+'_'+style)
   if index and part=='Head':
    low=min(v.co.z for v in o.data.vertices);high=max(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
     t=(v.co.z-low)/(high-low);v.co.x*=1+(.065 if index==1 else -.05)*math.exp(-((t-.28)/.18)**2)
   elif index and part=='Jacket':
    # Same topology-based wrap-strip removal used by the original creator suite.
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);parts=[]
    while remaining:
     stack=[remaining.pop()];component=[]
     while stack:
      v=stack.pop();component.append(v)
      for e in v.link_edges:
       n=e.other_vert(v)
       if n in remaining:remaining.remove(n);stack.append(n)
     parts.append(component)
    for component in parts:
     if 60<=len(component)<=110:bmesh.ops.delete(bm,geom=component,context='VERTS')
    bm.to_mesh(o.data);bm.free()
   elif index:
    for v in o.data.vertices:v.co+=v.normal*.0018
   for attr in ['hide_render','hide_viewport']:
    suite.driver(o,attr,rig,prop,f'x != {index}')
    wear='Wear_'+part
    if wear in rig:
     d=o.animation_data.drivers.find(attr).driver;v=d.variables.new();v.name='wear';v.targets[0].id=rig;v.targets[0].data_path='["'+wear+'"]';d.expression=f'(x != {index}) or not wear'
 if 'SkinTone' not in rig:
  # Preserve the new hair palette while adding the original skin/eye controls.
  mats=[m for m in bpy.data.materials if 'hair' in m.name.lower() or 'brow' in m.name.lower()];names=[m.name for m in mats]
  old_color=rig.get('HairColor',1)
  for i,m in enumerate(mats):m.name='PaletteExcludedFiber_'+str(i)
  suite.palette(rig)
  for m,n in zip(mats,names):m.name=n
  rig['HairColor']=old_color
def run(kind):
 result=[];directory=OUT/kind
 files=[directory/'Preview.blend',directory/f'OpenStance_{kind}_Animation.blend']+[directory/(n+'.blend') for n in ['Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']]
 for path in files:
  bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind];scene=bpy.context.scene;add_choices(rig);build.refresh(rig)
  if path.stem.startswith('Crowd'):rig['Wear_FootGuards']=True;build.refresh(rig)
  before={n:rig[n] for n in ['HairStyle','EyebrowStyle','HelmetDesign','ProtectorDesign','Wear_Hair','Wear_Eyebrows','Wear_Helmet','Wear_Protector']}
  checks=[]
  for prop,prefix,styles,wear in [('HairStyle','Hair_',build.hair.STYLES,'Wear_Hair'),('EyebrowStyle','Eyebrows_',build.hair.EYEBROW_STYLES,'Wear_Eyebrows'),('HelmetDesign','',build.HELMETS,'Wear_Helmet'),('ProtectorDesign','',build.PROTECTORS,'Wear_Protector')]:
   objects=[o for o in build.meshes() if any(o.name.startswith(prefix+s) for s in styles)]
   if not objects:
    assert path.stem.startswith('Crowd') and prop in ['HelmetDesign','ProtectorDesign'];continue
   rig[wear]=True
   for index,style in enumerate(styles):
    rig[prop]=index;build.refresh(rig)
    assert all(o.hide_render==(not o.name.startswith(prefix+style)) for o in objects),(path,prop,index)
    checks.append(prop+':'+str(index))
   rig[wear]=False;build.refresh(rig);assert all(o.hide_render for o in objects)
  for value in [False,True]:
   rig['Wear_Helmet']=value;build.refresh(rig)
   for o in build.meshes():
    if o.name.startswith('Hair_') and o.data.shape_keys:
     assert abs(o.data.shape_keys.key_blocks['HelmetFit'].value-int(value))<1e-5
  for n,v in before.items():rig[n]=v
  build.refresh(rig)
  markers=[o for o in scene.objects if o.get('MarkerLabel')]
  full=path.stem in ['Preview','OpenStance_'+kind+'_Animation']
  assert len(markers)==(41 if full else 0)
  assert len(rig.data.bones)==(25 if path.stem.startswith('Crowd') else 341)
  if full:assert len(bpy.data.objects['RIG_Face_'+kind].data.bones)==874
  # Confirm an actual pose moves skinned body vertices.
  body=bpy.data.objects['Body'];bone=rig.pose.bones['lowerarm_l'];old=bone.rotation_quaternion.copy();mode=bone.rotation_mode
  def coords():return [v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
  neutral=coords();bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,0,1),.3);bpy.context.view_layer.update()
  motion=max((a-b).length for a,b in zip(neutral,coords()));assert motion>.001
  bone.rotation_quaternion=old;bone.rotation_mode=mode;bpy.context.view_layer.update()
  scene['AssetRevision']='Updated specifications - 2026-10-05'
  bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(path));assert bpy.context.scene['AssetRevision']=='Updated specifications - 2026-10-05'
  rig=bpy.data.objects['RIG_Body_'+kind]
  if not full:
   if path.stem.startswith('Crowd'):
    build.export(rig,directory/(path.stem+'.fbx'))
    if path.stem=='Crowd_Near':
     for clip in ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer','Crowd_Wave']:
      rig.animation_data.action=bpy.data.actions[clip];build.export(rig,directory/(clip+'.fbx'),True)
     rig.animation_data.action=None
   else:
    build.export(rig,directory/(path.stem+'_Sparring.fbx'))
    for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:rig[key]=False
    build.refresh(rig);build.export(rig,directory/(path.stem+'_Dobok.fbx'))
    if path.stem=='Gameplay_High':build.export(rig,directory/f'OpenStance_{kind}_Mocap_Source.fbx')
  result.append({'file':path.name,'selectors_checked':checks,'marker_count':len(markers),'body_pose_movement_local':motion,'saved_file_reopened':True})
 (directory/'native_validation.json').write_text(json.dumps({'passed':True,'files':result,'real_capture_tested':False},indent=2))
 build.log(kind+' native finalization complete')
if __name__=='__main__':
 try:
  for kind in sys.argv[sys.argv.index('--')+1:]:run(kind)
 except:build.log(traceback.format_exc());raise
