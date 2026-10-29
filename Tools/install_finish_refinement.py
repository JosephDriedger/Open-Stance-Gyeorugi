from pathlib import Path
import time,subprocess,sys,json
from PIL import Image
root=Path(__file__).resolve().parents[1];stage=root/'Resources/Models/FinishRefinementV2'
deadline=time.monotonic()+1800
print('Waiting for the final preview frames.',flush=True)
while not (stage/'Medium/preview.log').read_text().rstrip().endswith('COMPLETE'):
 if time.monotonic()>deadline:raise TimeoutError('Preview did not finish')
 time.sleep(5)
for folder,count in [('Frames',108),('SideFrames',36)]:
 files=list((stage/'Medium'/folder).glob('*.png'));assert len(files)==count
 for p in files:
  with Image.open(p) as im:im.verify()
assert json.loads((stage/'ExportDiagnostics/validation.json').read_text())['passed']
print('All 144 preview frames decode correctly. Installing verified delivery.',flush=True)
subprocess.run([sys.executable,str(root/'Tools/publish_finish_refinement_repair.py')],cwd=root,check=True)
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'Tools/organize_model_library.ps1')],cwd=root,check=True)
print('INSTALL AND SHORTCUTS COMPLETE',flush=True)
