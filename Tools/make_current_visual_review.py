from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'Resources/Models/HairClothRevision'; OUT=ROOT/'Resources/Models/VisualReview_20261016';OUT.mkdir(exist_ok=True)
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def sheet(items,path,cols=3,w=300,h=338):
 result=Image.new('RGB',(cols*w,((len(items)+cols-1)//cols)*(h+24)),'white');d=ImageDraw.Draw(result)
 for i,(label,p) in enumerate(items):
  x=i%cols*w;y=i//cols*(h+24);im=Image.open(p).convert('RGB');im.thumbnail((w,h));result.paste(im,(x+(w-im.width)//2,y+24));d.text((x+5,y+5),label,fill='black')
 result.save(path)
if __name__=='__main__':
 for filename,label in [('Preview_0_Neutral.png','Preview'),('Gameplay_High_1_Neutral.png','Vneck'),('Gameplay_Far_0_Neutral.png','Far'),('Crowd_Far_0_Crowd_StandingIdle.png','Crowd')]:
  sheet([(k,S/k/filename) for k in KINDS],OUT/(label+'.jpg'))
 for kind in KINDS:
  paths=list((OUT/kind).glob('*.png'))
  if paths:sheet([(p.stem,p) for p in paths],OUT/(kind+'.jpg'),4,280,315)
