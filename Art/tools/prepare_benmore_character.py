"""Sparse sheltered scrub groups and roadside stock-fence runs."""
from pathlib import Path
import numpy as np,json,math
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreCharacter';OUT.mkdir(exist_ok=True)
h=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
land=np.asarray(Image.open(ROOT/'Art/Export/BenmoreEnvironment/T_Benmore_Landform.png'));rng=np.random.default_rng(10072026)
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
pts=np.array([[p['x_m'],p['y_m'],r['width_m']/2] for r in routes for p in r['points']])
def height(x,y):
    fx=(x+1250)/2500*2016;fy=(y+1250)/2500*2016;i=int(fx);j=int(fy);a=fx-i;b=fy-j
    q,r,s,t=h[j,i],h[j,i+1],h[j+1,i],h[j+1,i+1]
    return float(q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b)
def clearance(x,y):return float(np.min(np.hypot(pts[:,0]-x,pts[:,1]-y)-pts[:,2]))
def slope(x,y):return math.hypot((height(x+1,y)-height(x-1,y))/2,(height(x,y+1)-height(x,y-1))/2)
def shelter(x,y):return land[int((4278-y)/12770*land.shape[0]),int((x+11463)/13680*land.shape[1]),0]/255
centres=[]
for _ in range(10000):
    x,y=rng.uniform(-1060,1000,2)
    if 3<height(x,y)<180 and shelter(x,y)>.57 and slope(x,y)<.48 and 12<clearance(x,y)<180 and all(math.hypot(x-a,y-b)>115 for a,b in centres):centres.append((x,y))
    if len(centres)>=20:break
shrubs=[]
for ci,(cx,cy) in enumerate(centres):
    for _ in range(55):
        x=cx+rng.normal(0,22);y=cy+rng.normal(0,12)
        if not(-1200<x<1200 and -1200<y<1200) or clearance(x,y)<9 or height(x,y)<2 or slope(x,y)>.58:continue
        if any(math.hypot(x-s['x'],y-s['y'])<2.6 for s in shrubs):continue
        shrubs.append({'x':x,'y':y,'z':height(x,y),'height_m':float(rng.uniform(.8,1.85)),'yaw':float(rng.uniform(-180,180)),'kind':int(rng.integers(0,2)),'cluster':ci,'clearance_m':clearance(x,y)})
fences=[]
for name,start,end,side in [('Lakeside fence',100,300,1),('Terrace fence',1270,1530,-1)]:
    route=routes[0];rows=route['points'];arcs=np.array([p['arc_m'] for p in rows]);xx=np.array([p['x_m'] for p in rows]);yy=np.array([p['y_m'] for p in rows]);points=[]
    for arc in np.arange(start,end+1,5):
        if start+85<arc<start+100:points.append(None);continue
        x=float(np.interp(arc,arcs,xx));y=float(np.interp(arc,arcs,yy));x2=float(np.interp(arc+1,arcs,xx));y2=float(np.interp(arc+1,arcs,yy));ang=math.atan2(y2-y,x2-x)
        x-=math.sin(ang)*(route['width_m']/2+7)*side;y+=math.cos(ang)*(route['width_m']/2+7)*side
        if clearance(x,y)<6 or height(x,y)<2:points.append(None);continue
        points.append([x,y,height(x,y),float(rng.uniform(-3,3))])
    fences.append({'name':name,'points':points})
data={'seed':10072026,'shrubs':shrubs,'clusters':centres,'fences':fences,'min_shrub_road_clearance_m':min(s['clearance_m'] for s in shrubs),'height_changed':False}
(OUT/'placements.json').write_text(json.dumps(data,indent=2));print({'scrub':len(shrubs),'clusters':len(centres),'fence_posts':sum(p is not None for f in fences for p in f['points']),'min_clearance':data['min_shrub_road_clearance_m']})
