"""Denser stands from existing masks; never regenerate terrain or water."""
from pathlib import Path
import numpy as np,json
from PIL import Image
R=Path(__file__).resolve().parents[2];O=R/'Art/Export/BenmoreWoodland'
H=(np.fromfile(R/'Art/Export/BenmoreGaea/ShoreRefinement/reloaded-native-height.r16',dtype='<u2').reshape(2017,2017).astype(float)-32768)*200/128
S=np.asarray(Image.open(O/'style.png'),dtype=float)/255
def h(x,y):
 fx=np.clip((x+125000)*2016/250000,0,2015.999);fy=np.clip((y+125000)*2016/250000,0,2015.999);i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j
 q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
rng=np.random.default_rng(140925)
x,y=np.meshgrid(np.arange(-123000,123000,625),np.arange(-123000,123000,625));x=x.ravel()+rng.uniform(-240,240,x.size);y=y.ravel()+rng.uniform(-240,240,y.size)
s=S[np.clip(((y+125000)*2048/250000).astype(int),0,2047),np.clip(((x+125000)*2048/250000).astype(int),0,2047)]
z=h(x,y);slope=np.hypot(h(x+100,y)-h(x-100,y),h(x,y+100)-h(x,y-100))/200
stand=.5+.27*np.sin(x/5100+np.sin(y/2700))+.23*np.cos(y/4300+x/8100)
keep=(s[:,1]>.48)&(s[:,0]<.12)&(s[:,3]<.28)&(slope<.6)&(rng.random(x.size)<np.clip(.38+stand*.63,.20,.98))
for site in json.loads((O/'authoring.json').read_text())['sites']:
 cx,cy=site['center'];keep&=(np.hypot(x-cx,y-cy)>700)
x=x[keep];y=y[keep];z=z[keep]
trees=[[round(float(a),2),round(float(b),2),round(float(c),2),int(k),round(float(height),2),round(float(yaw),2)] for a,b,c,k,height,yaw in zip(x,y,z,rng.integers(0,3,len(x)),rng.uniform(1000,1950,len(x)),rng.uniform(0,360,len(x)))]
(O/'dense-trees.json').write_text(json.dumps(trees,separators=(',',':')))
print('Dense trees',len(trees))
