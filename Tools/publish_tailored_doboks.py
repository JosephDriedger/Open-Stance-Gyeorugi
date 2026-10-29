from pathlib import Path
import json,hashlib,shutil,datetime,subprocess
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'TailoredDoboks'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
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
native=check(S/'delivery_validation.json',63);mb=check(S/'motionbuilder_validation.json',36);samples=check(S/'sample_export_validation.json',6)
w=read(S/'workspace_validation.json');assert w['passed'] and len(w['scenes'])==9
assert (S/'Medium/preview.log').read_text().rstrip().endswith('COMPLETE')
mapping=[]
def add(src,dest):assert src.is_file(),src;mapping.append((src,dest))
for row in native['files']:
 src=S/row['file'];kind=row['preset'];level=row['profile'];dest=M/'Animation'/src.name if level=='Animation' else M/'CharacterSuite'/kind/src.name;add(src,dest)
 if level=='Preview' and kind.startswith(('Male_','Female_')):add(src,M/'CharacterVariations'/kind/'Character.blend')
 if level!='Animation':
  pose='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
  for style in [0,1]:
   dest=M/'CharacterSuite'/kind
   if style:dest=dest/'WhiteVNeck'
   add(S/kind/(level+'_'+str(style)+'_'+pose+'.png'),dest/(level+'.png'))
  if level=='Preview' and kind.startswith(('Male_','Female_')):add(S/kind/'Preview_0_Neutral.png',M/'CharacterVariations'/kind/'Full_Body.png')
for kind in KINDS:
 for style in ['WhiteWrap','WhiteVNeck']:
  report=check(S/kind/style/'export_validation.json',13);dest=M/'CharacterSuite'/kind
  if style=='WhiteVNeck':dest=dest/style
  for row in report['files']:add(S/kind/style/row['file'],dest/row['file'])
 add(S/kind/'WhiteWrap/Gameplay_High_Dobok.fbx',M/'Animation/MotionBuilder/_Sources'/('OpenStance_'+kind+'_Mocap_Source.fbx'))
for row in mb['files']:
 src=S/row['file'];style=src.parent.name;kind=src.parent.parent.name;dest=M/'Animation/MotionBuilder'/kind
 if style=='WhiteVNeck':dest=dest/style
 add(src,dest/src.name);add(src.with_name('validation_'+src.stem+'.json'),dest/('validation_'+src.stem+'.json'))
for level in ['Sample_Demo','Sample_Kick']:
 r=read(S/'Medium'/(level+'_validation.json'));src=S/'Medium'/r['file'];assert r['passed'] and sha(src)==r['sha256'];add(src,M/'Animation/Samples'/src.name)
for row in samples['files']:
 src=S/row['file'];dest=M/'Animation/Samples'
 if src.parent.name=='WhiteVNeck':dest=dest/'WhiteVNeck'
 add(src,dest/src.name)
for folder,count in [('Frames',108),('SideFrames',36)]:
 files=list((S/'Medium'/folder).glob('*.png'));assert len(files)==count
 for src in files:add(src,M/'Animation/Samples'/folder/src.name)
add(S/'OpenStance_Characters_Workspace.blend',M/'OpenStance_Characters_Workspace.blend');add(S/'workspace_validation.json',M/'Animation/workspace_validation.json')
archive=M/'Archive'/('Before_Tailored_Doboks_20261015_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  dest=archive/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
def write(p,s):backup(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
for _,p in mapping:backup(p)
for n in ['Fighter_Demo.gif','Fighter_Demo.mp4','Front_Kick_Preview.gif','Front_Kick_Side.gif']:backup(M/'Animation/Samples'/n)
for p in (M/'Animation/Samples/PreviewFrames').glob('*.png'):backup(p)
records=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);digest=sha(src);assert sha(dest)==digest;records.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})
subprocess.run(['py',str(ROOT/'Tools/encode_sample_fighter_preview.py')],check=True)
for kind in KINDS:
 p=M/'CharacterSuite'/kind/'catalog.json';catalog=read(p);catalog['dobok_fit_revision']='2026-10-15'
 for row in native['files']:
  if row['preset']==kind and row['profile']!='Animation':
   profile=catalog.setdefault('profiles',{}).setdefault(row['profile'],{})
   profile.pop('visible_evaluated_triangles',None)
   profile['visible_total']=row['style_triangle_counts']['0'];profile['visible_totals_by_jacket_style']=row['style_triangle_counts'];profile['dobok_fit_revision']='2026-10-15'
 write(p,json.dumps(catalog,indent=2))
for p,link in [(M/'Animation/README.md','../TailoredDoboks/README.md'),(M/'CharacterSuite/README.md','../TailoredDoboks/README.md'),(M/'CharacterVariations/README.md','../TailoredDoboks/README.md'),(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/TailoredDoboks/README.md'),(M/'Animation/Samples/README.md','../../TailoredDoboks/README.md')]:
 text=p.read_text(encoding='utf-8');lines=text.splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 write(p,'> Tailored dobok fit, 2026-10-15: both uniform styles now have less torso, sleeve and trouser bulk, with original body shapes and rigs retained. Current files, animations and characterized targets use the updated fit. See [fit changes and validation]('+link+').\n\n'+''.join(lines))
for folder in ['ROMRepair','GarmentRollout','AlternateJacketRepair']:
 p=M/folder/'README.md';write(p,'> Follow-up: [TailoredDoboks](../TailoredDoboks/README.md) is the current slimmer-fit revision. This report describes the preceding repair.\n\n'+p.read_text(encoding='utf-8'))
(S/'published.json').write_text(json.dumps({'archive':str(archive),'files':records,'native_profiles':63,'runtime_exports':234,'sample_exports':6,'motionbuilder_targets':36},indent=2))
print('Published '+str(len(records))+' assets. Backup: '+str(archive))
