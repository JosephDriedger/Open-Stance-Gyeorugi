"""Read-only follow-up review of installed characters; saves renders only."""
import bpy,sys,json,traceback,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
OUT=a.ROOT/'Resources/Models/FollowupReview_20261020';OUT.mkdir(exist_ok=True)
def load(kind,level):
 s,r,z,src=a.load(kind,level)
 for o in s.objects:
  if o.type=='MESH' and o.data.shape_keys:
   ks=o.data.shape_keys
   if ks.animation_data:ks.animation_data.action=None
   for k in ks.key_blocks:
    if k.name.startswith(('ClothBake','Pose_')):k.value=0
 s.cycles.samples=12
 return s,r,z,src
try:
 for ix,kind in enumerate(sys.argv[sys.argv.index('--')+1:]):
  d=OUT/kind;d.mkdir(exist_ok=True);rows=[]
  s,r,z,src=load(kind,'Gameplay_High');stamp=src.stat().st_mtime_ns
  cases=[('Neutral',False,0),('Neutral',True,1),('Knee_L',False,0),('Front_Kick_L',True,1),('Deep_Squat',True,0),('Cross_Body',False,1),('Elbows_Flexed',True,0),('Side_Kick_R',False,1)]
  for n,(pose,gear,j) in enumerate(cases):
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
   r['JacketStyle']=j;r['HelmetDesign']=n%3;r['ProtectorDesign']=n%2;a.build.refresh(r);a.audit.pose(r,pose,z)
   cam=(4,-.8,1.7) if pose in ['Knee_L','Front_Kick_L'] else (1.3,-4,1.8)
   rows.append(a.render(s,r,z,d,f'Body_{n}_{pose}',cam,(0,0,.96),2.35,640,720))
  for pose,target,cam,ortho in [('Wrists_Flexed',(.2,-.61,1.4),(.8,-2,1.7),.55),('Ankle_Flexed',(.10,-.2,.55),(1,-1,.65),.6)]:
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
   a.build.refresh(r);a.audit.pose(r,pose,z)
   rows.append(a.render(s,r,z,d,pose,cam,target,ortho,480,480))
  assert stamp==src.stat().st_mtime_ns
  s,r,z,src=load(kind,'Preview');stamp=src.stat().st_mtime_ns
  style=a.build.PRESETS.index(kind)%6;r['HairStyle']=style
  for helmet in range(3):
   r['HelmetDesign']=helmet;a.build.refresh(r)
   for side,cam in [('Front',(.5,-1,1.84)),('Rear',(.5,1,1.84))]:rows.append(a.render(s,r,z,d,f'Hair{style}_H{helmet}_{side}',cam,(0,0,1.65),.5,480,480))
  r['Wear_Helmet']=False;a.build.refresh(r)
  rows.append(a.render(s,r,z,d,'Bare_Head',(.5,-1,1.82),(0,0,1.67),.4,480,480));assert stamp==src.stat().st_mtime_ns
  for level in ['Crowd_Near','Crowd_Far']:
   s,r,z,src=load(kind,level);stamp=src.stat().st_mtime_ns
   r['HairStyle']=style;r['Wear_Helmet']=False;r['Wear_Protector']=False;a.build.refresh(r)
   rows.append(a.render(s,r,z,d,level,(.4,-1,1.9),(0,0,1.65),.5,480,480));assert stamp==src.stat().st_mtime_ns
  (d/'manifest.json').write_text(json.dumps({'preset':kind,'renders':rows,'hair_style_sample':style,'source_files_unchanged':True,'scope':'General skinning with clip-specific baked corrections disabled; selected pose and hairstyle combinations, not exhaustive collision proof'},indent=2))
  with (OUT/'review.log').open('a') as f:f.write(kind+' COMPLETE\n')
except:
 with (OUT/'error.log').open('a') as f:f.write(traceback.format_exc())
 raise
