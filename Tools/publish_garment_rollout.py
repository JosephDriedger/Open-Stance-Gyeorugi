"""Install the remaining validated profiles and characterized mocap targets."""
from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];MODELS=ROOT/'Resources/Models';STAGE=MODELS/'GarmentRollout'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def checked(p,count):
 r=read(p);assert r['passed'] and len(r['files'])==count,p
 for row in r['files']:assert sha(p.parent/row['file'])==row['sha256'],row['file']
 return r
native=checked(STAGE/'delivery_validation.json',54);mb=checked(STAGE/'motionbuilder_validation.json',18)
workspace=read(STAGE/'workspace_validation.json');assert workspace['passed'] and len(workspace['scenes'])==9
mapping=[]
def add(src,dest):assert src.is_file(),src;mapping.append((src,dest))
for row in native['files']:
 kind=row['preset'];level=row['profile'];src=STAGE/row['file']
 dest=MODELS/'Animation'/src.name if level=='Animation' else MODELS/'CharacterSuite'/kind/src.name
 add(src,dest)
 if level=='Preview' and kind.startswith(('Male_','Female_')):add(src,MODELS/'CharacterVariations'/kind/'Character.blend')
 preview=STAGE/kind/(level+('_Crowd_StandingIdle' if level.startswith('Crowd') else '_Neutral')+'.png')
 if level!='Animation':add(preview,MODELS/'CharacterSuite'/kind/(level+'.png'))
 if level=='Preview' and kind.startswith(('Male_','Female_')):add(preview,MODELS/'CharacterVariations'/kind/'Full_Body.png')
for kind in KINDS:
 report=checked(STAGE/kind/'export_validation.json',11)
 for row in report['files']:add(STAGE/kind/row['file'],MODELS/'CharacterSuite'/kind/row['file'])
 for p in (STAGE/kind).glob('*_native_validation.json'):add(p,MODELS/'CharacterSuite'/kind/('Garment_'+p.name))
 for clip in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
  add(STAGE/kind/('Crowd_Near_Crowd_'+clip+'.png'),MODELS/'CharacterSuite'/kind/('Crowd_'+clip+'.png'))
 add(MODELS/'CharacterSuite'/kind/'Gameplay_High_Dobok.fbx',MODELS/'Animation/MotionBuilder/_Sources'/('OpenStance_'+kind+'_Mocap_Source.fbx'))
for row in mb['files']:
 src=STAGE/row['file'];kind=src.parent.name
 add(src,MODELS/'Animation/MotionBuilder'/kind/src.name)
 add(src.with_name('validation_'+src.stem+'.json'),MODELS/'Animation/MotionBuilder'/kind/('validation_'+src.stem+'.json'))
add(STAGE/'OpenStance_Characters_Workspace.blend',MODELS/'OpenStance_Characters_Workspace.blend')
add(STAGE/'workspace_validation.json',MODELS/'Animation/workspace_validation.json')
archive=MODELS/'Archive'/('Before_Garment_Rollout_20261013_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  dest=archive/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
def write(p,s):backup(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
for _,dest in mapping:backup(dest)
records=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);assert sha(src)==sha(dest)
 records.append({'file':str(dest.relative_to(ROOT)),'sha256':sha(dest)})
for kind in KINDS:
 p=MODELS/'CharacterSuite'/kind/'catalog.json';catalog=read(p)
 catalog['garment_revision']='2026-10-13';catalog['garment_validation']='../../GarmentRollout/README.md'
 for row in native['files']:
  if row['preset']==kind and row['profile']!='Animation':
   profile=catalog.setdefault('profiles',{}).setdefault(row['profile'],{})
   profile['visible_evaluated_triangles']=row['parts'];profile['visible_total']=row['visible_evaluated_triangles'];profile['garment_revision']='2026-10-13'
   validation=MODELS/'CharacterSuite'/kind/(row['profile']+'_validation.json')
   info=read(validation) if validation.exists() else {}
   for obsolete in ['visible_base_triangles','base_triangles','parts']:info.pop(obsolete,None)
   info.update(garment_revision='2026-10-13',visible_evaluated_triangles=row['parts'],visible_evaluated_total=row['visible_evaluated_triangles'],garment_drivers_valid=True)
   write(validation,json.dumps(info,indent=2))
 write(p,json.dumps(catalog,indent=2))
notice='> 2026-10-13: garment repairs now include Preview, gameplay Mid/Far, both crowd LODs, all animation masters, the shared workspace and all 18 characterized MotionBuilder targets. High-detail models and Medium samples were repaired in the preceding pass. See '
for p,link in [(MODELS/'CharacterSuite/README.md','../GarmentRollout/README.md'),(MODELS/'Animation/README.md','../GarmentRollout/README.md'),(MODELS/'ROMRepair/README.md','../GarmentRollout/README.md'),(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/GarmentRollout/README.md')]:
 content=p.read_text(encoding='utf-8');lines=content.splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 write(p,notice+'[the current repair report]('+link+').\n\n'+''.join(lines))
(STAGE/'published.json').write_text(json.dumps({'archive':str(archive),'files':records,'native_files':54,'exports':99,'motionbuilder_targets':18},indent=2))
print('Published '+str(len(records))+' assets. Archive: '+str(archive))
