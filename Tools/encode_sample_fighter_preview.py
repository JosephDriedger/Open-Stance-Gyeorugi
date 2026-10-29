"""Encode actual Blender frames into a labeled MP4 and chat GIF."""
from pathlib import Path
import subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Resources/Models/Animation/Samples'
files=sorted((OUT/'Frames').glob('*.png'));assert len(files)==108,len(files)
labels=['GUARD IDLE','STRAIGHT PUNCHES','FRONT KICK']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
dest=OUT/'PreviewFrames';dest.mkdir(exist_ok=True);gif=[]
for i,path in enumerate(files):
 im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im)
 d.rectangle((0,0,640,67),fill=(18,24,32));d.text((22,10),labels[i//36],font=font,fill='white')
 d.text((22,40),'Authored rig test | Medium sparring model',font=small,fill=(190,205,220))
 im.save(dest/path.name)
 gif.append(im.resize((480,540)).quantize(colors=128))
gif[0].save(OUT/'Fighter_Demo.gif',save_all=True,append_images=gif[1:],duration=83,loop=0,optimize=False)
gif[72].save(OUT/'Front_Kick_Preview.gif',save_all=True,append_images=gif[73:],duration=83,loop=0,optimize=False)
sidefiles=sorted((OUT/'SideFrames').glob('*.png'))
if len(sidefiles)==36:
 sideframes=[]
 for p in sidefiles:
  im=Image.open(p).convert('RGB');d=ImageDraw.Draw(im);d.rectangle((0,0,640,67),fill=(18,24,32))
  d.text((22,10),'FRONT KICK - SIDE VIEW',font=font,fill='white')
  d.text((22,40),'Chamber / extend / retract / recover',font=small,fill=(190,205,220))
  sideframes.append(im.resize((480,540)).quantize(colors=128))
 sideframes[0].save(OUT/'Front_Kick_Side.gif',save_all=True,append_images=sideframes[1:],duration=83,loop=0,optimize=False)
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','12','-i',str(dest/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-movflags','+faststart',str(OUT/'Fighter_Demo.mp4')],check=True,capture_output=True)
print('Encoded 108 frames, 9-second MP4 and GIF')
