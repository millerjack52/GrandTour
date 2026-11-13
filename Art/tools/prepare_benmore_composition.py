"""Place connected vegetation and schist exposures against the real terrain.

All heights remain the canonical gameplay surface. These are art placements,
not surveyed land cover. Road clearance uses complete line segments.
"""
from pathlib import Path
import numpy as np
from PIL import Image
import json, math, hashlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreComposition'; OUT.mkdir(exist_ok=True)
HFILE=ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32'
GRID=np.fromfile(HFILE,dtype='<f4').reshape(2017,2017)
GEO=np.asarray(Image.open(ROOT/'Art/Export/BenmoreVistaStudy/T_Benmore_GeographicZones.png'))/255.
ROUTES=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
aa=[];bb=[];width=[]
for route in ROUTES:
    p=np.array([[v['x_m'],v['y_m']] for v in route['points']])
    aa.extend(p[:-1]);bb.extend(p[1:]);width.extend([route['width_m']/2]*(len(p)-1))
A=np.array(aa);B=np.array(bb);AB=B-A;AB2=(AB*AB).sum(1);WIDTH=np.array(width)

def height(x,y):
    fx=np.clip((np.asarray(x)+1250)/2500*2016,0,2015.999999)
    fy=np.clip((np.asarray(y)+1250)/2500*2016,0,2015.999999)
    i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j
    q,r,s,t=GRID[j,i],GRID[j,i+1],GRID[j+1,i],GRID[j+1,i+1]
    return np.where(a>=b,q+(r-q)*a+(t-r)*b,q+(t-s)*a+(s-q)*b)

def gradient(x,y,d=5.):
    return np.array([(height(x+d,y)-height(x-d,y))/(2*d),(height(x,y+d)-height(x,y-d))/(2*d)])

def clearance(x,y):
    p=np.array([x,y]);t=np.clip(((p-A)*AB).sum(1)/AB2,0,1)
    return float((np.linalg.norm(A+AB*t[:,None]-p,axis=1)-WIDTH).min())

CAM=np.array([750.,500.]);CAMZ=float(height(*CAM))+1.9
FORWARD=np.array([math.cos(math.radians(215)),math.sin(math.radians(215))])
def visible(x,y,lift=1.):
    p=np.array([x,y]);v=p-CAM;dist=np.linalg.norm(v)
    if dist<160 or dist>1900 or np.dot(v/dist,FORWARD)<math.cos(math.radians(39)):return False
    t=np.linspace(.04,.96,45);xy=CAM[:,None]+v[:,None]*t
    ray=CAMZ+(float(height(x,y))+lift-CAMZ)*t
    return bool(np.all(height(xy[0],xy[1])<ray+.25))

def geo(x,y):return GEO[int((4278-y)/5),int((x+11463)/5)]

def run():
    rng=np.random.default_rng(7102026)
    candidates=[]
    for y in np.arange(-950,360,24):
        for x in np.arange(-1060,610,24):
            x=float(x+rng.uniform(-7,7));y=float(y+rng.uniform(-7,7))
            z=float(height(x,y));g=gradient(x,y);s=np.linalg.norm(g)
            if z<9 or not .055<s<.58 or clearance(x,y)<24 or not visible(x,y):continue
            ring=np.array([height(x+dx,y+dy) for dx,dy in [(35,0),(-35,0),(0,35),(0,-35)]])
            hollow=float(ring.mean()-z);a=geo(x,y)
            candidates.append((x,y,hollow,a[0],a[1],s))
    # A few continuous gullies, not evenly spread dots. Width and density
    # change along each stem, with gaps and detached satellite clumps.
    stems=[]
    for x,y,hollow,drain,rock,s in sorted(candidates,key=lambda q:q[2]+q[3]*8,reverse=True):
        if hollow<.45 or any(np.linalg.norm(np.array([x,y])-np.array(p['points'][0]))<205 for p in stems):continue
        points=[];p=np.array([x,y])
        for k in range(int(rng.integers(20,37))):
            if not(-1150<p[0]<1150 and -1150<p[1]<1150) or height(*p)<6:break
            points.append(p.tolist());g=gradient(*p,9);n=np.linalg.norm(g)
            if n<.025:break
            p=p-g/n*8
        if len(points)>12:stems.append({'points':points,'width_m':float(rng.uniform(20,36))})
        if len(stems)==9:break
    shrubs=[];tussocks=[];used=set()
    for ci,stem in enumerate(stems):
        points=np.array(stem['points'])
        for _ in range(1200):
            idx=int(rng.integers(0,len(points)-1));p=points[idx];d=points[idx+1]-p;d/=np.linalg.norm(d)
            side=np.array([-d[1],d[0]]);f=idx/(len(points)-1)
            w=stem['width_m']*(.52+.35*math.sin(f*math.pi)+.20*math.sin(f*17+ci))
            xy=p+d*rng.uniform(-6,6)+side*rng.normal(0,w*.58)
            x,y=map(float,xy);cell=(round(x/2.6),round(y/2.6))
            if cell in used or not(-1180<x<1180 and -1180<y<1180):continue
            if height(x,y)<5 or clearance(x,y)<10 or np.linalg.norm(gradient(x,y))>.68:continue
            if rng.random()<.18+.13*math.sin(f*24+ci):continue
            used.add(cell)
            shrubs.append(dict(x=x,y=y,height_m=float(rng.uniform(1.2,2.5)),yaw=float(rng.uniform(-180,180)),kind=int(rng.random()<.8),cluster=ci))
        for _ in range(2100):
            idx=int(rng.integers(0,len(points)));xy=points[idx]+rng.normal(0,stem['width_m']*.9,2)
            x,y=map(float,xy);cell=(round(x/1.15),round(y/1.15))
            if cell in used or not(-1180<x<1180 and -1180<y<1180):continue
            if height(x,y)<5 or clearance(x,y)<8 or np.linalg.norm(gradient(x,y))>.64:continue
            used.add(cell);tussocks.append(dict(x=x,y=y,height_m=float(rng.uniform(.62,1.02)),yaw=float(rng.uniform(-180,180)),kind=int(rng.random()<.3),cluster=ci))
    # Contour-following broken ledges on visible convex slopes. Each formation
    # has a common strike; not a pile of independently rotated giant boulders.
    outcrops=[]
    for x,y,hollow,drain,rock,s in sorted(candidates,key=lambda q:q[4]*4-q[2]*.8+q[5],reverse=True):
        if not .15<s<.60 or hollow>.1 or clearance(x,y)<48:continue
        if any(math.hypot(x-r['x'],y-r['y'])<120 for r in outcrops):continue
        g=gradient(x,y,12);yaw=math.degrees(math.atan2(g[1],g[0]))+90+rng.uniform(-12,12)
        outcrops.append(dict(x=x,y=y,z=float(height(x,y)),yaw=float(yaw),length_m=float(rng.uniform(27,54)),width_m=float(rng.uniform(8,14)),seed=ci+int(rng.integers(0,1000000))))
        if len(outcrops)==18:break
    assert len(stems)>=5 and len(outcrops)>=12,(len(stems),len(outcrops))
    assert len(shrubs)<8500 and len(tussocks)<20000
    data=dict(seed=7102026,stems=stems,shrubs=shrubs,tussocks=tussocks,outcrops=outcrops,
              height_sha256=hashlib.sha256(HFILE.read_bytes()).hexdigest(),height_changed=False,
              min_shrub_road_edge_clearance_m=min(clearance(r['x'],r['y']) for r in shrubs),
              min_tussock_road_edge_clearance_m=min(clearance(r['x'],r['y']) for r in tussocks),
              outcrops_visible_from_overlook=sum(visible(r['x'],r['y'],2) for r in outcrops))
    (OUT/'placements.json').write_text(json.dumps(data,indent=2))
    # Carry the planted areas into the terrain material as the individual
    # silhouettes get small. This is numeric coverage, not a painted image.
    zones=GEO.copy();density=np.zeros(GEO.shape[:2],np.float32)
    for r in shrubs:
        ix=int((r['x']+11463)/5);iy=int((4278-r['y'])/5)
        density[iy,ix]+=1
    for axis in [0,1]:
        pad=[(0,0),(0,0)];pad[axis]=(2,2)
        p=np.pad(density,pad,mode='edge');s=np.cumsum(p,axis=axis,dtype=np.float64)
        pad=[(0,0),(0,0)];pad[axis]=(1,0);s=np.pad(s,pad)
        density=((s[5:]-s[:-5])/5 if axis==0 else (s[:,5:]-s[:,:-5])/5).astype(np.float32)
    zones[...,0]=np.maximum(zones[...,0],np.clip(density/.90,0,.76))
    Image.fromarray(np.uint8(np.round(zones*255))).save(OUT/'T_Benmore_CompositionZones.png')
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in data.items()},indent=2))
    print('outcrops',[(round(r['x']),round(r['y'])) for r in outcrops])
    print('stems',[(tuple(round(v) for v in r['points'][0]),len(r['points'])) for r in stems])

if __name__=='__main__':run()
