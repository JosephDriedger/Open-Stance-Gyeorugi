"""Background-only helmet library, retaining the approved fitted baseline."""
import bpy, math, json, sys, traceback
from pathlib import Path
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as base
import rebuild_reference_helmets as u
import build_character_suite as suite
OUT=base.ROOT/'Resources/Models/HelmetVariants'
OUT.mkdir(exist_ok=True)
STYLES=['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown']
REFS=[u.URLS[1],u.URLS[0],u.URLS[2]]

def finish_shell(o):
 m=o.modifiers.new('Molded foam continuity','REMESH');m.mode='VOXEL';m.voxel_size=.001;m.use_smooth_shade=True;u.apply(o,m)
 m=o.modifiers.new('Soft padding edges','SMOOTH');m.factor=.65;m.iterations=7;u.apply(o,m)
 m=o.modifiers.new('Preview surface','SUBSURF');m.levels=1;u.apply(o,m)
 for p in o.data.polygons:p.use_smooth=True

def full_cap(mat):
 # Fitted shallow crown follows the approved brow and side rim exactly.
 verts=[];faces=[];n=96;rows=20
 for j in range(rows+1):
  r=1-j/rows
  for i in range(n):
   a=math.tau*i/n;rim=1.721+.026*math.sin(a)**2+.011*max(0,-math.cos(a))
   # Sink the outer lip into the upper band so the molded cap has no gap.
   verts.append((.088*r*math.sin(a),-.009-.113*r*math.cos(a),rim-.006*r**10+(1.770-rim)*math.sqrt(max(0,1-r*r))))
 for j in range(rows):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 return base.smooth_surface(u.mesh('Full_Crown_Padding',verts,faces,mat))

def create(style,rig):
 mat=u.material(STYLES[style]+'_Foam',rig,.47 if style==1 else .30)
 web=u.material(STYLES[style]+'_Webbing',rig,.86,False)
 shell=base.band(mat,vents=False)
 extras=[]
 if style==2:
  cap=full_cap(mat)
  m=shell.modifiers.new('Join full crown','BOOLEAN');m.operation='UNION';m.solver='EXACT';m.object=cap;u.apply(shell,m);bpy.data.objects.remove(cap,do_unlink=True)
  for x,y in [(0,-.065),(-.043,-.025),(.043,-.025),(-.039,.040),(.039,.040),(0,.074)]:u.hole(shell,(x,y,1.83),(.010,.012),'Z')
  for y,z in [(-.055,1.685),(-.030,1.663),(.002,1.687),(.030,1.667),(.060,1.688),(.072,1.643),(.065,1.600),(.037,1.577)]:u.hole(shell,(0,y,z),(.008,.009),'X')
 else:
  # Open crown with crossed flexible support straps; solid temple panels.
  points=[(-.088+.176*i/48,.006,1.743+.029*math.sin(math.pi*i/48)) for i in range(49)]
  extras.append(u.ribbon('Transverse_Crown_Webbing',points,.032,web))
  centers=[(0,-.119+.222*i/48,1.722+.049*math.sin(math.pi*i/48)**.8) for i in range(49)]
  extras.append(base.padded_strip('Longitudinal_Crown_Padding',centers,[.031]*49,mat))
 finish_shell(shell);shell.name='Foam_Shell'
 ears=[base.ear_pad(s,mat) for s in [-1,1]]
 if style==1:
  for s,ear in zip([-1,1],ears):
   for v in ear.data.vertices:
    v.co.y=-.006+(v.co.y+.006)*1.12;v.co.z=1.615+(v.co.z-1.615)*1.08
   extras.append(u.tube('Ear_Opening_Bridge',[(s*.108,-.027,1.615),(s*.109,.015,1.615)],.0038,web))
   extras.append(u.tube('Ear_Pad_Piping',[(s*.106,-.006+.034*math.cos(math.tau*i/96),1.615+.042*math.sin(math.tau*i/96)) for i in range(97)],.0008,mat))
 return [shell]+ears+[base.strap(web)]+base.patches(web)+extras

def run():
 bpy.ops.wm.open_mainfile(filepath=str(base.OUT/'Single_Helmet_Review.blend'))
 scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_Medium']
 original=list(bpy.data.collections['HELMET_STUDY_Editable_Parts'].objects)
 groups=[original,create(1,rig),create(2,rig)]
 rig['HelmetDesign']=0;rig.id_properties_ui('HelmetDesign').update(min=0,max=2,description='0 approved vented crown; 1 padded open crown; 2 perforated full crown')
 rig['Wear_Helmet']=True
 report={'scope':'Medium body preview library; gameplay LOD and other body fits not regenerated','styles':[]}
 for index,(name,objects) in enumerate(zip(STYLES,groups)):
  coll=bpy.data.collections.new('Helmet_'+name);scene.collection.children.link(coll)
  entry={'name':name,'reference':REFS[index],'parts':{},'head_weights_valid':True}
  for o in objects:
   for c in list(o.users_collection):c.objects.unlink(o)
   coll.objects.link(o);o.name=name+'__'+o.name;base.skin(o,rig);o['ReferenceURL']=REFS[index]
   for attr in ['hide_render','hide_viewport']:
    suite.driver(o,attr,rig,'HelmetDesign',f'x != {index}')
    d=o.animation_data.drivers.find(attr).driver;v=d.variables.new();v.name='wear';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Helmet"]';d.expression=f'(x != {index}) or (not wear)'
   assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-6 for v in o.data.vertices)
   o.data.calc_loop_triangles();entry['parts'][o.name]=len(o.data.loop_triangles)
  report['styles'].append(entry)
 scene.render.resolution_x=1000;scene.render.resolution_y=1000
 target=(0,-.007,1.65);base.camera(scene,(.62,-1,1.86),target,.39)
 rig.update_tag();scene.frame_set(2);scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Helmet_Design_Library.blend'),compress=True)
 for index,name in enumerate(STYLES):
  rig['HelmetDesign']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  base.camera(scene,(.62,-1,1.86),target,.39);scene.render.filepath=str(OUT/(name+'_Fitted.png'));bpy.ops.render.render(write_still=True)
 # Isolated renders share camera, lighting and color to compare geometry fairly.
 all_parts=[o for g in groups for o in g]
 for o in scene.objects:
  if o.type=='MESH' and o not in all_parts:
   if o.animation_data:
    for d in o.animation_data.drivers:
     if d.data_path=='hide_render':d.mute=True
   o.hide_render=True
 for index,name in enumerate(STYLES):
  rig['HelmetDesign']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  base.camera(scene,(.65,-1,2.02),(0,-.007,1.66),.37);scene.render.filepath=str(OUT/(name+'_Detail.png'));bpy.ops.render.render(write_still=True)
 # Reopen the delivered file and test every style and its head attachment.
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Helmet_Design_Library.blend'))
 rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
 for index,name in enumerate(STYLES):
  rig['HelmetDesign']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  objects=list(bpy.data.collections['Helmet_'+name].objects)
  assert all(not o.hide_render for o in objects)
  for other in set(STYLES)-{name}:assert all(o.hide_render for o in bpy.data.collections['Helmet_'+other].objects)
  deps=bpy.context.evaluated_depsgraph_get();before={o.name:(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co).copy() for o in objects}
  bone=rig.pose.bones['head'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,1,0),.25);bpy.context.view_layer.update()
  motion=[(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co-before[o.name]).length for o in objects]
  assert min(motion)>.005
  bone.rotation_quaternion=Quaternion();bpy.context.view_layer.update()
  report['styles'][index]['head_pose_test_passed']=True
 rig['Wear_Helmet']=False;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
 assert all(o.hide_render for name in STYLES for o in bpy.data.collections['Helmet_'+name].objects)
 report['saved_file_reopened']=True;report['style_switch_and_gear_toggle_passed']=True
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2))
 (OUT/'build.log').write_text('COMPLETE\n')

if __name__=='__main__':
 try:run()
 except:(OUT/'build.log').write_text(traceback.format_exc());raise
