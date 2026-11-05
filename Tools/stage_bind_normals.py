import json
from concurrent.futures import ProcessPoolExecutor
import repair_fbx_bind_normals as repair
if __name__=='__main__':
 files=json.loads((repair.OUT.parent/'UniformGeometryDelivery/export_inputs.json').read_text())
 (repair.OUT/'inputs.json').write_text(json.dumps(files,indent=2))
 with ProcessPoolExecutor(max_workers=2) as pool:list(pool.map(repair.run,files))
 print('ALL_BIND_NORMALS_STAGED',len(files),flush=True)
