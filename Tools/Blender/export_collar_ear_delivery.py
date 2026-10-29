import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
repair.OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/CollarEarRepair')
p=Path(__file__).with_name('export_tailored_doboks.py');code=p.read_text()
code=code.replace('for style in [0,1]:run(kind,style)',"for style in [0,1]:\n    if not (OUT/kind/('WhiteVNeck' if style else 'WhiteWrap')/'export_validation.json').exists():run(kind,style)")
exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
