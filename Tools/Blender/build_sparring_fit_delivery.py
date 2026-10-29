import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
if '--' in sys.argv:
 args=sys.argv[sys.argv.index('--')+1:]
 if len(args)>1:build.PRESETS=args[1:]
p=Path(__file__).with_name('build_opening_delivery.py')
code=p.read_text().replace('import repair_garment_openings as fix','import repair_sparring_fit as fix').replace('Resources/Models/OpeningRepair','Resources/Models/SparringFitRepair').replace("'opening_overlap'","'sparring_fit_repair'")
code=code.replace("['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']","['Arms_Overhead','Knee_L']")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
