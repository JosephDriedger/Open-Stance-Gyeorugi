import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_crew_surface_finish as fix
import extend_garment_repairs as base
import tailor_doboks as fitting
import rebuild_updated_characters as build
OUT=fix.OUT
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def run(kind,level,source=None):
 path=Path(source) if source else base.source(kind,level)
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 sig=base.signature(r);actions=base.actions();body=bpy.data.objects['Body'];coords=[tuple(v.co) for v in body.data.vertices]
 changes=fix.repair(s)
 assert sig==base.signature(r) and actions==base.actions() and coords==[tuple(v.co) for v in body.data.vertices]
 d=OUT/kind;d.mkdir(exist_ok=True);dest=d/path.name
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 (d/(level+'_validation.json')).write_text(json.dumps({'passed':True,'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rig_body_actions_preserved':True,'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'changes':changes},indent=2))
 log(kind+' '+level+' COMPLETE')
fitting.run=run;fitting.OUT=OUT;fitting.log=log
try:
 args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
 mode=args[0] if args else 'native';kinds=args[1:] or build.PRESETS
 if mode in ['native','tpose']:
  for kind in kinds:
   for level in (fitting.LEVELS if mode=='native' else ['Tpose']):
    if not (OUT/kind/(level+'_validation.json')).exists():run(kind,level,build.ROOT/'Resources/Models/TPose'/f'OpenStance_{kind}_Tpose.blend' if mode=='tpose' else None)
 elif mode=='exports':
  p=Path(__file__).with_name('export_tailored_doboks.py');sys.argv=[str(p),'--']+kinds
  exec(compile(p.read_text(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
 elif mode in ['samples','workspace']:
  p=Path(__file__).with_name('tailor_sample_animations.py' if mode=='samples' else 'assemble_tailored_workspace.py')
  code=p.read_text().replace('Resources/Models/TailoredDoboks','Resources/Models/HairExportFinish')
  sys.argv=[str(p)];exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
 elif mode=='aux':
  run('Medium','Gear',build.ROOT/'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend')
  run('Medium','Physics',build.ROOT/'Resources/Models/Animation/Physics/LiveCloth_Pilot.blend')
 log(mode+' COMPLETE')
except:log(traceback.format_exc());raise
