"""Validate newly generated FBX metadata before replacing its raw export."""
from pathlib import Path
import sys, hashlib
ROOT=Path(__file__).resolve().parents[2]
def finalize(path):
 sys.path.insert(0,str(ROOT/'Tools'))
 import repair_fbx_bind_normals as repair
 path=Path(path).resolve();rel=path.relative_to(ROOT).as_posix()
 target,report=repair.run(rel,ROOT/'Saved/ExportValidation/BindNormals')
 with path.open('rb') as stream:
  assert hashlib.file_digest(stream,'sha256').hexdigest()==report['before_sha256']
 target.replace(path)
 return report
