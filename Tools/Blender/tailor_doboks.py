"""Reduce excess cloth volume while preserving bodies, rigs and morph animation."""
import bpy,sys,json,math,hashlib,traceback
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
import rebuild_updated_characters as build
import audit_fighter_range as audit
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/TailoredDoboks';OUT.mkdir(exist_ok=True)
LEVELS=['Gameplay_High','Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']
PARTS=base.PARTS+['Jacket_WhiteVNeck'];PANELS=['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def lerp(a,b,t):return a+(b-a)*max(0,min(1,t))
def run(kind,level,source=None):
 bpy.context.preferences.filepaths.save_version=0
 path=Path(source) if source else base.source(kind,level);bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 signature=base.signature(r);actions=base.actions();body=bpy.data.objects['Body'];bodycoords=[tuple(v.co) for v in body.data.vertices]
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;pelvis=(r.matrix_world@r.data.bones['pelvis'].head_local).z
 tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons])
 def axis(q,n):
  bone=r.data.bones[n];a=r.matrix_world@bone.head_local;b=r.matrix_world@bone.tail_local;v=b-a;t=max(0,min(1,(q-a).dot(v)/v.length_squared));return a+v*t
 def torso(q):
  t=(q.z-pelvis)/(.52*scale);fx=lerp(.92,1,t);fy=lerp(.90,1,t);return Vector((q.x*fx,q.y*fy,q.z))
 measures={}
 for name in PARTS:
  o=bpy.data.objects.get(name)
  if not o:continue
  world=o.matrix_world.copy();inv=world.inverted();basis=[world@v.co for v in o.data.vertices];transforms=[];offsets=[]
  for v,q in zip(o.data.vertices,basis):
   target=torso(q);factor=1.;center=Vector();arm=name in ['Jacket','Jacket_WhiteVNeck'] and abs(q.x)>.22*scale
   leg=name=='Pants' and q.z<pelvis-.08*scale
   if arm or leg:
    side='l' if q.x>=0 else 'r';names=[('upperarm_' if arm else 'thigh_')+side,('lowerarm_' if arm else 'calf_')+side]
    candidates=[(axis(q,n),n) for n in names];center,bone=min(candidates,key=lambda item:(q-item[0]).length_squared)
    strength=max(0,min(1,(abs(q.x)/scale-.22)/.08)) if arm else max(0,min(1,(pelvis-q.z)/scale/.20))
    if leg:strength*=max(0,min(1,(q.z/scale-.10)/.18))
    factor=1-(.22 if arm else .18)*strength;target=torso(q).lerp(center+(q-center)*(.78 if arm else .82),strength)
   if name.startswith('Belt_Tail'):target=Vector((q.x*.92,q.y*.90,q.z))
   # Keep real wearing ease around the original body, rather than changing body shape.
   if arm or leg:
    hit,normal,_,dist=tree.find_nearest(target)
    ease=(.014 if name=='Pants' else .016)*scale
    if hit is not None and dist<.12*scale:
     old_sep=(q-hit).dot(normal);new_sep=(target-hit).dot(normal)
     if old_sep>ease and new_sep<ease:
      target=q.lerp(target,max(0,min(1,(old_sep-ease)/max(.00001,old_sep-new_sep))))
   offsets.append(target-q)
   # Morph deltas use the same local contraction so existing corrections remain effective.
   transforms.append(factor if arm or leg else .94)
  if name in ['Jacket','Jacket_WhiteVNeck','Pants']:
   neighbors=[set() for _ in basis]
   for edge in o.data.edges:
    a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
   for _ in range(10):
    previous=[p.copy() for p in offsets]
    for i,adj in enumerate(neighbors):
     if adj:offsets[i]=previous[i]*.5+sum((previous[j] for j in adj),Vector())*(.5/len(adj))
  if o.data.shape_keys:
   keys=o.data.shape_keys.key_blocks;oldbasis=[p.co.copy() for p in keys[0].data]
   for key in keys:
    for i,p in enumerate(key.data):p.co=inv@(basis[i]+offsets[i]+world.to_3x3()@(p.co-oldbasis[i])*transforms[i])
   for v,p in zip(o.data.vertices,keys[0].data):v.co=p.co
  else:
   for v,q,delta in zip(o.data.vertices,basis,offsets):v.co=inv@(q+delta)
  measures[name]={'max_adjustment_m':max((d.length for d in offsets),default=0),'mean_adjustment_m':sum(d.length for d in offsets)/max(1,len(offsets))}
 # The tighter cloth needs full hidden-leg coverage, including inner-thigh faces.
 # Keep the existing Wear_Pants-driven mask, and preserve exposed feet and hands.
 pants=bpy.data.objects['Pants'];pp=[pants.matrix_world@v.co for v in pants.data.vertices]
 lo=min(p.z for p in pp)+.006*scale;hi=max(p.z for p in pp)-.006*scale
 group=body.vertex_groups.get('CoveredBy_Pants');assert group is not None
 hidden=[v.index for v in body.data.vertices if lo<(body.matrix_world@v.co).z<hi and abs((body.matrix_world@v.co).x)<.36*scale]
 group.add(hidden,1,'REPLACE')
 from repair_garment_openings import repair as repair_openings
 repair_openings(s)
 assert [tuple(v.co) for v in body.data.vertices]==bodycoords
 assert base.signature(r)==signature
 for n,h in actions.items():assert base.actions()[n]==h,('Changed animation',n)
 s['DobokFitRevision']='Tailored fit 2026-10-14';d=OUT/kind;d.mkdir(exist_ok=True);dest=d/path.name;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 report={'passed':True,'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bones':len(r.data.bones),'body_unchanged':True,'rest_hierarchy_unchanged':True,'animation_keyframes_unchanged':True,'adjustments':measures}
 r.animation_data.action=None
 for tr in r.animation_data.nla_tracks:tr.mute=True
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 s.render.engine='CYCLES';s.cycles.samples=4;s.render.resolution_x=480;s.render.resolution_y=540;s.render.resolution_percentage=100
 build.view.camera(s,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
 checks=['Neutral','Arms_Overhead','Deep_Squat','Front_Kick_L'] if not level.startswith('Crowd') else ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer']
 for style in [0,1]:
  r['JacketStyle']=style
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  build.refresh(r)
  for label in checks:
   if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions[label];s.frame_set(16)
   else:audit.pose(r,label,scale)
   bpy.context.view_layer.update();s.render.filepath=str(d/(level+'_'+str(style)+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
 if level=='Gameplay_High':
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=True
  build.refresh(r)
  for label in ['Arms_Overhead','Front_Kick_L']:
   audit.pose(r,label,scale);bpy.context.view_layer.update();s.render.filepath=str(d/(level+'_Gear_'+label+'.png'));bpy.ops.render.render(write_still=True)
 report['checks']=checks;(d/(level+'_validation.json')).write_text(json.dumps(report,indent=2));log(kind+' '+level+' COMPLETE')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else build.PRESETS;quick='--quick' in args;args=[a for a in args if not a.startswith('--')]
  for kind in args:
   for level in (['Preview'] if quick else LEVELS):run(kind,level)
 except:log(traceback.format_exc());raise
