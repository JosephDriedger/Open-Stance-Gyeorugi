import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
if '--' in sys.argv:
 args=sys.argv[sys.argv.index('--')+1:]
 if len(args)>1:build.PRESETS=args[1:]
p=Path(__file__).with_name('build_opening_delivery.py')
code=p.read_text().replace('import repair_garment_openings as fix','import repair_collar_ears as fix').replace('Resources/Models/OpeningRepair','Resources/Models/CollarEarRepair').replace("'opening_overlap'","'collar_ear_repair'")
code=code.replace("['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']","['Arms_Overhead','Knee_L']")
code=code.replace("sys.argv=[str(p)]", "sys.argv=[str(p)]\n  if mode=='preview':code=code.replace('bpy.ops.render.render(write_still=True)', '(bpy.ops.render.render(write_still=True) if not Path(scene.render.filepath).exists() else None)')")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
