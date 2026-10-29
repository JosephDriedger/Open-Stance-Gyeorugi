import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import audit_fighter_range as audit
STAGE=audit.ROOT/'Resources/Models/ROMRepair';audit.OUT=STAGE/'Audit';audit.OUT.mkdir(exist_ok=True)
try:
 for kind in ['Updated_Medium','Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']:
  source=STAGE/kind/('Medium_Sparring_Samples.blend' if kind=='Updated_Medium' else 'Gameplay_High.blend')
  audit.audit(kind,source_override=source)
except:audit.log(traceback.format_exc());raise
