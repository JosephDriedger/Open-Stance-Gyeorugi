import sys
from pathlib import Path
p=Path(__file__).with_name('build_opening_delivery.py')
code=p.read_text().replace('import repair_garment_openings as fix','import repair_visual_fit as fix').replace('Resources/Models/OpeningRepair','Resources/Models/VisualFitRepair').replace("'opening_overlap'","'visual_fit_repair'")
code=code.replace("['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']","['Arms_Overhead','Elbows_Flexed','Knee_L','Deep_Squat','Wrists_Flexed','Ankle_Flexed']")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
