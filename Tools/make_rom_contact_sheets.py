from pathlib import Path
import sys
from PIL import Image,ImageOps,ImageDraw
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('Resources/Models/Animation/RangeOfMotion')
for folder in root.iterdir():
 if not folder.is_dir():continue
 for mode in ['Dobok','Gear']:
  paths=[p for p in sorted(folder.glob(mode+'_*.png')) if not p.stem.endswith('_Side')]
  if len(paths)!=23:continue
  sheet=Image.new('RGB',(1000,6*304+40),(235,235,235));d=ImageDraw.Draw(sheet);d.text((12,12),folder.name+' / '+mode+' / ROM checkpoints',fill='black')
  for i,p in enumerate(paths):
   im=Image.open(p).convert('RGB').resize((250,281));x=(i%4)*250;y=40+(i//4)*304;sheet.paste(im,(x,y));d.text((x+5,y+283),p.stem.split('_',2)[-1],fill='black')
  sheet.save(folder/(mode+'_ContactSheet.jpg'))

