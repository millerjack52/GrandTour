"""Deterministic scenery groups on the surveyed driving terrain."""
from pathlib import Path
import numpy as np,json,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreScenery';OUT.mkdir(exist_ok=True)
h=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
step=2500/2016;dy,dx=np.gradient(h,step);slope=np.degrees(np.arctan(np.hypot(dx,dy)))
roads=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
points=np.array([[p['x_m'],p['y_m'],r['width_m']/2] for r in roads for p in r['points']])
def sample(a,x,y):
    fx=(x+1250)/step;fy=(y+1250)/step;i=int(fx);j=int(fy);u=fx-i;v=fy-j
    return float((a[j,i]*(1-u)+a[j,i+1]*u)*(1-v)+(a[j+1,i]*(1-u)+a[j+1,i+1]*u)*v)
def clearance(x,y):return float(np.min(np.hypot(points[:,0]-x,points[:,1]-y)-points[:,2]))
rng=np.random.default_rng(710);trees=[];rocks=[]
for gi,(cx,cy,count) in enumerate([(-1115,-1020,7),(-1122,-650,7),(-1115,-350,6),(-889,-192,7)]):
    accepted=[]
    for attempt in range(400):
        if len(accepted)==count:break
        x,y=np.array([cx,cy])+rng.normal(0,[20,17]);z=sample(h,x,y)
        if not(1.2<z<9) or sample(slope,x,y)>16 or clearance(x,y)<14:continue
        if any(math.hypot(x-p[0],y-p[1])<8 for p in accepted):continue
        accepted.append((x,y));variant=['broad','young','windswept','weathered'][len(accepted)%4]
        trees.append(dict(group=gi,variant=variant,xyz=[x,y,z-.07],yaw=float(rng.uniform(0,360)),scale=float(rng.uniform(.86,1.12)*{'young':1.1,'broad':1.8,'windswept':1.8,'weathered':1.65}[variant]),road_clearance_m=clearance(x,y)))
    assert len(accepted)==count
# Small stone groups reinforce terrace edges and hillside breaks.
anchors=[(-810,-320),(-728,-36),(-635,-652),(-325,-117),(-200,126),(25,126),(262,-92),(-405,250),(570,150),(750,-460),(-145,-905),(-800,620),(350,740)]
for gi,(cx,cy) in enumerate(anchors):
    for attempt in range(20):
        x,y=np.array([cx,cy])+rng.normal(0,[16,12]);z=sample(h,x,y)
        if z<8 or sample(slope,x,y)>34 or clearance(x,y)<13:continue
        scale=float(rng.uniform(.55,1.5))
        rocks.append(dict(group=gi,kind=int(rng.integers(1,4)),xyz=[x,y,z],yaw=float(rng.uniform(0,360)),scale=scale,road_clearance_m=clearance(x,y)))
assert len(trees)==27 and len(rocks)>100
data={'ok':True,'seed':710,'trees':trees,'rocks':rocks,'placement':'Art-directed, not surveyed vegetation','min_tree_road_clearance_m':min(p['road_clearance_m'] for p in trees),'min_rock_road_clearance_m':min(p['road_clearance_m'] for p in rocks)}
(OUT/'placements.json').write_text(json.dumps(data,indent=2));print({'trees':len(trees),'rocks':len(rocks),'tree_road_margin_m':data['min_tree_road_clearance_m'],'rock_road_margin_m':data['min_rock_road_clearance_m']})
