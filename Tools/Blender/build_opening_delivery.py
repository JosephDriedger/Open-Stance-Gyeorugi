import bpy,sys,json,hashlib,traceback,runpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_garment_openings as fix
import tailor_doboks as fitting
import rebuild_updated_characters as build
import extend_garment_repairs as base
import audit_fighter_range as audit
OUT=fix.OUT;fitting.OUT=OUT
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def run(kind,level,source=None):
 path=Path(source) if source else base.source(kind,level)
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 signature=base.signature(r);actions=base.actions();body=bpy.data.objects['Body'];coords=[tuple(v.co) for v in body.data.vertices]
 changes=fix.repair(s);bpy.context.view_layer.update()
 assert coords==[tuple(v.co) for v in body.data.vertices] and signature==base.signature(r) and actions==base.actions()
 d=OUT/kind;d.mkdir(exist_ok=True);dest=d/path.name;bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 report={'passed':True,'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'body_unchanged':True,'rest_hierarchy_unchanged':True,'animation_keyframes_unchanged':True,'opening_overlap':changes}
 if not level.startswith('Sample'):
  r.animation_data_create();r.animation_data.action=None
  for tr in r.animation_data.nla_tracks:tr.mute=True
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  s.render.engine='CYCLES';s.cycles.samples=8;s.render.resolution_x=480;s.render.resolution_y=540;s.render.resolution_percentage=100
  build.view.camera(s,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
  for style in [0,1]:
   r['JacketStyle']=style;build.refresh(r)
   pose='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
   if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions[pose];s.frame_set(16)
   else:audit.pose(r,'Neutral',scale)
   s.render.filepath=str(d/f'{level}_{style}_{pose}.png');bpy.ops.render.render(write_still=True)
   if level=='Gameplay_High':
    for label in ['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']:
     audit.pose(r,label,scale);s.render.filepath=str(d/f'{level}_{style}_{label}.png');bpy.ops.render.render(write_still=True)
 (d/(level+'_validation.json')).write_text(json.dumps(report,indent=2));log(kind+' '+level+' COMPLETE')
fitting.run=run;fitting.log=log
try:
 mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'native'
 scripts={'exports':'export_tailored_doboks.py','validate':'validate_tailored_delivery.py','samples':'tailor_sample_animations.py','workspace':'assemble_tailored_workspace.py','preview':'render_tailored_sample_preview.py'}
 if mode=='pilot':run('Medium','Gameplay_High')
 elif mode=='tpose':
  for kind in build.PRESETS:run(kind,'Tpose',build.ROOT/'Resources/Models/TPose'/('OpenStance_'+kind+'_Tpose.blend'))
  log('TPOSE COMPLETE')
 elif mode in scripts:
  p=Path(__file__).with_name(scripts[mode]);code=p.read_text().replace('Resources/Models/TailoredDoboks','Resources/Models/OpeningRepair')
  sys.argv=[str(p)]
  exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
 else:
  for kind in build.PRESETS:
   for level in fitting.LEVELS:
    if not (OUT/kind/(level+'_validation.json')).exists():run(kind,level)
  log('NATIVE BUILD COMPLETE')
except:log(traceback.format_exc());raise
