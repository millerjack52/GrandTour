"""Deterministic dry-bank cover and mineral patches above the baked waterline.

No bed or flow data is changed. RGBA stores vegetation, dampness, mineral
variation and river-local influence; these are numeric material weights.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from PIL import Image
from prepare_benmore_composition import clearance

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'Art/Export/BenmoreRivers'

def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1); return t*t*(3-2*t)

def run():
    d=np.load(OUT/'river_bake.npz'); x=d['x']; y=d['y']; xx,yy=np.meshgrid(x,y)
    shore=d['shore']; rng=np.random.default_rng(8102701)
    def field(scale):
        f=gaussian_filter(rng.normal(size=xx.shape),scale)
        return np.clip(.5+f/max(f.std(),1e-9)*.18,0,1)
    broad=field(22); small=field(5); mineral=field(11)
    gy,gx=np.gradient(d['bed']); slope=np.hypot(gx,gy)
    # Broken fingers reach toward the water, with bare convex/mineral gaps.
    edge=.9+2.6*smooth(.30,.68,broad*.75+small*.25)
    cover=smooth(edge,edge+2.5,shore)
    cover*=.52+.48*smooth(.22,.68,small*.45+broad*.55)
    cover*=1-smooth(.30,.76,slope)*.43
    cover=np.maximum(cover,smooth(10,17,shore)*.90)
    influence=(1-smooth(11,22,shore))*(d['bed']>.72)
    damp=(1-smooth(.4,3.0,shore))*(.55+.45*small)
    rgba=np.stack([cover,damp,mineral,influence],axis=-1)
    Image.fromarray(np.uint8(np.round(np.clip(rgba,0,1)*255))).save(OUT/'T_Benmore_RiverBankArt.png')
    def sample(a,px,py):
        return float(map_coordinates(a,[[py-y[0]],[px-x[0]]],order=1,mode='constant',cval=0)[0])
    candidates=np.argwhere((shore>1.5)&(shore<17)&(xx>-1225)&(xx<-335)&(d['bed']>1.0)&(slope<.65))
    rng.shuffle(candidates); rows={'tussocks':[],'shrubs':[],'rocks':[],'trees':[]}; used=set()
    def row(px,py,size,kind):
        return dict(x=float(px),y=float(py),size_m=float(size),kind=int(kind),yaw=float(rng.uniform(0,360)))
    for j,i in candidates:
        px=x[i]+rng.uniform(-.38,.38);py=y[j]+rng.uniform(-.38,.38)
        if cover[j,i]<.22 or rng.random()>cover[j,i]*.80 or clearance(px,py)<35:continue
        key=(round(px/1.15),round(py/1.15))
        if key in used:continue
        used.add(key);rows['tussocks'].append(row(px,py,rng.uniform(.52,1.04),rng.random()<.18))
        if len(rows['tussocks'])>=2300:break
    used=set()
    for j,i in candidates:
        if not(2.8<shore[j,i]<13) or cover[j,i]<.44 or broad[j,i]<.50 or slope[j,i]>.42:continue
        px=x[i]+rng.uniform(-.35,.35);py=y[j]+rng.uniform(-.35,.35);key=(round(px/3.3),round(py/3.3))
        if key in used or rng.random()>.23 or clearance(px,py)<35:continue
        used.add(key);rows['shrubs'].append(row(px,py,rng.uniform(.55,1.25),rng.random()<.7))
        if len(rows['shrubs'])>=150:break
    # Lower, elongated exposures group with small fragments. Their complete
    # conservative bounding circles clear the active wet cells.
    used=set()
    for j,i in candidates:
        if not(2.8<shore[j,i]<10.5) or mineral[j,i]<.57 or cover[j,i]>.48:continue
        px=x[i]+rng.uniform(-.3,.3);py=y[j]+rng.uniform(-.3,.3);key=(round(px/8),round(py/8))
        if key in used or rng.random()>.16:continue
        size=float(rng.uniform(1.05,2.9));radius=size*.72
        if shore[j,i]<radius+1.4 or clearance(px,py)<40:continue
        used.add(key);r=row(px,py,size,rng.integers(1,4));r['height_ratio']=float(rng.uniform(.72,1.0));rows['rocks'].append(r)
        if len(rows['rocks'])>=45:break
    # A few sheltered willow groups punctuate the downstream reach; leave
    # most of the channel open rather than creating a continuous tree avenue.
    for target_x,side in [(-1165,1),(-1115,1),(-996,-1),(-940,-1),(-810,1)]:
        path=d['path'];k=np.argmin(abs(path[:,0]-target_x));p=path[k,:2]
        best=[]
        for j,i in candidates:
            if abs(x[i]-p[0])>25 or not(8<shore[j,i]<16) or slope[j,i]>.28:continue
            if (y[j]-p[1])*side<0:continue
            best.append((abs(x[i]-p[0])+abs(shore[j,i]-11),j,i))
        for _,j,i in sorted(best)[:1]:
            for dx,dy in [(0,0),(6,side*2.5)]:
                px=x[i]+dx;py=y[j]+dy
                if sample(shore,px,py)<7 or clearance(px,py)<40:continue
                rows['trees'].append(row(px,py,rng.uniform(4.4,6.2),0))
    assert len(rows['tussocks'])>1800 and len(rows['rocks'])>30
    allrows=[r for group in rows.values() for r in group]
    report=dict(ok=True,seed=8102701,counts={k:len(v) for k,v in rows.items()},placements=rows,
        bake_sha256=hashlib.sha256((OUT/'river_bake.npz').read_bytes()).hexdigest(),
        bed_changed=False,flow_changed=False,min_center_road_clearance_m=min(clearance(r['x'],r['y']) for r in allrows),
        min_rock_wet_clearance_m=min(sample(shore,r['x'],r['y'])-r['size_m']*.72 for r in rows['rocks']))
    assert report['min_rock_wet_clearance_m']>1
    (OUT/'bank-art-placements.json').write_text(json.dumps(report,indent=2))
    print({k:v for k,v in report.items() if k!='placements'})

if __name__=='__main__':run()
