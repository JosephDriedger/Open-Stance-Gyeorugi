import json
from concurrent.futures import ProcessPoolExecutor
import repair_fbx_uniform_geometry as repair
def job(rel):
 repair.run(rel)
if __name__=='__main__':
 root=repair.ROOT
 files={r['file'] for r in json.loads((repair.OUT.parent/'current_assets.json').read_text())['files'] if r['file'].endswith('.fbx')}
 for p in (root/'Resources/Models/Animation/MotionBuilder_BeltChain').rglob('*.fbx'):files.add(p.relative_to(root).as_posix())
 for folder in ('MotionBuilder','MotionBuilder_BeltChain'):
  for p in (root/'Resources/Models/Animation'/folder).rglob('validation_*.json'):
   source=json.loads(p.read_text()).get('source')
   if source and (root/source).is_file():files.add((root/source).resolve().relative_to(root).as_posix())
 (repair.OUT/'export_inputs.json').write_text(json.dumps(sorted(files),indent=2))
 with ProcessPoolExecutor(max_workers=2) as pool:list(pool.map(job,sorted(files)))
 print('ALL_EXPORTS_STAGED',len(files),flush=True)
