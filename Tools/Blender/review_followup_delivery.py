import sys,inspect
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
source=inspect.getsource(a.load).replace("ROOT/'Resources/Models/CharacterSuite'/kind","ROOT/'Resources/Models/FollowupFix'/kind")
exec(source,a.__dict__)
p=Path(__file__).with_name('review_remaining_issues.py')
code=p.read_text().replace('Resources/Models/FollowupReview_20261020','Resources/Models/FollowupFix/Review')
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
