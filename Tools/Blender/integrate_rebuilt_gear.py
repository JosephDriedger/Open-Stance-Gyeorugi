"""Stage fitted rebuilt gear, LODs and exports without touching original suite files."""
import bpy,json,sys,traceback,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import build_character_suite as suite
import finish_character_suite as finish
import build_single_helmet_study as view
ROOT=suite.ROOT;SOURCE=ROOT/'Resources/Models/ProtectorStudy/Chest_Protector_Library.blend'
OUT=ROOT/'Resources/Models/GearUpgrade';OUT.mkdir(exist_ok=True)
HELMETS=['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown']
PROTECTORS=['Quilted_Lace_Back','Smooth_Buckle_Back']
PROFILES=['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far']
BUDGETS={'Preview':(160000,90000),'Gameplay_High':(30000,22000),'Gameplay_Mid':(15000,11000),'Gameplay_Far':(6000,10000)}
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def update(rig):
 rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
def measures(rig):
 z=(rig.matrix_world@rig.data.bones['head'].head_local).z
 body=bpy.data.objects['Body'];points=[body.matrix_world@v.co for v in body.data.vertices]
 rib=(rig.matrix_world@rig.data.bones['spine_04'].head_local).z
 band=[p for p in points if abs(p.z-rib)<.018*z/1.578]
 head=bpy.data.objects['Head'];hv=[head.matrix_world@v.co for v in head.data.vertices]
 return {'head_z':z,'head_top':max(p.z for p in hv),'head_width':max(p.x for p in hv)-min(p.x for p in hv),'rib_width':max(p.x for p in band)-min(p.x for p in band),'rib_depth':max(p.y for p in band)-min(p.y for p in band)}
def prepare(profiles=PROFILES):
 for profile in profiles:
  bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['RIG_Body_Medium'];measure=measures(rig)
  objects=[];data=[]
  for category,styles,budget in [('Helmet',HELMETS,BUDGETS[profile][0]),('Protector',PROTECTORS,BUDGETS[profile][1])]:
   for index,style in enumerate(styles):
    parts=list(bpy.data.collections[category+'_'+style].objects)
    for o in parts:o.hide_viewport=False;o.hide_render=False;o.animation_data_clear()
    sizes=[suite.tris(o) for o in parts];total=sum(sizes)
    for o,size in zip(parts,sizes):
     minimum=48
     if profile=='Gameplay_Far' and category=='Protector':
      if any(s in o.name for s in ['Bound_','Binding','Shoulder_Strap']):minimum=400
     suite.decimate(o,max(minimum,int(budget*size/total)))
     suite.weights(o,rig,2)
     # Retain modular parts; label independently of Blender's suffix naming.
     o['GearCategory']=category;o['GearStyle']=index;o['GearStyleName']=style
     objects.append(o)
    data.append({'category':category,'style':style,'triangles':sum(suite.tris(o) for o in parts),'parts':len(parts)})
  bpy.data.libraries.write(str(OUT/(profile+'_Gear.blend')),set(objects),fake_user=True,compress=True)
  (OUT/(profile+'_budgets.json')).write_text(json.dumps(data,indent=2));(OUT/'source_measurements.json').write_text(json.dumps(measure))
  log('Prepared '+profile)
def install(kind,profile):
 path=suite.OUT/kind/(profile+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind];target=measures(rig)
 src=json.loads((OUT/'source_measurements.json').read_text());zs=target['head_z']/src['head_z']
 # Add garment clearance before deriving torso scales, preserving foam thickness.
 sx=(target['rib_width']+.10*zs)/(src['rib_width']+.10)
 sy=(target['rib_depth']+.10*zs)/(src['rib_depth']+.10)
 hx=target['head_width']/src['head_width'];hz=(target['head_top']-target['head_z'])/(src['head_top']-src['head_z'])
 for o in list(bpy.data.objects):
  if o.type=='MESH' and o.name.startswith(('Helmet','Protector')):bpy.data.objects.remove(o,do_unlink=True)
 old_ids=set(bpy.data.objects)
 with bpy.data.libraries.load(str(OUT/(profile+'_Gear.blend')),link=False) as (a,b):
  b.objects=[n for n in a.objects if any(n.startswith(s+'__') for s in HELMETS+PROTECTORS)]
 objects=b.objects
 for category,styles in [('Helmet',HELMETS),('Protector',PROTECTORS)]:
  rig[category+'Style']=0;rig.id_properties_ui(category+'Style').update(min=0,max=len(styles)-1,description='; '.join(f'{i}: {s}' for i,s in enumerate(styles)))
  rig['Wear_'+category]=True
 rig['Wear_Gloves']=True;rig['Wear_FootGuards']=True;rig['Wear_Hair']=False
 for o in objects:
  category=o['GearCategory'];index=o['GearStyle'];style=o['GearStyleName']
  coll=bpy.data.collections.get('Rebuilt_'+category+'_'+style)
  if not coll:coll=bpy.data.collections.new('Rebuilt_'+category+'_'+style);bpy.context.scene.collection.children.link(coll)
  coll.objects.link(o);o.hide_set(False);o.animation_data_clear()
  # Convert from source world coordinates before rebinding to the destination rig.
  world=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix()
  for v in o.data.vertices:
   p=world@v.co
   if category=='Helmet':p=Vector((p.x*hx,p.y*hx,target['head_z']+(p.z-src['head_z'])*hz))
   else:p=Vector((p.x*sx,p.y*sy,p.z*zs))
   v.co=p
  suite.bind(o,rig);o.name=category+'_'+style+'__'+o.name.split('__',1)[-1]
  for mat in o.data.materials:
   if mat and mat.node_tree and mat.node_tree.animation_data:
    for d in mat.node_tree.animation_data.drivers:
     for var in d.driver.variables:
      for t in var.targets:t.id=rig
  for attr in ['hide_render','hide_viewport']:
   suite.driver(o,attr,rig,category+'Style',f'x != {index}');d=o.animation_data.drivers.find(attr).driver
   v=d.variables.new();v.name='wear';v.targets[0].id=rig;v.targets[0].data_path='["Wear_'+category+'"]';d.expression=f'(x != {index}) or not wear'
 for o in list(bpy.data.objects):
  if o not in old_ids and o not in objects and o.type=='ARMATURE':bpy.data.objects.remove(o,do_unlink=True)
 update(rig);scene=bpy.context.scene
 directory=OUT/kind;directory.mkdir(exist_ok=True)
 if profile=='Preview':
  view.camera(scene,(.8*zs,-2*zs,1.55*zs),(0,0,1.34*zs),1.12*zs)
  scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/(profile+'.blend')),compress=True)
 if profile!='Preview':
  meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
  finish.export(rig,meshes,directory/(profile+'_Sparring.fbx'))
 # Reopen native deliverable and test every selector, weight and attachment.
 bpy.ops.wm.open_mainfile(filepath=str(directory/(profile+'.blend')));rig=bpy.data.objects['RIG_Body_'+kind];scene=bpy.context.scene
 gear=[o for o in scene.objects if o.get('GearCategory')]
 for o in gear:
  assert next(m.object for m in o.modifiers if m.type=='ARMATURE')==rig
  assert all(abs(sum(g.weight for g in v.groups)-1)<.002 and 1<=len(v.groups)<=2 for v in o.data.vertices),o.name
 for category,styles in [('Helmet',HELMETS),('Protector',PROTECTORS)]:
  for index in range(len(styles)):
   rig[category+'Style']=index;update(rig)
   for o in gear:
    if o['GearCategory']==category:assert o.hide_render==(o['GearStyle']!=index)
  rig['Wear_'+category]=False;update(rig);assert all(o.hide_render for o in gear if o['GearCategory']==category)
  rig['Wear_'+category]=True;rig[category+'Style']=0;update(rig)
 counts={};deps=bpy.context.evaluated_depsgraph_get()
 for o in scene.objects:
  if o.type=='MESH' and not o.hide_render and any(m.type=='ARMATURE' for m in o.modifiers):
   e=o.evaluated_get(deps);mesh=e.to_mesh();mesh.calc_loop_triangles();counts[o.name]=len(mesh.loop_triangles);e.to_mesh_clear()
 report={'passed':True,'fit_scale':{'helmet':[hx,hx,hz],'protector':[sx,sy,zs]},'gear_parts':len(gear),'visible_evaluated_triangles':counts,'visible_total':sum(counts.values())}
 (directory/(profile+'_gear_validation.json')).write_text(json.dumps(report,indent=2))
 if profile=='Preview':
  scene.render.filepath=str(directory/'Rebuilt_Gear.png');bpy.ops.render.render(write_still=True)
 if kind=='Medium' and profile=='Gameplay_Far':
  view.camera(scene,(.8,-2,1.55),(0,0,1.34),1.12);scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(directory/'Gameplay_Far_Gear.png');bpy.ops.render.render(write_still=True)
 log('Validated '+kind+' '+profile)
def main():
 args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
 if args==['refine-far']:
  prepare(['Gameplay_Far'])
  for kind in ['Medium','Compact','Stocky','LeanTall','Tall']:install(kind,'Gameplay_Far')
  log('FAR REFINEMENT COMPLETE');return
 if not args or args[0]=='prepare':prepare()
 kinds=['Medium','Compact','Stocky','LeanTall','Tall'] if not args else args
 if kinds==['prepare']:return
 for kind in kinds:
  for profile in PROFILES:install(kind,profile)
 log('COMPLETE')
if __name__=='__main__':
 try:main()
 except:log(traceback.format_exc());raise
