"""Publish only the validated trouser physics settings, retaining rollback copies."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/FinalRefinement/PantsClothDeliveryV3'
CURRENT=OUT.parent/'current_assets.json';ARCHIVE=ROOT/'Resources/Models/Archive/Before_Pants_Cloth_20261030'
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert not (OUT/'published.json').exists() and not ARCHIVE.exists()
 rows=[read(p) for p in OUT.glob('native_*.json')]
 assert len(rows)==102 and {r['file'] for r in rows}==set(read(OUT/'inputs.json'))
 checks=[read(p) for p in OUT.glob('*/validation.json')]
 assert len(checks)==9 and all(r['passed'] and r['frames']==144 for r in checks)
 assert read(OUT/'visual_review.json')['pants_accepted']
 assert read(OUT/'secondary_motion.json')['passed']
 assert all(not r['changed'] or r.get('reopened_preservation_passed') for r in rows)
 baseline=read(CURRENT);assets={r['file']:r for r in baseline['files']}
 changes=[r for r in rows if r['changed']]
 for r in rows:
  assert sha(ROOT/r['file'])==r['before_sha256'],r['file']
  if r['changed']:assert sha(OUT/'Files'/r['file'])==r['sha256'],r['file']
 assert shutil.disk_usage(ROOT).free>sum((ROOT/r['file']).stat().st_size for r in changes)+1024**3
 ARCHIVE.mkdir(parents=True);shutil.copy2(CURRENT,ARCHIVE/'current_assets_before.json')
 for r in changes:
  dst=ARCHIVE/r['file'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/r['file'],dst)
  assert sha(dst)==r['before_sha256'];print('PANTS_CLOTH_ARCHIVED',r['file'],flush=True)
 for r in changes:
  dst=ROOT/r['file'];assert sha(dst)==r['before_sha256'];shutil.copy2(OUT/'Files'/r['file'],dst)
  assert sha(dst)==r['sha256'];print('PANTS_CLOTH_INSTALLED',r['file'],flush=True)
  assets[r['file']]={'file':r['file'],'sha256':r['sha256'],'revision_manifest':'Resources/Models/FinalRefinement/PantsClothDeliveryV3/published.json'}
 result={'passed':True,'native_changed':len(changes),'native_checked':len(rows),'archive':str(ARCHIVE),'files':changes,'scope':'Trouser cloth settings, pin group and hidden limb contacts only. Lower-jacket and belt physics are not fixed. FBX files unchanged; live Blender physics is not carried in skeletal FBX.'}
 (OUT/'published.json').write_text(json.dumps(result,indent=2))
 temp=CURRENT.with_suffix('.pending.json');temp.write_text(json.dumps({'passed':True,'files':list(assets.values())},indent=2));temp.replace(CURRENT)
 (OUT/'installation_complete.txt').write_text(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
 print('PANTS_CLOTH_INSTALL_COMPLETE',len(changes),flush=True)
if __name__=='__main__':main()


