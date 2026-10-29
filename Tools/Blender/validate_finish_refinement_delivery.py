from pathlib import Path
p=Path(__file__).with_name('validate_hair_cloth_delivery.py')
code=p.read_text().replace('Resources/Models/HairClothRevision','Resources/Models/FinishRefinementV2')
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
