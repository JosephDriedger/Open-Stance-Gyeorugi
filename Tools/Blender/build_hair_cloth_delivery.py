import sys
from pathlib import Path
p=Path(__file__).with_name('build_opening_delivery.py')
code=p.read_text().replace('import repair_garment_openings as fix','import enhance_hair_cloth as fix').replace('Resources/Models/OpeningRepair','Resources/Models/HairClothRevision').replace("'opening_overlap'","'hair_cloth_setup'")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
