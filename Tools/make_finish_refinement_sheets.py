from pathlib import Path
from make_current_visual_review import sheet
root=Path(__file__).resolve().parents[1]/'Resources/Models/FinishRefinementV2'
for d in (root/'VisualQA').iterdir():
    if not d.is_dir() or not (d/'manifest.json').exists():continue
    for label,paths,cols,w,h in [('Body',sorted(d.glob('J*.png'))+sorted(p for p in d.glob('*.png') if not p.stem.startswith(('J','H','N'))),4,240,270)]+[(f'Helmet{i}',sorted(d.glob(f'H{i}_*.png')),4,240,240) for i in range(3)]+[('BareHair',sorted(d.glob('N_*.png')),3,300,300)]:
        sheet([(p.stem,p) for p in paths],root/'VisualQA'/f'{d.name}_{label}.jpg',cols,w,h)
