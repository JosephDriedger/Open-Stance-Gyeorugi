from pathlib import Path
import time,subprocess,json
from PIL import Image
root=Path(__file__).resolve().parents[1];stage=root/'Resources/Models/CollarEarRepair';deadline=time.monotonic()+7200
required=['ear_topology_validation.json','visual_review.json','delivery_validation.json','motionbuilder_validation.json','workspace_validation.json','exports_validation.json','sample_export_validation.json','cloth_pilot.json','Gear/validation.json']
while True:
 if time.monotonic()>deadline:raise TimeoutError('Delivery incomplete')
 log=stage/'Medium/preview.log'
 if all((stage/p).exists() for p in required) and log.exists() and log.read_text().rstrip().endswith('COMPLETE'):break
 time.sleep(5)
for folder,count in [('Frames',108),('SideFrames',36)]:
 paths=list((stage/'Medium'/folder).glob('*.png'));assert len(paths)==count
 for p in paths:
  with Image.open(p) as im:im.verify()
subprocess.run(['py',str(root/'Tools/publish_collar_ear_repair.py')],check=True,cwd=root)
subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'Tools/organize_model_library.ps1')],check=True,cwd=root)
(stage/'installation_complete.txt').write_text('Publication and shortcut verification complete')
