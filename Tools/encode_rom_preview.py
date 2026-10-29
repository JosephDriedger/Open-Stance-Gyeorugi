from pathlib import Path
from PIL import Image,ImageDraw
import json,imageio_ffmpeg
p=Path('Resources/Models/Animation/RangeOfMotion/Updated_Medium');paths=sorted((p/'Frames').glob('*.png'));assert len(paths)==92
poses=json.loads((p/'audit.json').read_text())['poses'];frames=[]
writer=imageio_ffmpeg.write_frames(str(p/'ROM_Audit.mp4'),(480,540),fps=8,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',output_params=['-crf','22']);writer.send(None)
for path in paths:
 f=int(path.stem);im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im);label=poses[min((f-1)//12,22)]['name'].replace('_',' ');d.rectangle((0,0,480,40),fill=(20,20,25));d.text((10,5),'ROM audit - unresolved clothing issues',fill='white');d.text((10,22),label+' / frame '+str(f),fill='white');writer.send(im.tobytes());frames.append(im)
writer.close();frames[0].save(p/'ROM_Audit.gif',save_all=True,append_images=frames[1:],duration=125,loop=0,optimize=True)
mid=[paths[i] for i in range(2,len(paths),4)];sheet=Image.new('RGB',(1000,6*304),(235,235,235));d=ImageDraw.Draw(sheet)
for i,path in enumerate(mid):
 im=Image.open(path).convert('RGB').resize((250,281));x=i%4*250;y=i//4*304;sheet.paste(im,(x,y));d.text((x+5,y+283),'Transition frame '+path.stem,fill='black')
sheet.save(p/'Transition_Review.jpg')
print('Encoded 92 frames, 11.5 seconds; transition review saved.')
