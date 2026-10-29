from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]/'Resources/Models/OpeningRepair'
kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
poses=['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']
for style in [0,1]:
 out=Image.new('RGB',(960,9*285),'white');draw=ImageDraw.Draw(out)
 for row,kind in enumerate(kinds):
  for col,pose in enumerate(poses):
   im=Image.open(root/kind/f'Gameplay_High_{style}_{pose}.png').convert('RGB');im.thumbnail((240,265));out.paste(im,(col*240,row*285+20));draw.text((col*240+4,row*285+3),kind+' '+pose,fill='black')
 out.save(root/f'Motion_Review_{style}.jpg',quality=90)
out=Image.new('RGB',(1280,6*340),'white');draw=ImageDraw.Draw(out)
for row,(kind,style) in enumerate((k,s) for k in ['Medium','Stocky','Female_Strong'] for s in [0,1]):
 for col,pose in enumerate(poses):
  im=Image.open(root/kind/f'Close_{style}_{pose}.png').convert('RGB');im.thumbnail((320,320));out.paste(im,(col*320,row*340+20));draw.text((col*320+3,row*340+3),f'{kind} style {style} {pose}',fill='black')
out.save(root/'Closeup_Review.jpg',quality=92)
out=Image.new('RGB',(1200,600),'white')
for col,p in enumerate([root/'Medium/Close_0_Wrists_Flexed.png',root/'Ankles.png']):
 im=Image.open(p).convert('RGB');im.thumbnail((600,600));out.paste(im,(col*600,0))
out.save(root/'Repaired_Openings.jpg',quality=92)
print('Review sheets created')
