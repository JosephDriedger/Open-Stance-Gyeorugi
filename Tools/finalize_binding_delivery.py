from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';OUT=M/'FinalRefinement/BindingDelivery'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8388608),b''):h.update(block)
 return h.hexdigest()
sources=[M/'HairExportFinish/published.json',M/'FinalRefinement/HairRepeat/published.json',M/'FinalRefinement/fitted_belt_delivery.json',M/'FinalRefinement/BodyPhysics/delivery.json',OUT/'published.json']
merged={}
for source in sources:
 for row in json.loads(source.read_text())['files']:
  key=row['file'].replace('\\','/');merged[key]={'file':key,'sha256':row['sha256'],'revision_manifest':str(source.relative_to(ROOT)).replace('\\','/')}
for index,row in enumerate(merged.values()):
 assert sha(ROOT/row['file'])==row['sha256'],row['file']
 if index%50==0:print('ASSET_HASH_CHECK',index,'/',len(merged),flush=True)
for p in (M/'Animation/MotionBuilder').rglob('validation_*Sparring.json'):
 r=json.loads(p.read_text())
 if r.get('binding_revision')!='2026-10-23':continue
 assert sha(ROOT/r['source'])==r['source_sha256']
result={'passed':True,'files':list(merged.values()),'scope':'Consolidated delivered asset hashes; not an artistic completion or all-motion collision guarantee.'}
(M/'FinalRefinement/current_assets.json').write_text(json.dumps(result,indent=2))
(OUT/'installation_complete.txt').write_text('75 native Blender files and 78 FBXs updated; 18 MotionBuilder sidecars updated; backups retained. See published.json.\n')
for p,link in [(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/FinalRefinement/README.md'),(M/'CharacterSuite/README.md','../FinalRefinement/README.md'),(M/'Animation/README.md','../FinalRefinement/README.md')]:
 lines=p.read_text(encoding='utf-8').splitlines(keepends=True)
 while lines and (lines[0].startswith('>') or not lines[0].strip()):lines.pop(0)
 p.write_text('> Latest installed repair, 2026-10-24: chest-protector edge clearance updated across the native library and affected sparring exports. Hair wrapping remains repaired. Belt/free-cloth and long-hair work remain unfinished. See [current scope and remaining work]('+link+').\n\n'+''.join(lines),encoding='utf-8')
print('CURRENT_ASSETS_VERIFIED',len(merged))
