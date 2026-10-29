from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path('Resources/Models/HairExportFinish');kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong'];font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
sheet=Image.new('RGB',(1800,990),'#ddd');d=ImageDraw.Draw(sheet)
for i,k in enumerate(kinds):
 for j,n in enumerate(['Gameplay_High_Dobok','Crowd_Near']):
  f=p/k/(n+'_Reimport.png');x=(i%3)*600+j*300;y=(i//3)*330
  sheet.paste(Image.open(f).convert('RGB').resize((300,300)),(x,y+30));d.text((x+5,y+4),k+(' Fighter' if j==0 else ' Crowd'),font=font,fill='black')
sheet.save(p/'Exports_Review.jpg')
