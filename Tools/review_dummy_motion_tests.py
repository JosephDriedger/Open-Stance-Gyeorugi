from pathlib import Path
from PIL import Image,ImageDraw
import json
root=Path(__file__).resolve().parents[1]/'Resources/Models/Animation/DummyMotionTests'
report=json.loads((root/'delivery_validation.json').read_text());assert report['presets']==9
poses=['Arms_Overhead','Side_Kick_L','Deep_Squat'];width,height=192,216
sheet=Image.new('RGB',(3*(width*3+12),3*(height+42)),(28,31,37));draw=ImageDraw.Draw(sheet)
for i,row in enumerate(report['rows']):
    x=(i%3)*(width*3+12);y=(i//3)*(height+42)
    draw.text((x+6,y+5),row['preset'],fill='white')
    for j,pose in enumerate(poses):
        with Image.open(root/row['preset']/(pose+'.png')) as source:
            sheet.paste(source.convert('RGB').resize((width,height),Image.Resampling.LANCZOS),(x+j*width,y+24))
sheet.save(root/'Review_Overview.jpg',quality=94)
print(root/'Review_Overview.jpg')
