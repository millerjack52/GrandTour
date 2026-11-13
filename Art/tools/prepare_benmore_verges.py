"""Deterministic broken gravel windrows and approved tussock verge patches."""
from pathlib import Path
import json,math,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreVerges';OUT.mkdir(parents=True,exist_ok=True)
roads=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
h=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(2017,2017);step=2500/2016
def height(x,y):
    f=(x+1250)/step;g=(y+1250)/step;i=int(f);j=int(g);a=f-i;b=g-j
    return float((h[j,i]*(1-a)+h[j,i+1]*a)*(1-b)+(h[j+1,i]*(1-a)+h[j+1,i+1]*a)*b)
# Dense centreline samples make junction exclusions accurate to 25 cm.
centres=[];widths=[]
for r in roads:
    for p,q in zip(r['points'][:-1],r['points'][1:]):
        a=np.array([p['x_m'],p['y_m']]);b=np.array([q['x_m'],q['y_m']])
        for t in np.arange(0,1,.25/max(np.linalg.norm(b-a),.001)):
            centres.append(a+(b-a)*t);widths.append(r['width_m']/2)
centres=np.array(centres);widths=np.array(widths);buckets={}
for index,xy in enumerate(centres):buckets.setdefault(tuple(np.floor(xy/10).astype(int)),[]).append(index)
rng=np.random.default_rng(710701);rows=[]
for ri,r in enumerate(roads):
    for i,p in enumerate(r['points']):
        yaw=math.radians(p['yaw']);forward=np.array([math.cos(yaw),math.sin(yaw)]);side=np.array([-forward[1],forward[0]])
        for sign in [-1,1]:
            patch=.5+.3*math.sin(i*.18+sign*2+ri)+.2*math.sin(i*.053+sign*4)
            if patch<.21:continue
            categories=[('chip',int(5+patch*10)),('cobble',int(patch*3)),('Fine',int(2+patch*5))]
            if patch>.5:categories.append(('Straw' if rng.random()<.7 else 'Weathered',int(1+patch*2)))
            for kind,count in categories:
                for _ in range(count):
                    offset=float(rng.uniform(.18,1.1) if kind=='chip' else rng.uniform(.75,2.25) if kind=='cobble' else rng.uniform(.45,1.9) if kind=='Fine' else rng.uniform(1.2,3.0))
                    xy=np.array([p['x_m'],p['y_m']])+side*sign*(r['width_m']/2+offset)+forward*rng.uniform(-.95,.95)
                    z=height(*xy)
                    if z<.8:continue
                    slope=math.hypot(height(xy[0]+.3,xy[1])-height(xy[0]-.3,xy[1]),height(xy[0],xy[1]+.3)-height(xy[0],xy[1]-.3))/.6
                    if slope>.7:continue
                    cell=np.floor(xy/10).astype(int)
                    indices=np.array([idx for a in [-1,0,1] for b in [-1,0,1] for idx in buckets.get((cell[0]+a,cell[1]+b),[])])
                    distances=np.linalg.norm(centres[indices]-xy,axis=1)
                    clearance=float(np.min(distances-widths[indices]))
                    minimum=.12 if kind=='chip' else .5 if kind=='Fine' else .65
                    if clearance<minimum:continue
                    scale=float(rng.uniform(.05,.12) if kind=='chip' else rng.uniform(.13,.30) if kind=='cobble' else rng.uniform(.48,.95) if kind=='Fine' else rng.uniform(.55,1.05))
                    mesh='Stone'+str(int(rng.integers(1,5))) if kind in ['chip','cobble'] else kind
                    # The authored stone is already flattened (height ~half its width).
                    sz=scale*(rng.uniform(.8,1.15) if mesh.startswith('Stone') else rng.uniform(.65,1.0))
                    burial=.004 if kind=='chip' else .008 if kind=='cobble' else .025
                    rows.append(dict(mesh=mesh,kind=kind,xyz=[float(xy[0]),float(xy[1]),z-burial],scale=[scale,scale*float(rng.uniform(.8,1.15)),float(sz)],yaw=float(rng.uniform(0,360)),clearance_m=clearance))
counts={k:sum(r['kind']==k for r in rows) for k in sorted(set(r['kind'] for r in rows))}
report=dict(ok=True,instances=rows,counts=counts,seed=710701,road_clearance_min_m=min(r['clearance_m'] for r in rows),terrain_heights_changed=False)
(OUT/'placements.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='instances'},indent=2))
