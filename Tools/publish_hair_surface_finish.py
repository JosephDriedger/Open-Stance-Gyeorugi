from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'HairExportFinish'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong'];LEVELS=['Gameplay_High','Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(p,count):
 r=read(p);assert r['passed'] and len(r['files'])==count,p
 for row in r['files']:assert sha(p.parent/row['file'])==row['sha256'],row['file']
 return r
assert read(S/'visual_review.json')['targeted_repairs_passed']
mb=check(S/'motionbuilder_validation.json',36);samples=check(S/'sample_export_validation.json',6)
assert read(S/'workspace_validation.json')['passed'] and len(read(S/'workspace_validation.json')['scenes'])==9
mapping=[]
def add(src,dst):assert src.is_file(),src;mapping.append((src,dst))
def native(kind,level,dest=None):
 r=read(S/kind/(level+'_validation.json'));src=S/kind/r['file'];original=Path(r['source'])
 assert r['passed'] and r['rig_body_actions_preserved'] and sha(src)==r['sha256'] and sha(original)==r['source_sha256'],(kind,level)
 add(src,dest or original);return src
for kind in KINDS:
 for level in LEVELS:
  src=native(kind,level)
  if level=='Preview' and kind.startswith(('Male_','Female_')):add(src,M/'CharacterVariations'/kind/'Character.blend')
  if level=='Animation':continue
  assert read(S/kind/(level+'_visual_ready.json'))['drivers_valid']
  for style in [0,1]:
   dest=M/'CharacterSuite'/kind/('WhiteVNeck' if style else '');pose='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral';add(S/kind/(level+'_'+str(style)+'_'+pose+'.png'),dest/(level+'.png'))
  if level=='Preview' and kind.startswith(('Male_','Female_')):add(S/kind/'Preview_0_Neutral.png',M/'CharacterVariations'/kind/'Full_Body.png')
 native(kind,'Tpose')
 for style in ['WhiteWrap','WhiteVNeck']:
  report=check(S/kind/style/'export_validation.json',13);dest=M/'CharacterSuite'/kind/('WhiteVNeck' if style=='WhiteVNeck' else '')
  for row in report['files']:add(S/kind/style/row['file'],dest/row['file'])
 add(S/kind/'WhiteWrap/Gameplay_High_Dobok.fbx',M/'Animation/MotionBuilder/_Sources'/('OpenStance_'+kind+'_Mocap_Source.fbx'))
for level in ['Gear','Physics','Sample_Demo','Sample_Kick']:native('Medium',level)
for row in samples['files']:
 src=S/row['file'];dest=M/'Animation/Samples'/('WhiteVNeck' if src.parent.name=='WhiteVNeck' else '');add(src,dest/src.name)
for row in mb['files']:
 src=S/row['file'];style=src.parent.name;kind=src.parent.parent.name;dest=M/'Animation/MotionBuilder'/kind/('WhiteVNeck' if style=='WhiteVNeck' else '')
 add(src,dest/src.name);add(src.with_name('validation_'+src.stem+'.json'),dest/('validation_'+src.stem+'.json'))
add(S/'OpenStance_Characters_Workspace.blend',M/'OpenStance_Characters_Workspace.blend');add(S/'workspace_validation.json',M/'Animation/workspace_validation.json')
old={}
for stage in ['FollowupFix','ExportMaterialRepair']:
 old.update({r['file'].replace('\\','/'):r['sha256'] for r in read(M/stage/'published.json')['files']})
for _,p in mapping:
 rel=p.relative_to(ROOT).as_posix()
 if p.exists() and rel in old:assert sha(p)==old[rel],('Intervening edit',rel)
archive=M/'Archive'/('Before_Hair_Surface_Finish_20261022_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  d=archive/p.relative_to(ROOT);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);assert sha(d)==sha(p)
def write(p,s):backup(p);p.write_text(s,encoding='utf-8')
print('Backing up '+str(len(mapping))+' assets',flush=True)
for i,(_,p) in enumerate(mapping):
 backup(p)
 if i%100==0:print('Backed up '+str(i),flush=True)
records=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);digest=sha(src);assert sha(dest)==digest;records.append({'file':dest.relative_to(ROOT).as_posix(),'sha256':digest})
 if len(records)%100==0:print('Installed '+str(len(records)),flush=True)
for kind in KINDS:
 p=M/'CharacterSuite'/kind/'catalog.json';cat=read(p);cat['hair_surface_finish_revision']='2026-10-22';write(p,json.dumps(cat,indent=2));records.append({'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
for p,link in [(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/HairExportFinish/README.md'),(M/'CharacterSuite/README.md','../HairExportFinish/README.md'),(M/'Animation/README.md','../HairExportFinish/README.md')]:
 lines=p.read_text(encoding='utf-8').splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 write(p,'> Latest hair repair, 2026-10-22: crew-cut shell fitted closer to the head; coarse crown texture sampling corrected. Native models, T-poses, workspace, samples and FBX targets updated. See [validation and limitations]('+link+').\n\n'+''.join(lines))
(S/'published.json').write_text(json.dumps({'archive':str(archive),'files':records,'native_profiles':63,'runtime_exports':234,'motionbuilder_targets':36,'tposes':9,'sample_exports':6},indent=2))
(S/'installation_complete.txt').write_text('Copies and hashes verified. See published.json.\n');print('Installed '+str(len(mapping))+' assets. Backup: '+str(archive),flush=True)
