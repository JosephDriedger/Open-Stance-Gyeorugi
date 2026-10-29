"""Publish validated high-detail garment repairs, preserving replaced assets."""
from pathlib import Path
import json, hashlib, shutil, datetime, subprocess
ROOT=Path(__file__).resolve().parents[1];MODELS=ROOT/'Resources/Models';STAGE=MODELS/'ROMRepair';SAMPLES=MODELS/'Animation/Samples'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports=[json.loads((STAGE/n).read_text()) for n in ['native_validation.json','export_validation.json']]
assert all(r['passed'] for r in reports)
mapping=[]
for report in reports:
 for row in report['files']:
  src=STAGE/row['file'];assert digest(src)==row['sha256'],src
  rel=src.relative_to(STAGE)
  dest=SAMPLES/rel.name if rel.parts[0]=='Updated_Medium' else MODELS/'CharacterSuite'/rel
  mapping.append((src,dest))
assert len(mapping)==31
mapping.append((STAGE/'Updated_Medium/Front_Kick.blend',SAMPLES/'Front_Kick.blend'))
assert (STAGE/'Updated_Medium/preview.log').read_text().rstrip().endswith('COMPLETE')
for folder,count in [('Frames',108),('SideFrames',36)]:
 files=sorted((STAGE/'Updated_Medium'/folder).glob('*.png'));assert len(files)==count
 mapping.extend((p,SAMPLES/folder/p.name) for p in files)
archive=MODELS/'Archive'/('Before_ROM_Repair_20261012_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  dest=archive/p.relative_to(MODELS);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert digest(p)==digest(dest)
for _,dest in mapping:backup(dest)
for n in ['Fighter_Demo.gif','Fighter_Demo.mp4','Front_Kick_Preview.gif','Front_Kick_Side.gif','README.md']:backup(SAMPLES/n)
for p in (SAMPLES/'PreviewFrames').glob('*.png'):backup(p)
backup(MODELS/'Animation/RangeOfMotion/REPORT.md')
backup(MODELS/'CharacterSuite/README.md')
start=ROOT/'Models and Rigs/START HERE.md'
if start.exists():shutil.copy2(start,archive/'Models_and_Rigs_START_HERE.md')
published=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);assert digest(src)==digest(dest)
 published.append({'file':str(dest.relative_to(MODELS)),'sha256':digest(dest)})
subprocess.run(['py',str(ROOT/'Tools/encode_sample_fighter_preview.py')],check=True)
shutil.copy2(STAGE/'SAMPLES_README.md',SAMPLES/'README.md')
old=MODELS/'Animation/RangeOfMotion/REPORT.md'
notice='> Historical pre-repair audit. See [the repair report](../../ROMRepair/README.md) for the current high-detail assets and remaining scope.\n\n'
content=old.read_text(encoding='utf-8')
if not content.startswith(notice):old.write_text(notice+content,encoding='utf-8')
suite=MODELS/'CharacterSuite/README.md'
notice='> 2026-10-12 garment repair: only Gameplay_High and its Dobok/Sparring FBXs have the latest underarm, hip and belt fixes. Other profiles retain earlier garments. See [repair scope and validation](../ROMRepair/README.md). Existing polygon catalogs predate these garment changes.\n\n'
content=suite.read_text(encoding='utf-8')
if not content.startswith(notice):suite.write_text(notice+content,encoding='utf-8')
notice='> Latest garment repair (2026-10-12): use folder 04, High - Editable fighter, or its matching FBXs for the repaired clothing. Folder 08 contains the refreshed Medium demo. MotionBuilder targets, animation masters and other LODs still have earlier garments. For mocap, solve on the existing characterized skeleton and transfer the result to the repaired High model. See folder 07, Garment repairs - Current scope.\n\n'
content=start.read_text(encoding='utf-8')
if not content.startswith(notice):start.write_text(notice+content,encoding='utf-8')
(STAGE/'published.json').write_text(json.dumps({'archive':str(archive),'files':published},indent=2))
print('Published high-detail repairs and samples. Backup: '+str(archive))
