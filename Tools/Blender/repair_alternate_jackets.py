import bpy,bmesh,sys,json,hashlib,traceback
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
import rebuild_updated_characters as build
import audit_fighter_range as audit
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/AlternateJacketRepair';OUT.mkdir(exist_ok=True)
LEVELS=['Gameplay_High','Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']
PANELS=['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def driver(o,r,expr):
 for channel in ['hide_render','hide_viewport']:
  try:o.driver_remove(channel)
  except:pass
  d=o.driver_add(channel).driver;d.expression=expr
  for name,prop in [('wear','Wear_Jacket'),('style','JacketStyle')]:
   v=d.variables.new();v.name=name;v.targets[0].id=r;v.targets[0].data_path='["'+prop+'"]'
def prepare(kind):
 d=OUT/kind;d.mkdir(exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(base.source(kind,'Gameplay_High')))
 r=bpy.data.objects['RIG_Body_'+kind];o=bpy.data.objects['Jacket'];bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);removed=0
 while remaining:
  stack=[remaining.pop()];part=[]
  while stack:
   v=stack.pop();part.append(v)
   for e in v.link_edges:
    n=e.other_vert(v)
    if n in remaining:remaining.remove(n);stack.append(n)
  if len(part)==52:
   bmesh.ops.delete(bm,geom=part,context='VERTS');removed+=1
 assert removed==1,('Expected isolated diagonal wrap trim',kind,removed)
 bm.to_mesh(o.data);bm.free();o.name='Jacket_WhiteVNeck'
 # Blender may suffix the name because the legacy alternate still exists.
 bpy.data.libraries.write(str(d/'VNeck_Source.blend'),{o},compress=True)
 (d/'source_name.json').write_text(json.dumps(o.name))
def run(kind,level,source=None):
 d=OUT/kind;path=Path(source) if source else base.source(kind,level);bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 original=base.signature(r);actions=base.actions();oldstyle=r.get('JacketStyle',0);oldwear=r.get('Wear_Jacket',True)
 old=bpy.data.objects.get('Jacket_WhiteVNeck')
 if old:bpy.data.objects.remove(old,do_unlink=True)
 before=set(bpy.data.objects)
 with bpy.data.libraries.load(str(d/'VNeck_Source.blend'),link=False) as (a,z):z.objects=[json.loads((d/'source_name.json').read_text())]
 o=z.objects[0];s.collection.objects.link(o);o.name='Jacket_WhiteVNeck';world=o.matrix_world.copy();o.parent=r;o.matrix_world=world
 for m in o.modifiers:
  if m.type=='ARMATURE':m.object=r
 build.redirect(o,r)
 for mat in o.data.materials:
  if mat and mat.use_nodes:build.redirect(mat.node_tree,r)
 if level.startswith('Crowd'):
  mapping=json.loads((ROOT/'Resources/Models/GarmentRollout'/kind/'weight_mapping.json').read_text());base.remap(o,r,mapping)
 budget=build.suite.tris(bpy.data.objects['Jacket']);build.reduce_mesh(o,budget);build.suite.weights(o,r,2 if level.startswith('Crowd') else 4)
 for extra in list(bpy.data.objects):
  if extra not in before and extra!=o:bpy.data.objects.remove(extra,do_unlink=True)
 driver(bpy.data.objects['Jacket'],r,'not wear or style != 0');driver(o,r,'not wear or style != 1')
 for name in PANELS:driver(bpy.data.objects[name],r,'not wear')
 r.id_properties_ui('JacketStyle').update(min=0,max=1,description='0: White wrap; 1: White V-neck. Both use fitted lower panels and hip corrections.')
 for wear in [False,True]:
  for style in [0,1]:
   r['Wear_Jacket']=wear;r['JacketStyle']=style;build.refresh(r)
   assert bpy.data.objects['Jacket'].hide_render==(not wear or style!=0)
   assert o.hide_render==(not wear or style!=1)
   assert all(bpy.data.objects[n].hide_render==(not wear) for n in PANELS)
 r['JacketStyle']=oldstyle;r['Wear_Jacket']=oldwear;build.refresh(r)
 assert base.signature(r)==original
 for name,value in actions.items():assert base.actions()[name]==value,('Changed action',name)
 s['AlternateJacketRevision']='2026-10-13';dest=d/path.name;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(dest));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];assert base.signature(r)==original
 report={'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bones':len(r.data.bones),'actions_preserved':list(actions),'selector_and_wear_checks':True,'rest_hierarchy_unchanged':True}
 r['JacketStyle']=1;r['Wear_Jacket']=True;build.refresh(r)
 r.animation_data.action=None
 for tr in r.animation_data.nla_tracks:tr.mute=True
 for obj in s.objects:
  if obj.get('MarkerLabel'):obj.hide_render=True
 s.render.engine='CYCLES';s.cycles.samples=4;s.render.resolution_x=480;s.render.resolution_y=540;s.render.resolution_percentage=100
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;build.view.camera(s,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
 checks=['Neutral','Arms_Overhead','Deep_Squat','Front_Kick_L'] if not level.startswith('Crowd') else ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer']
 for label in checks:
  if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions[label];s.frame_set(16)
  else:audit.pose(r,label,scale)
  bpy.context.view_layer.update();s.render.filepath=str(d/(level+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
 report['rendered_checks']=checks;(d/(level+'_validation.json')).write_text(json.dumps({'passed':True,**report},indent=2));log(kind+' '+level+' COMPLETE')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else build.PRESETS
  quick='--quick' in args;args=[a for a in args if not a.startswith('--')]
  for kind in args:
   prepare(kind)
   for level in (['Gameplay_High','Preview'] if quick else LEVELS):run(kind,level)
 except:log(traceback.format_exc());raise
