from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import subprocess,imageio_ffmpeg
p=Path(__file__).resolve().parents[1]/'Resources/Models/Animation/Samples/ClothRevision'
files=sorted((p/'Frames').glob('*.png'));assert len(files)==36
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
preview=p/'PreviewFrames';preview.mkdir(exist_ok=True);frames=[]
for file in files:
 im=Image.open(file).convert('RGB');d=ImageDraw.Draw(im);d.rectangle((0,0,640,62),fill=(18,24,32))
 d.text((20,10),'CLOTH & BELT REVISION',font=font,fill='white');d.text((20,36),'Simulated hem and tails / matte cotton material',font=small,fill=(190,205,220))
 im.save(preview/file.name);frames.append(im.resize((480,540)).quantize(colors=160))
frames[0].save(p/'Cloth_Revision.gif',save_all=True,append_images=frames[1:],duration=83,loop=0,optimize=False)
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','12','-i',str(preview/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','19','-movflags','+faststart',str(p/'Cloth_Revision.mp4')],check=True,capture_output=True)
print('Encoded revised three-second cloth preview')
