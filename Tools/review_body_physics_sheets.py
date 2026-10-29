from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]/'Resources/Models/FinalRefinement/BodyPhysics'
for folder in ROOT.iterdir():
 if not folder.is_dir() or not (folder/'validation.json').exists():continue
 canvas=Image.new('RGB',(1280,616),'#262a2e');draw=ImageDraw.Draw(canvas)
 for row,view in enumerate(['Front','Side']):
  for col,frame in enumerate([1,26,35,72,144]):
   image=Image.open(folder/f'{view}_{frame}.png').convert('RGB');image.thumbnail((256,288))
   x=col*256;y=row*308;canvas.paste(image,(x,y));draw.text((x+5,y+290),f'{folder.name} / {view} / {frame}',fill='white')
 canvas.save(folder/'Review.jpg',quality=94)
 print(folder.name)
