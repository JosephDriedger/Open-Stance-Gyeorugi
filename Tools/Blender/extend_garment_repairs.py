"""Propagate verified garments without rebuilding heads, rigs or authored actions."""
import bpy,sys,json,traceback,hashlib,math
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import repair_rom_garments as repair
import audit_fighter_range as audit
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/GarmentRollout';OUT.mkdir(exist_ok=True)
PARTS=repair.PARTS+['Pants']
PROFILES=['Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def signature(r):return [[b.name,b.parent.name if b.parent else None,*[v for row in b.matrix_local for v in row]] for b in r.data.bones]
def curves(a):
 if hasattr(a,'fcurves'):return list(a.fcurves)
 return [f for l in a.layers for s in l.strips for bag in s.channelbags for f in bag.fcurves]
def actions():
 return {a.name:hashlib.sha256(str([(f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]) for f in curves(a)]).encode()).hexdigest() for a in bpy.data.actions}
def source(kind,level):
 return ROOT/'Resources/Models/Animation'/f'OpenStance_{kind}_Animation.blend' if level=='Animation' else ROOT/'Resources/Models/CharacterSuite'/kind/(level+'.blend')
def prepare(kind):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'))
 r=bpy.data.objects['RIG_Body_'+kind];mapping={}
 for bone in r.data.bones:
  p=bone
  while p and p.name not in build.suite.KEEP:p=p.parent
  mapping[bone.name]=p.name if p else 'pelvis'
 d=OUT/kind;d.mkdir(exist_ok=True)
 bpy.data.libraries.write(str(d/'Garments.blend'),{bpy.data.objects[n] for n in PARTS},fake_user=True,compress=True)
 (d/'weight_mapping.json').write_text(json.dumps(mapping))
 bpy.ops.wm.open_mainfile(filepath=str(source(kind,'Preview')))
 bpy.data.libraries.write(str(d/'Scalps.blend'),{o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Hair_') and 'Scalp_Coverage' in o.name},compress=True)
def remap(o,r,mapping):
 rows=[];valid=set(r.data.bones.keys())
 for v in o.data.vertices:
  row={}
  for g in v.groups:
   name=o.vertex_groups[g.group].name
   if name in mapping:
    n=mapping[name];row[n]=row.get(n,0)+g.weight
  rows.append(row)
 for g in list(o.vertex_groups):
  if g.name in mapping:o.vertex_groups.remove(g)
 groups={n:o.vertex_groups.get(n) or o.vertex_groups.new(name=n) for row in rows for n in row}
 for i,row in enumerate(rows):
  for n,w in row.items():groups[n].add([i],w,'REPLACE')
 build.suite.weights(o,r,2)
def run(kind,level):
 directory=OUT/kind;bpy.ops.wm.open_mainfile(filepath=str(source(kind,level)));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 original=signature(r);old_actions=actions();crowd=level.startswith('Crowd');full=level in ['Preview','Animation']
 old_action=r.animation_data.action if r.animation_data else None
 nla=[(tr,tr.mute) for tr in r.animation_data.nla_tracks] if r.animation_data else []
 r.animation_data_create();r.animation_data.action=None
 for tr,_ in nla:tr.mute=True
 pose=[(p,p.matrix_basis.copy(),p.rotation_mode) for p in r.pose.bones]
 for p,_,_ in pose:p.matrix_basis=Matrix()
 for n in PARTS:
  o=bpy.data.objects.get(n)
  if o:bpy.data.objects.remove(o,do_unlink=True)
 before=set(bpy.data.objects)
 with bpy.data.libraries.load(str(directory/'Garments.blend'),link=False) as (a,b):b.objects=list(PARTS)
 for o in b.objects:
  s.collection.objects.link(o);o.name=o.name.split('.')[0];world=o.matrix_world.copy();o.parent=r;o.matrix_world=world
  for m in o.modifiers:
   if m.type=='ARMATURE':m.object=r
  for owner in [o,o.data.shape_keys]:build.redirect(owner,r)
  for mat in o.data.materials:
   if mat and mat.use_nodes:build.redirect(mat.node_tree,r)
 for o in list(bpy.data.objects):
  if o not in before and o not in b.objects:bpy.data.objects.remove(o,do_unlink=True)
 # Keep the original skeleton and its animation data; only garment meshes change.
 if crowd:
  mapping=json.loads((directory/'weight_mapping.json').read_text())
  for o in b.objects:remap(o,r,mapping)
 budgets={'Gameplay_Mid':(7600,6000,800,350),'Gameplay_Far':(3800,3000,500,220),'Crowd_Near':(1670,1320,280,120),'Crowd_Far':(610,480,150,70)}
 if level in budgets:
  jacket,pants,panel,belt=budgets[level]
  for o in b.objects:
   budget=jacket if o.name=='Jacket' else pants if o.name=='Pants' else panel if o.name.startswith('Jacket_') else belt
   build.reduce_mesh(o,budget)
   build.suite.weights(o,r,2 if crowd else 4)
 if level=='Crowd_Far':
  # Coarse scalp triangles cut through the forehead; use the proven near grid.
  for o in list(bpy.data.objects):
   if o.name.startswith('Hair_') and 'Scalp_Coverage' in o.name:bpy.data.objects.remove(o,do_unlink=True)
  prior=set(bpy.data.objects)
  with bpy.data.libraries.load(str(directory/'Scalps.blend'),link=False) as (a,z):z.objects=[n for n in a.objects if n.startswith('Hair_') and 'Scalp_Coverage' in n]
  for o in z.objects:
   s.collection.objects.link(o);o.name=o.name.split('.')[0];build.suite.bind(o,r);build.redirect(o,r);build.redirect(o.data.shape_keys,r)
   for mat in o.data.materials:
    if mat and mat.use_nodes:build.redirect(mat.node_tree,r)
   build.resample_scalp(o,bpy.data.objects['Head'],r,'Crowd_Near')
  for o in list(bpy.data.objects):
   if o not in prior and o not in z.objects:bpy.data.objects.remove(o,do_unlink=True)
 # Match donor coverage while retaining the original body's detail and colors.
 body=bpy.data.objects['Body'];pelvis=r.matrix_world@r.data.bones['pelvis'].head_local;arm=r.matrix_world@r.data.bones['upperarm_l'].head_local
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.57778847
 group=body.vertex_groups.get('CoveredBy_Jacket')
 if group:group.add([v.index for v in body.data.vertices if abs((body.matrix_world@v.co).x)<arm.x+.065*scale and pelvis.z+.08*scale<(body.matrix_world@v.co).z<arm.z+.055*scale],1,'REPLACE')
 r['JacketStyle']=0
 for p,m,mode in pose:p.rotation_mode=mode;p.matrix_basis=m
 r.animation_data.action=old_action
 for tr,mute in nla:tr.mute=mute
 s['GarmentRevision']='ROM garment rollout 2026-10-13';build.refresh(r)
 assert signature(r)==original
 for name,sha in old_actions.items():assert actions()[name]==sha,('Changed action',name)
 assert len(r.data.bones)==(25 if crowd else 341)
 if full:
  assert len(bpy.data.objects['RIG_Face_'+kind].data.bones)==874
  assert len([o for o in s.objects if o.get('MarkerLabel')])==41
 path=directory/(f'OpenStance_{kind}_Animation.blend' if level=='Animation' else level+'.blend')
 bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];assert signature(r)==original
 row={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bones':len(r.data.bones),'original_rest_hierarchy_preserved':True,'original_actions_preserved':list(old_actions),'marker_count':sum(bool(o.get('MarkerLabel')) for o in s.objects),'garment_triangles':{n:build.suite.tris(bpy.data.objects[n]) for n in PARTS}}
 # Render motion checkpoints from the delivered native file.
 r.animation_data.action=None
 for tr in r.animation_data.nla_tracks:tr.mute=True
 s.render.engine='CYCLES';s.cycles.samples=4;s.render.resolution_x=480;s.render.resolution_y=540;s.render.resolution_percentage=100
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 build.view.camera(s,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
 checks=['Neutral','Arms_Overhead','Deep_Squat','Front_Kick_L','Side_Kick_L'] if not crowd else ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer','Crowd_Wave']
 for label in checks:
  if crowd:r.animation_data.action=bpy.data.actions[label];s.frame_set(16)
  else:audit.pose(r,label,scale)
  bpy.context.view_layer.update();s.render.filepath=str(directory/(level+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
 row['rendered_checks']=checks
 (directory/(level+'_native_validation.json')).write_text(json.dumps({'passed':True,**row},indent=2));log(kind+' '+level+' COMPLETE')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:]
  levels=['Crowd_Far'] if '--only-far' in args else PROFILES
  args=[a for a in args if not a.startswith('--')]
  for kind in args or build.PRESETS:
   prepare(kind)
   for level in levels:run(kind,level)
 except:log(traceback.format_exc());raise
