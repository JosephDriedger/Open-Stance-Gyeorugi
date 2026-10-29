import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
stage=review.ROOT/'Resources/Models/SparringFitRepair'
for kind,level in [('Female_Athletic','Gameplay_High'),('Tall','Preview')]:
    deadline=time.monotonic()+7200
    while not (stage/kind/(level+'_validation.json')).exists():
        if time.monotonic()>deadline:raise RuntimeError('Native build timeout')
        time.sleep(5)
p=Path(review.__file__);code=p.read_text().replace("ROOT/'Resources/Models/CharacterSuite'/kind","ROOT/'Resources/Models/SparringFitRepair'/kind").replace('Resources/Models/SparringStyleReview_20261016','Resources/Models/SparringFitRepair')
exec(compile(code,str(p),'exec'),review.__dict__)
p=Path(__file__).with_name('check_sparring_review_surfaces.py')
exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
