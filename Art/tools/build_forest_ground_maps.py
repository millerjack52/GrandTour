"""Visual-only woodland eligibility and shared periodic moss footprints."""
from pathlib import Path
import json,struct,math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path('C:/GrandTour');PLACE=ROOT/'Art/Export/LidarStudy/Place';OUT=PLACE/'ForestGround';OUT.mkdir(parents=True,exist_ok=True)
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
style=np.asarray(Image.open(PLACE/'style.png'),dtype=np.float32)/255
clay=np.asarray(Image.open(PLACE/'clay.png'),dtype=np.float32)/255
forest=np.asarray(Image.open(PLACE.parent/'Reference/forest-mask.png').convert('L'),dtype=np.float32)/255
N=style.shape[0];assert forest.shape==(N,N)
cover=smooth(.25,.65,forest)*(1-smooth(.20,.50,style[:,:,1]))*(1-smooth(.20,.75,style[:,:,3]))*(1-smooth(.1,.5,style[:,:,0]))*(1-smooth(.05,.35,clay[:,:,0]))
roads=Image.new('L',(N,N));draw=ImageDraw.Draw(roads)
for road in json.loads((PLACE/'roads.json').read_text()):
 points=[((p[0]+185000)/370000*N,(p[1]+185000)/370000*N) for p in road['points']]
 draw.line(points,fill=255,width=math.ceil(1000/370000*N),joint='curve')
roadmask=np.asarray(roads.filter(ImageFilter.GaussianBlur(.65)),dtype=np.float32)/255
cover*=1-roadmask
axis=(np.arange(N)+.5)/N*370000-185000;x,y=np.meshgrid(axis,axis)
a=.6*(x+45800)-.8*(y+31600);b=-.8*(x+45800)-.6*(y+31600)
cover*=smooth(0,180,np.maximum(np.abs(a)-1100,np.abs(b)-780))
mask=np.uint8(np.clip(cover,0,1)*255)
Image.fromarray(mask).save(OUT/'T_FG_Coverage.png');(OUT/'coverage.bin').write_bytes(struct.pack('<I',N)+mask.tobytes())
def hashed(x,y,seed):
 h=((x&15)*1597334677)^((y&15)*3812015801)^seed
 h&=0xffffffff;h=((h^(h>>16))*2246822519)&0xffffffff;h=((h^(h>>13))*3266489917)&0xffffffff
 return (h^(h>>16))&0xffffffff
def unit(x,y,seed):return (hashed(x,y,seed)&65535)/65535
W=1024;span=2560.;ax=(np.arange(W)+.5)/W*span;xx,yy=np.meshgrid(ax,ax)
moss=np.zeros((W,W),np.float32);height=np.zeros_like(moss);pattern=[]
for j in range(16):
 for i in range(16):
  cx=(i+.22+.56*unit(i,j,11))*160;cy=(j+.22+.56*unit(i,j,17))*160
  rx=30+32*unit(i,j,23);ry=rx*(.45+.85*unit(i,j,29));angle=math.tau*unit(i,j,31);variant=hashed(i,j,37)%3;phase=variant*1.7
  dx=(xx-cx+span/2)%span-span/2;dy=(yy-cy+span/2)%span-span/2
  px=(dx*math.cos(angle)+dy*math.sin(angle))/rx;py=(-dx*math.sin(angle)+dy*math.cos(angle))/ry
  t=np.arctan2(py,px);shape=1+.26*np.sin(3*t+phase)+.16*np.cos(5*t-phase)
  radius=np.sqrt(px*px+py*py)/shape
  cov=1-smooth(.82,1.12,radius);moss=np.maximum(moss,cov);height=np.maximum(height,np.maximum(0,1-radius*radius)**.62)
  pattern.append(dict(cell=[i,j],centre=[cx,cy],radius=[rx,ry],yaw=math.degrees(angle),variant=variant))
Image.fromarray(np.uint8(np.stack([moss,height,moss,np.ones_like(moss)],-1)*255)).save(OUT/'T_FG_Moss.png')
(OUT/'pattern.json').write_text(json.dumps(pattern))
report=dict(eligible_km2=float(np.mean(mask/255)*(3700**2)/1e6),forest_km2=float(np.mean(forest>.5)*3700**2/1e6),coverage_resolution=N,pattern_span_cm=span,pattern_cell_cm=160,moss_fraction=float(np.mean(moss>.5)),physics_maps_unchanged=True,roads_excluded_m=10,approved_section_excluded=True)
(OUT/'maps.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
