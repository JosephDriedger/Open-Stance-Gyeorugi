import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import refine_crowd_faces as f
for kind in f.review.build.PRESETS:
 for level in ['Crowd_Near','Crowd_Far']:
  path=f.OUT/kind/(level+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
  if not s.get('PonytailRootRepair'):
   cap=bpy.data.objects['Hair_Low_Ponytail__Scalp_Coverage'];tie=bpy.data.objects['Hair_Low_Ponytail__Hair_Tie'];top=sum((tie.matrix_world@v.co for v in tie.data.vertices),Vector())/len(tie.data.vertices)
   # Join the ponytail root to the rear hair shell; preserve the hanging tip.
   nearby=[cap.matrix_world@v.co for v in cap.data.vertices if abs((cap.matrix_world@v.co).z-top.z)<.025]
   rear=max(v.y for v in nearby);shift=Vector((0,min(0,rear-top.y-.004),0));scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
   for suffix in ['Hair_Tie','Ponytail','Ponytail_Core']:
    o=bpy.data.objects['Hair_Low_Ponytail__'+suffix];inv=o.matrix_world.inverted();keys=o.data.shape_keys
    for block in (keys.key_blocks if keys else [o.data]):
     for v in (block.data if keys else block.vertices):
      p=o.matrix_world@v.co;w=1 if suffix=='Hair_Tie' else max(0,min(1,(p.z-(top.z-.10*scale))/(.085*scale)));v.co=inv@(p+shift*w)
    if keys:
     for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
   s['PonytailRootRepair']=True;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
   rp=path.with_name(level+'_validation.json');report=json.loads(rp.read_text());report['sha256']=f.sha(path);report['ponytail_root_attached']=True;rp.write_text(json.dumps(report,indent=2))
  if kind=='Tall':
   r.animation_data_create();r.animation_data.action=None
   for t in r.animation_data.nla_tracks:t.mute=True
   r['HairStyle']=4
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','BlenderCloth']:r[prop]=False
   f.review.build.refresh(r);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;f.review.audit.pose(r,'Neutral',scale);s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
   f.review.render(s,r,scale,path.parent,level+'_V4_Side',(1,-.1,1.8),(0,0,1.65),.5,600,600)
