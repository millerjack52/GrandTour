"""Inspect actual evolving Unreal captures against matching settled controls."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

P=Path('C:/GrandTour/Art/Export/LidarStudy/FloraParity/AssetMatch')
R=P/'unreal-motion'
def raw(name):return np.fromfile(R/(name+'.f32'),np.float32).reshape(512,512,4)[...,:3]
def display(x):
 x=np.maximum(x,0)
 return np.uint8(np.clip(np.where(x<=.0031308,12.92*x,1.055*x**(1/2.4)-.055),0,1)*255)
def blur(x):return sum(np.roll(np.roll(x,i,0),j,1) for i in range(-2,3) for j in range(-2,3))/25
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
report={'runtime_fps_verified':False,'scope':'48 evolving camera/light frames, then two settled controls; no wind/forest-scale claim','controls':{}}
board=Image.new('RGB',(1060,1120),'#192326');d=ImageDraw.Draw(board)
d.text((20,12),'UNREAL / CAMERA AND LIGHT MOVEMENT',font=font,fill='white')
d.text((20,45),'During movement',font=font,fill='white');d.text((550,45),'Same camera/light, held still',font=font,fill='white')
for row,index in enumerate([6,30]):
 a=raw('motion_%03d'%index);b=raw('settled_%03d'%index)
 assert np.isfinite(a).all() and np.isfinite(b).all()
 mask=((a[:,:,1]>a[:,:,2]*1.25)|(b[:,:,1]>b[:,:,2]*1.25))&((a+b).max(2)>.003)
 aa=blur(a);bb=blur(b)
 report['controls'][str(index)]={'relative_rgb_l1_5px':float(abs(aa-bb)[mask].sum()/max(bb[mask].sum(),1e-8)),'mean_display_difference_0_to_1':float(abs(display(aa).astype(float)-display(bb).astype(float))[mask].mean()/255)}
 for col,v in enumerate([a,b]):board.paste(Image.fromarray(display(v)),(18+col*530,80+row*512))
board.save(P/'motion-review.jpg',quality=95)
frames=[]
for index in range(48):
 a=raw('motion_%03d'%index);assert np.isfinite(a).all()
 im=Image.new('RGB',(512,555),'#192326');im.paste(Image.fromarray(display(a)),(0,0));dd=ImageDraw.Draw(im);dd.text((12,520),'Unreal captures / visual test, not FPS',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17),fill='white');frames.append(im)
frames[0].save(P/'motion-preview.webp',save_all=True,append_images=frames[1:],duration=83,loop=0,quality=88,method=4)
(P/'motion-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
