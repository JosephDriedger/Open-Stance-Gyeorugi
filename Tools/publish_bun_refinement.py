"""Publish the reviewed bun geometry, keeping other exported hairstyles intact."""
from pathlib import Path
import json,hashlib,shutil,datetime,subprocess
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'HairFormRefinement'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
assert read(S/'visual_review.json')['passed']
assert (S/'auxiliary_complete.txt').exists()
reports=list(S.glob('*/*_validation.json'));assert len(reports)==74,len(reports)
mapping=[]
for p in reports:
 r=read(p);src=p.parent/r['file'];assert r['passed'] and sha(src)==r['sha256']
 mapping.append((src,ROOT/r['source']))
 if p.name=='Preview_validation.json' and p.parent.name.startswith(('Male_','Female_')):mapping.append((src,M/'CharacterVariations'/p.parent.name/'Character.blend'))
exports=read(S/'exports_validation.json');assert exports['passed'] and len(exports['files'])==18
for r in exports['files']:
 src=S/r['file'];assert sha(src)==r['sha256'];mapping.append((src,M/'CharacterSuite'/src.parent.name/'HairstyleSamples'/src.name))
w=read(S/'workspace_validation.json');assert w['passed'] and len(w['scenes'])==9
mapping.append((S/'OpenStance_Characters_Workspace.blend',M/'OpenStance_Characters_Workspace.blend'))
archive=M/'Archive'/('Before_Bun_Refinement_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  dest=archive/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
print('Backing up '+str(len(mapping))+' assets',flush=True)
for i,(src,dest) in enumerate(mapping,1):
 backup(dest)
 if i%20==0:print('Backup '+str(i),flush=True)
rows=[]
for i,(src,dest) in enumerate(mapping,1):
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);digest=sha(src);assert sha(dest)==digest;rows.append({'file':str(dest.relative_to(ROOT)),'sha256':digest})
 if i%20==0:print('Installed '+str(i),flush=True)
p=ROOT/'Models and Rigs/START HERE.md';backup(p);text=p.read_text(encoding='utf-8');p.write_text('> Bun refinement, 2026-10-19: rounded coil, corrected scalp/neck attachment, and matching hair tie across all editable presets. [Details](../Resources/Models/HairFormRefinement/README.md).\n\n'+text,encoding='utf-8')
(S/'published.json').write_text(json.dumps({'files':rows,'backup':str(archive)},indent=2))
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Tools/organize_model_library.ps1')],check=True,cwd=ROOT)
print('Published '+str(len(rows))+' assets. Backup: '+str(archive),flush=True)
