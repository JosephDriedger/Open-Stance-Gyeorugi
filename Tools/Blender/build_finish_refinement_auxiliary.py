import sys,runpy,traceback
from pathlib import Path
p=Path(__file__).with_name('build_finish_refinement_delivery.py')
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/FinishRefinementV2')
try:
 for mode in ['tpose','samples','workspace','preview']:
  sys.argv=[str(p),'--',mode];runpy.run_path(str(p),run_name='__main__')
  with (out/'auxiliary.log').open('a') as f:f.write(mode+' COMPLETE\n')
except:(out/'auxiliary_error.log').write_text(traceback.format_exc());raise
