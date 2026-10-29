from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]/'Resources/Models/AlternateJacketRepair'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
for level in ['Gameplay_High','Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
 poses=['Arms_Overhead','Deep_Squat','Front_Kick_L'] if not level.startswith('Crowd') else ['Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer']
 image=Image.new('RGB',(720,9*288),'white');draw=ImageDraw.Draw(image)
 for y,kind in enumerate(KINDS):
  for x,pose in enumerate(poses):
   path=ROOT/kind/(level+'_'+pose+'.png');assert path.exists(),path
   pic=Image.open(path);pic.thumbnail((240,270));image.paste(pic,(x*240,y*288+18))
   draw.text((x*240+3,y*288+3),kind+' '+pose,fill='black')
 image.save(ROOT/(level+'_Review.jpg'))
print('Six complete comparison sheets created')
