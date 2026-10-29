from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path('Resources/Models/HairExportFinish');kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong'];font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
for level in ['Gameplay_High','Preview','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']:
 sheet=Image.new('RGB',(1440,1050),'#ddd');d=ImageDraw.Draw(sheet)
 for i,k in enumerate(kinds):
  for j in [0,1]:
   pose='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral';f=p/k/(level+'_'+str(j)+'_'+pose+'.png');x=(i%3)*480+j*240;y=(i//3)*350
   sheet.paste(Image.open(f).convert('RGB').resize((240,320)),(x,y+30));d.text((x+5,y+4),k+' '+str(j),font=font,fill='black')
 sheet.save(p/(level+'_Catalog_Review.jpg'))
sheet=Image.new('RGB',(1800,990),'#ddd');d=ImageDraw.Draw(sheet)
for i,k in enumerate(kinds):
 for j,n in enumerate(['Gameplay_High','Crowd_Far']):
  f=p/k/(n+'_HairReview.png');x=(i%3)*600+j*300;y=(i//3)*330;sheet.paste(Image.open(f).convert('RGB').resize((300,300)),(x,y+30));d.text((x+5,y+4),k+' '+n,font=font,fill='black')
sheet.save(p/'Native_Hair_Review.jpg')
