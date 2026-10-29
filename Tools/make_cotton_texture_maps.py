from pathlib import Path
import numpy as np
from PIL import Image
out=Path(__file__).resolve().parents[1]/'Resources/Models/Animation/Samples/ClothRevision/Textures';out.mkdir(exist_ok=True)
n=512;y,x=np.mgrid[0:n,0:n];period=16
u=x/period;v=y/period;warp=np.cos(u*2*np.pi);weft=np.cos(v*2*np.pi)
over=((np.floor(u)+np.floor(v)).astype(int)%2)==0
height=np.where(over,.6*warp+.2*weft,.2*warp+.6*weft)
variation=.007*height+.002*np.sin(x*2*np.pi/7)*np.sin(y*2*np.pi/9)
for name,base in [('Cotton_BaseColor',(.87,.875,.88)),('Belt_BaseColor',(.075,.078,.082))]:
 data=np.clip(np.array(base)[None,None,:]+variation[:,:,None],0,1);Image.fromarray((data*255).astype('uint8')).save(out/(name+'.png'))
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.06;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.06
norm=np.stack([-dx,-dy,np.ones_like(dx)],-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
Image.fromarray(((norm*.5+.5)*255).astype('uint8')).save(out/'Cotton_Normal.png')
Image.fromarray((np.clip(.82+height*.018,0,1)*255).astype('uint8')).save(out/'Cotton_Roughness.png')
print(out)
