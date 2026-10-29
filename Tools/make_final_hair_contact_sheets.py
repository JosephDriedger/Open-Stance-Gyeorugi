from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]/'Resources/Models/FinalRefinement/HairRepeat/Review'
for kind in ['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']:
 canvas=Image.new('RGB',(1200,490),'#25292d');draw=ImageDraw.Draw(canvas)
 for style in range(6):
  for helmet in range(2):
   im=Image.open(root/f'{kind}_{style}_{helmet}.png').convert('RGB');im.thumbnail((200,225));x=style*200;y=helmet*245
   canvas.paste(im,(x,y));draw.text((x+5,y+226),f'{kind} / {style} / '+('helmet' if helmet else 'uncovered'),fill='white')
 canvas.save(root/(kind+'_Sheet.jpg'),quality=92)
