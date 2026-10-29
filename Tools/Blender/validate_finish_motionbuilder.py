"""Resume export checks in a fresh Blender process after native validation."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
repair.OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/FinishRefinementV2')
assert json.loads((repair.OUT/'delivery_validation.json').read_text())['passed']
p=Path(__file__).with_name('validate_tailored_delivery.py');code=p.read_text()
start=code.index('try:\n');end=code.index(' mb=[]',start)
code=code[:start]+'try:\n'+code[end:]
exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
