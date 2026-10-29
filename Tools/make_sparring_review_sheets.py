from pathlib import Path
from make_current_visual_review import sheet,KINDS
OUT=Path(__file__).resolve().parents[1]/'Resources/Models/SparringStyleReview_20261016'
for k in KINDS:
 for mode in ['body','hair','lod']:
  d=OUT/k/mode
  if not (d/'manifest.json').exists():continue
  paths=sorted(d.glob('*.png'))
  if mode=='body':
   for label in ['Front','Rear','Motion']:
    selected=[p for p in paths if (p.stem.startswith('Motion') if label=='Motion' else p.stem.endswith(label))]
    sheet([(p.stem,p) for p in selected],OUT/f'{k}_{label}.jpg',4 if label!='Rear' else 3,240,270)
  elif mode=='hair':
   for h in range(3):
    selected=[p for p in paths if p.stem.startswith(f'H{h}_')]
    sheet([(p.stem,p) for p in selected],OUT/f'{k}_Helmet{h}_Hair.jpg',3,260,260)
  else:sheet([(p.stem,p) for p in paths],OUT/f'{k}_LOD.jpg',2,300,338)
