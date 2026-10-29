from pathlib import Path
from PIL import Image,ImageDraw
root=Path('Resources/Models/CollarEarRepair')
out=root/'Sheets';out.mkdir(exist_ok=True)
for d in (root/'QA').glob('*'):
 files=sorted(d.glob('*.png'))
 if len(files)!=20:continue
 canvas=Image.new('RGB',(1200,5*322),'#222222');draw=ImageDraw.Draw(canvas)
 for i,p in enumerate(files):
  im=Image.open(p).convert('RGB');im.thumbnail((300,300));x=(i%4)*300;y=(i//4)*322;canvas.paste(im,(x,y));draw.text((x+4,y+301),p.stem,fill='white')
 canvas.save(out/(d.name+'.jpg'))
