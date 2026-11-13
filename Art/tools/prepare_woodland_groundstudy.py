"""Bounded ecology study; no edits to paint, terrain heights, rest maps or water."""
from pathlib import Path
import numpy as np
from PIL import Image
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreWoodland'
a=np.array(Image.open(OUT/'style.png'));base=a.copy();n=a.shape[0]
y,x=np.mgrid[:n,:n];x=-125000+(x+.5)*250000/n;y=-125000+(y+.5)*250000/n
sites=json.loads((OUT/'authoring.json').read_text())['sites']
def smooth(lo,hi,v):
    q=np.clip((v-lo)/(hi-lo),0,1);return q*q*(3-2*q)
for site in sites:
    cx,cy=site['center'];dist=np.hypot(x-cx,y-cy)
    patch=1-smooth(2000,3200,dist)
    # Leave the central driven line open, add broken turf at its shoulders.
    edge=smooth(280,650,np.abs((x-cx)*.77+(y-cy)*.64))
    cluster=(np.sin(x/310+np.sin(y/730))+np.sin(y/450+x/840)+2)/4
    cover=.78*patch*edge*smooth(.2,.72,cluster)*(1-a[:,:,0]/255)*(1-a[:,:,3]/255)
    # Water banks retain existing dry-land cover; do not invent grass in the river.
    if site['name']=='Ford':cover*=base[:,:,1]/255
    a[:,:,1]=np.maximum(a[:,:,1],np.uint8(cover*255))
assert np.array_equal(a[:,:,[0,2,3]],base[:,:,[0,2,3]])
Image.fromarray(a).save(OUT/'style_groundstudy.png')
height=(np.fromfile(ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/reloaded-native-height.r16',dtype='<u2').reshape(2017,2017).astype(float)-32768)*200/128
def sample(px,py):
    i=int(np.clip((px+125000)/250000*n,0,n-1));j=int(np.clip((py+125000)/250000*n,0,n-1));return a[j,i]/255
def z(px,py):
    fx=np.clip((px+125000)/250000*2016,0,2015.9999);fy=np.clip((py+125000)/250000*2016,0,2015.9999)
    i,j=int(fx),int(fy);u,v=fx-i,fy-j;q,r,s,t=height[j,i],height[j,i+1],height[j+1,i],height[j+1,i+1]
    return q+(r-q)*u+(t-r)*v if u>=v else q+(t-s)*u+(s-q)*v
rng=np.random.default_rng(90411);items=[]
for site in sites:
    cx,cy=site['center']
    for _ in range(500):
        px,py=rng.uniform(-3000,3000,2)+[cx,cy];s=sample(px,py)
        if np.hypot(px-cx,py-cy)>3000 or s[1]<.38 or s[0]>.25 or s[3]>.3:continue
        if abs((px-cx)*.77+(py-cy)*.64)<600:continue
        cluster=(np.sin(px/310+np.sin(py/730))+np.sin(py/450+px/840)+2)/4
        if rng.random()>cluster*.7:continue
        # low bushes, tall tuft accents, occasional grounded woody debris
        kind=int(rng.choice(3,p=[.30,.60,.10]));h=float(rng.uniform(*[(45,110),(35,65),(8,16)][kind]))
        items.append(dict(site=site['name'],kind=kind,p=[float(px),float(py),float(z(px,py))],height_cm=h,yaw=float(rng.uniform(0,360))))
(OUT/'groundstudy-placement.json').write_text(json.dumps(items,indent=2))
report=dict(changed_grass_pixels=int(np.count_nonzero(a[:,:,1]!=base[:,:,1])),style_channels_preserved=['sand','wetness','rock'],paint_sha256=hashlib.sha256((OUT/'paint.png').read_bytes()).hexdigest(),instances=len(items),scope='Three review sites, 25-35 metre daylight material fade')
(OUT/'groundstudy-authoring.json').write_text(json.dumps(report,indent=2));print(report)
