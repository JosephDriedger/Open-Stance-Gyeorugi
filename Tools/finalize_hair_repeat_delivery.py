from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'FinalRefinement/HairRepeat'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
report=read(S/'published.json');assert report['passed'] and len(report['files'])==81
for row in report['files']:assert sha(ROOT/row['file'])==row['sha256'],row['file']
old=read(M/'HairExportFinish/published.json');unchanged=[]
for row in old['files']:
 if row['file'].endswith('.blend'):continue
 assert sha(ROOT/row['file'])==row['sha256'],row['file'];unchanged.append(row)
assert read(S/'export_compatibility.json')['passed']
review=read(S/'Review/manifest.json');assert review['passed_controls'] and len(review['renders'])==108
for row in review['renders']:assert (S/'Review'/row['file']).is_file()
for p,link in [(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/FinalRefinement/README.md'),(M/'CharacterSuite/README.md','../FinalRefinement/README.md'),(M/'Animation/README.md','../FinalRefinement/README.md')]:
 backup=Path(report['archive'])/p.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(p,backup)
 lines=p.read_text(encoding='utf-8').splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 p.write_text('> Latest repair, 2026-10-23: hair UV-wrap seam fixed across 81 native Blender files. Experimental cloth kick study available; long-hair refinement and full cloth/contact validation remain unfinished. See [scope and validation]('+link+').\n\n'+''.join(lines),encoding='utf-8')
report['unchanged_non_blender_assets_verified']=len(unchanged);report['review_images']=108;report['export_reimports']=9
(S/'delivery_validation.json').write_text(json.dumps(report,indent=2))
(S/'installation_complete.txt').write_text('81 native files verified. See delivery_validation.json and ../README.md for scope and limitations.\n')
print('Verified 81 native files and '+str(len(unchanged))+' unchanged non-Blender assets.')
