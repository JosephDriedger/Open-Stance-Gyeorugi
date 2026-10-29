import sys,time,runpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
b.OUT=b.ROOT/'Resources/Models/AlternateJacketRepair'
deadline=time.monotonic()+3600
while not all((b.OUT/k/'Animation_validation.json').exists() for k in b.PRESETS):
 if time.monotonic()>deadline:raise RuntimeError('Animation scene build timeout')
 time.sleep(5)
runpy.run_path(str(Path(__file__).with_name('assemble_updated_workspace.py')),run_name='__main__')
