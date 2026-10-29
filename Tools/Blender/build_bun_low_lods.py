from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as profiles
profiles.LEVELS=['Gameplay_Far','Crowd_Near','Crowd_Far']
p=Path(__file__).with_name('build_bun_refinement.py');code=p.read_text()
code=code.replace('if check.exists():return', "if check.exists() and json.loads(check.read_text())['repair'].get('lod_budgeted'):return")
code=code.replace("  run(kind,'Tpose',fix.ROOT/'Resources/Models/TPose'/f'OpenStance_{kind}_Tpose.blend')",'')
code=code.replace(" if 'Medium' in kinds:",' if False:')
exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
