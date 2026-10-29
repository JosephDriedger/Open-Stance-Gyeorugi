from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]/'Resources/Models';OUT=ROOT/'TailoredDoboks'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
comparison=Image.new('RGB',(960,580),'white');draw=ImageDraw.Draw(comparison)
for x,(label,p) in enumerate([('Previous fit',ROOT/'GarmentRollout/Medium/Preview_Neutral.png'),('Tailored fit - same body',OUT/'Medium/Preview_0_Neutral.png')]):
 comparison.paste(Image.open(p),(x*480,40));draw.text((x*480+12,10),label,font=font,fill='black')
comparison.save(OUT/'Fit_Before_After.jpg')
for level in ['Gameplay_High','Preview','Animation','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
 poses=['Neutral','Arms_Overhead','Deep_Squat','Front_Kick_L'] if not level.startswith('Crowd') else ['Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer']
 for style in [0,1]:
  image=Image.new('RGB',(960,9*288),'white');d=ImageDraw.Draw(image)
  for y,kind in enumerate(KINDS):
   for x,pose in enumerate(poses):
    p=OUT/kind/(level+'_'+str(style)+'_'+pose+'.png');assert p.exists(),p
    pic=Image.open(p);pic.thumbnail((240,270));image.paste(pic,(x*240,y*288+18));d.text((x*240+3,y*288+3),kind+' '+pose,fill='black')
  image.save(OUT/(level+'_'+str(style)+'_Review.jpg'))
print('Before/after and 14 complete motion review sheets created')
