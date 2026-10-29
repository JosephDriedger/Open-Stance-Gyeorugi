import bpy,sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_crew_surface_finish as fix
import audit_sparring_styles as a
for kind in sys.argv[sys.argv.index('--')+1:]:
 for level in ['Gameplay_High','Preview','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
  while not (fix.OUT/kind/(level+'_validation.json')).exists():time.sleep(3)
  bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/kind/(level+'.blend')))
  s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.animation_data_create();r.animation_data.action=None
  for t in r.animation_data.nla_tracks:t.mute=True
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','BlenderCloth']:r[prop]=False
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True
  for style in [0,1]:
   r['JacketStyle']=style;a.build.refresh(r)
   label='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
   if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions['Crowd_StandingIdle'];s.frame_set(16)
   else:a.audit.pose(r,'Neutral',scale)
   a.render(s,r,scale,fix.OUT/kind,f'{level}_{style}_{label}',(.8,-4,1.7),(0,0,.96),2.35,480,540)

  assert len(r.data.bones)==(25 if level.startswith('Crowd') else 341)
  for o in s.objects:
   for owner in [o,o.data.shape_keys if o.type=='MESH' else None]:
    if owner and owner.animation_data:assert all(driver.is_valid for driver in owner.animation_data.drivers),(kind,level,o.name)
  if level in ['Gameplay_High','Crowd_Near','Crowd_Far']:
   r.animation_data.action=None;r['HairStyle']=0;r['JacketStyle']=0;a.build.refresh(r);a.audit.pose(r,'Neutral',scale)
   a.render(s,r,scale,fix.OUT/kind,level+'_HairReview',(.4,-1,1.9),(0,0,1.65),.52,600,600)
   if kind=='Medium':
    for design in [0,1,2]:
     r['Wear_Helmet']=True;r['HelmetDesign']=design;a.build.refresh(r)
     a.render(s,r,scale,fix.OUT/kind,level+'_Helmet_'+str(design),(.4,-1,1.9),(0,0,1.65),.52,600,600)
  (fix.OUT/kind/(level+'_visual_ready.json')).write_text(json.dumps({'drivers_valid':True,'bones':len(r.data.bones)}))
