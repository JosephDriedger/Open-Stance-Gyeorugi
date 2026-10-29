from pathlib import Path
from PIL import Image,ImageDraw
p=Path('Resources/Models/FollowupFix/Review');out=p/'Sheets';out.mkdir(exist_ok=True)
for d in p.iterdir():
 if not d.is_dir() or not (d/'manifest.json').exists():continue
 for cat,files,cols in [('Body',sorted(d.glob('Body*.png'))+[d/'Wrists_Flexed.png',d/'Ankle_Flexed.png'],5),('Head',sorted(d.glob('Hair*.png'))+sorted(d.glob('Bare*.png'))+sorted(d.glob('Crowd*.png')),3)]:
  rows=(len(files)+cols-1)//cols;im=Image.new('RGB',(cols*300,rows*360),'#202020');draw=ImageDraw.Draw(im)
  for i,f in enumerate(files):
   a=Image.open(f).convert('RGB');a.thumbnail((300,336));x=i%cols*300;y=i//cols*360;im.paste(a,(x,y));draw.text((x+4,y+338),f.stem,fill='white')
  im.save(out/(d.name+'_'+cat+'.jpg'))

