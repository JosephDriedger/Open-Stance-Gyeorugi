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
for kind in build.PRESETS:
 for level in ['Crowd_Near','Crowd_Far']:run(kind,level)
