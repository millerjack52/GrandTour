"""Author regional masks over the saved Gaea heights. No terrain or hydraulic edits."""
from pathlib import Path
import json,math,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreNative';OUT.mkdir(parents=True,exist_ok=True)
HEIGHT=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/reloaded-native-height.r16'
H=(np.fromfile(HEIGHT,dtype='<u2').reshape(2017,2017).astype(float)-32768)*200/128
def height(x,y):
 fx=np.clip((np.asarray(x)+125000)/250000*2016,0,2015.999999);fy=np.clip((np.asarray(y)+125000)/250000*2016,0,2015.999999)
 ix=fx.astype(int);iy=fy.astype(int);a=fx-ix;b=fy-iy
 q=H[iy,ix];r=H[iy,ix+1];v=H[iy+1,ix];w=H[iy+1,ix+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def distance(x,y,line):
 d=np.full_like(x,1e9)
 for a,b in zip(line,line[1:]):
  a=np.array(a);v=np.array(b)-a;t=np.clip(((x-a[0])*v[0]+(y-a[1])*v[1])/max(np.dot(v,v),1),0,1)
  d=np.minimum(d,np.hypot(x-a[0]-t*v[0],y-a[1]-t*v[1]))
 return d
plan=json.loads((ROOT/'Art/Export/BenmoreB2/plan.json').read_text())
sites=[dict(name='Road',center=[-76250,-43375],native=True),dict(name='Ford',center=[-68000,22000],native=False),dict(name='Bog',center=[-59550,-59475],native=True)]
for s in sites:
 cx,cy=s['center'];size=4800;ox,oy=cx-size/2,cy-size/2;n=512
 yy,xx=np.mgrid[0:n,0:n];x=ox+(xx+.5)*size/n;y=oy+(yy+.5)*size/n
 edge=np.minimum.reduce([x-ox,y-oy,ox+size-x,oy+size-y]);rim=smooth(150,500,edge)
 noise=np.sin(x/179+np.sin(y/280))*np.cos(y/233)+.35*np.sin((x-y)/91)
 if s['name']=='Road':
  d=distance(x,y,plan['zones'][0]['line_cm']);pocket=.6+.4*np.sin((x+y)/430)
  cover=(1-smooth(180,340+noise*35,d))*rim
  depth=cover*(10+23*pocket);sand=np.zeros_like(x);grass=np.zeros_like(x);soft=.65+.23*pocket
  rest=(np.sin(x/135)*np.cos(y/190)-.7)*2*cover
 elif s['name']=='Ford':
  # Cross-channel coordinate follows the saved ford's measured current direction.
  along=(x-cx)*-.8418733+(y-cy)*-.5396752
  across=(x-cx)*-.5396752+(y-cy)*.8418733
  cover=(1-smooth(1450,1950+noise*75,np.abs(along)))*rim
  sand=1-smooth(520,950,np.abs(across));grass=1-sand
  # Keep the actual crossing's firm shingle, yielding sand lies on its shoulders.
  firm=(1-smooth(220,420,np.abs(along)))*(1-smooth(260,430,np.abs(across)))
  cover*=1-firm
  depth=cover*(sand*10+grass*5);soft=np.full_like(x,.52);rest=np.zeros_like(x)
 else:
  q=np.hypot((x-cx)/1580,(y-cy)/760)
  cover=(1-smooth(.68,1.12+noise*.055,q))*rim
  depth=cover*(24+82*(1-smooth(.12,.78,q)));sand=np.zeros_like(x);grass=np.zeros_like(x);soft=np.full_like(x,.95)
  rest=(-3+np.sin(x/190)*np.cos(y/215)*3)*cover
 # Explicit coverage, independent of softness or finite soil depth.
 cover[[0,-1],:]=0;cover[:,[0,-1]]=0;depth*=cover>0
 paint=np.stack([depth/124,np.ones_like(x),np.zeros_like(x),soft],-1)
 style=np.stack([sand,grass,np.zeros_like(x),np.ones_like(x)],-1)
 def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(s['name']+'_'+name+'.png'))
 save('paint',paint);save('style',style);save('cover',np.stack([cover]*3+[np.ones_like(x)],-1))
 # Rest relief uses the existing 16-bit -50..15cm encoding; not the Gaea elevation.
 packed=np.uint16(np.clip((rest+50)/65,0,1)*65535+.5)
 rgba=np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8');Image.fromarray(rgba).save(OUT/(s['name']+'_rest.png'))
 z=height(x,y);base=float(z.min())-100;packed=np.uint16(np.clip((z-base)/8192,0,1)*65535+.5)
 rgba=np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8');Image.fromarray(rgba).save(OUT/(s['name']+'_macro.png'))
 s.update(origin=[ox,oy],size=size,center_height_cm=float(height(float(cx),float(cy))),depth_max_cm=float(depth.max()),area_m2=float(np.sum(cover>.5)*(size/n/100)**2),macro_min_cm=base)
(OUT/'authoring.json').write_text(json.dumps({'sites':sites,'terrain_sha256':hashlib.sha256(HEIGHT.read_bytes()).hexdigest(),'terrain_edited':False},indent=2))
print(json.dumps(sites,indent=2))
