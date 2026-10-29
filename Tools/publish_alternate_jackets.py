from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'AlternateJacketRepair'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def check(p,count):
 r=read(p);assert r['passed'] and len(r['files'])==count,p
 for row in r['files']:assert sha(p.parent/row['file'])==row['sha256'],row['file']
 return r
native=check(S/'delivery_validation.json',63);exports=[check(S/k/'export_validation.json',13) for k in KINDS];mb=check(S/'motionbuilder_validation.json',18);samples=check(S/'sample_export_validation.json',3)
w=read(S/'workspace_validation.json');assert w['passed'] and len(w['scenes'])==9
mapping=[]
def add(src,dest):assert src.is_file(),src;mapping.append((src,dest))
for row in native['files']:
 src=S/row['file'];kind=row['preset'];level=row['profile'];dest=M/'Animation'/src.name if level=='Animation' else M/'CharacterSuite'/kind/src.name
 add(src,dest)
 if level=='Preview' and kind.startswith(('Male_','Female_')):add(src,M/'CharacterVariations'/kind/'Character.blend')
 if level!='Animation':
  pose='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
  add(S/kind/(level+'_'+pose+'.png'),M/'CharacterSuite'/kind/'WhiteVNeck'/(level+'.png'))
for kind,r in zip(KINDS,exports):
 for row in r['files']:add(S/kind/row['file'],M/'CharacterSuite'/kind/'WhiteVNeck'/row['file'])
for row in mb['files']:
 src=S/row['file'];dest=M/'Animation/MotionBuilder'/src.parent.name/'WhiteVNeck'/src.name;add(src,dest)
 add(src.with_name('validation_'+src.stem+'.json'),dest.with_name('validation_'+src.stem+'.json'))
for level in ['Sample_Demo','Sample_Kick']:
 r=read(S/'Medium'/(level+'_validation.json'));assert r['passed'];src=S/'Medium'/r['file'];assert sha(src)==r['sha256'];add(src,M/'Animation/Samples'/src.name)
for row in samples['files']:
 src=S/row['file'];add(src,M/'Animation/Samples/WhiteVNeck'/src.name)
add(S/'OpenStance_Characters_Workspace.blend',M/'OpenStance_Characters_Workspace.blend');add(S/'workspace_validation.json',M/'Animation/workspace_validation.json')
archive=M/'Archive'/('Before_Alternate_Jacket_Repair_20261013_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  dest=archive/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
def write(p,s):backup(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
for _,p in mapping:backup(p)
records=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);digest=sha(src);assert sha(dest)==digest;records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})
for p,link in [(M/'Animation/README.md','../AlternateJacketRepair/README.md'),(M/'CharacterSuite/README.md','../AlternateJacketRepair/README.md'),(M/'CharacterVariations/README.md','../AlternateJacketRepair/README.md'),(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/AlternateJacketRepair/README.md'),(M/'Animation/Samples/README.md','../../AlternateJacketRepair/README.md')]:
 text=p.read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 notice='> Alternate jacket repair, 2026-10-13: JacketStyle 1 (white V-neck) now uses the fitted hem and hip corrections in every current native profile. Alternate FBXs and characterized targets are in WhiteVNeck subfolders. See [usage and validation]('+link+').\n\n'
 write(p,notice+''.join(lines))
for folder in ['ROMRepair','GarmentRollout']:
 p=M/folder/'README.md';text=p.read_text(encoding='utf-8');notice='> Follow-up: the alternate V-neck jacket is now repaired too. See [AlternateJacketRepair](../AlternateJacketRepair/README.md). Scope exclusions below describe this earlier pass.\n\n';write(p,notice+text)
(S/'published.json').write_text(json.dumps({'archive':str(archive),'files':records,'native_profiles':63,'alternate_runtime_exports':117,'alternate_sample_exports':3,'alternate_motionbuilder_targets':18},indent=2))
print('Published '+str(len(records))+' assets. Backup: '+str(archive))
