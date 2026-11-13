"""Full LINZ coverage; metric terrain with host-authored ecology and playable loop.
Source tiles remain untouched. Roads/vegetation are a study, not surveyed features.
"""
from pathlib import Path
import numpy as np, rasterio, json, math, heapq, struct, hashlib
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/LidarStudy';OUT.mkdir(parents=True,exist_ok=True)
SRC=Path(r'C:/Users/mille/Downloads/lds-new-zealand-2layers-GTiff-SHP/new-zealand-lidar-1m-dem')
N=2048;SIZE=370000.;ORIGIN=-185000.;STEP=SIZE/N
files=[SRC/'CF08.tif',SRC/'CG08.tif']
raw=np.concatenate([rasterio.open(f).read(1) for f in files]);assert raw.shape==(3701,3637) and np.isfinite(raw).all() and raw.min()>-9999
# Keep 1:1 metres. 32m padding on east/west gives a square UE landscape.
padded=np.pad(raw,((0,0),(32,32)),mode='edge')
H=np.array(Image.fromarray(padded).resize((2017,2017),Image.Resampling.BILINEAR))*100
span=32768.;source=np.uint16(np.clip(H/span,0,1)*65535+.5);H=source.astype(np.float32)/65535*span
def resize(a,n):return np.array(Image.fromarray(a.astype(np.float32)).resize((n,n),Image.Resampling.BILINEAR))
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def height(x,y):
 fx=np.clip((np.asarray(x)-ORIGIN)/SIZE*2016,0,2015.99999);fy=np.clip((np.asarray(y)-ORIGIN)/SIZE*2016,0,2015.99999)
 i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def sample(a,x,y):
 i=np.clip(((np.asarray(x)-ORIGIN)/SIZE*a.shape[1]).astype(int),0,a.shape[1]-1);j=np.clip(((np.asarray(y)-ORIGIN)/SIZE*a.shape[0]).astype(int),0,a.shape[0]-1);return a[j,i]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(name+'.png'))
# Path search on actual grades, with water excluded. The selected destinations
# trace the southern shelf, upland hollows and east shore.
K=256;hh=resize(H,K);ww=np.zeros((K,K),dtype=bool)
dy,dx=np.gradient(hh,SIZE/(K-1));sl=np.hypot(dx,dy)
waypoints=[(500,550),(610,535),(622,460),(560,418),(445,430),(415,505),(500,550)]
def astar(start,end):
 start=tuple(round(v/1023*(K-1)) for v in start);end=tuple(round(v/1023*(K-1)) for v in end)
 queue=[(0,start)];cost={start:0};prev={};cell=SIZE/(K-1)
 while queue:
  _,p=heapq.heappop(queue)
  if p==end:break
  for ax,ay in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   q=(p[0]+ax,p[1]+ay)
   if min(q)<2 or max(q)>=K-2 or ww[q[1],q[0]]:continue
   dist=math.hypot(ax,ay);grade=abs(float(hh[q[1],q[0]]-hh[p[1],p[0]]))/(cell*dist)
   c=cost[p]+dist*(1+45*grade*grade+3*float(sl[q[1],q[0]])**2)
   if c<cost.get(q,1e30):cost[q]=c;prev[q]=p;heapq.heappush(queue,(c+math.hypot(q[0]-end[0],q[1]-end[1]),q))
 assert end in prev
 path=[end]
 while path[-1]!=start:path.append(prev[path[-1]])
 return list(reversed(path))
route=[]
for a,b in zip(waypoints,waypoints[1:]):route+=astar(a,b)[bool(route):]
p=np.array(route,dtype=float)/(K-1)*SIZE+ORIGIN
# Two corner-cutting passes preserve a route close to the searched corridor.
for _ in range(2):p=np.vstack([p[0],np.stack([.75*p[:-1]+.25*p[1:],.25*p[:-1]+.75*p[1:]],axis=1).reshape(-1,2),p[-1]])
roadimg=Image.new('L',(N,N));draw=ImageDraw.Draw(roadimg)
for k,(a,b) in enumerate(zip(p,p[1:])):
 width=6.5+1.7*math.sin(k*.09)+.7*math.sin(k*.23)
 draw.line([tuple((a-ORIGIN)/STEP),tuple((b-ORIGIN)/STEP)],fill=255,width=max(2,round(width*100/STEP)))
road=np.array(roadimg.filter(ImageFilter.GaussianBlur(.6)),dtype=np.float32)/255
rng=np.random.default_rng(161026)
def noise(n):return resize(rng.random((n,n)).astype(np.float32),N)
yy,xx=np.mgrid[:N,:N];x=ORIGIN+(xx+.5)*STEP;y=ORIGIN+(yy+.5)*STEP;z=height(x,y)
gy,gx=np.gradient(z,STEP);slope=np.hypot(gx,gy);broad=noise(45);fine=noise(221)
local=resize(resize(z,120),N);concavity=np.clip((local-z)/180+.3,0,1)
rock=smooth(.4,.95,slope)*(.65+.35*broad)
wetland=concavity*(1-smooth(.06,.28,slope))*(.5+.5*broad)
wet=np.clip(.25+.7*wetland+.17*road,0,1)
grass=np.clip((1-road*.97)*(1-rock)*(.75+.25*fine),0,1)
sand=np.zeros_like(grass)
depth=np.clip(3+wetland*65+road*(4+30*wetland),0,100)*(1-rock)
paint=np.stack([depth/124,np.ones_like(depth),road*(1-wetland)*.7,.25+.7*wet],-1)
paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
save('paint',paint);save('style',np.stack([sand,grass,wet,rock],-1))
def pack(name,values):
 q=np.uint16(np.clip(values,0,1)*65535+.5);Image.fromarray(np.stack([q>>8,q&255,np.zeros_like(q),np.full_like(q,255)],-1).astype('uint8')).save(OUT/(name+'.png'))
pack('rest',(resize(-wetland*3-road*1.2,1024)+50)/65);pack('macro',z/65536)
Image.fromarray(np.stack([source>>8,source&255,np.zeros_like(source),np.full_like(source,255)],-1).astype('uint8')).save(OUT/'HeightRG.png');source.astype('<u2').tofile(OUT/'height.r16')
# Dense mixed-height forest with coherent openings; all coverage participates.
tx,ty=np.meshgrid(np.arange(ORIGIN+4000,-ORIGIN-4000,1300),np.arange(ORIGIN+1500,-ORIGIN-1500,1300));tx=tx.ravel()+rng.uniform(-470,470,tx.size);ty=ty.ravel()+rng.uniform(-470,470,ty.size)
cluster=sample(broad,tx,ty);gs=sample(grass,tx,ty);rs=sample(road,tx,ty);ss=sample(slope,tx,ty)
keep=(rs<.01)&(ss<.85)&(rng.random(tx.size)<np.clip(.15+cluster,0,.9))
# Route checkpoints select locally gentle terrain.
route_slope=np.hypot((height(p[:,0]+200,p[:,1])-height(p[:,0]-200,p[:,1]))/400,(height(p[:,0],p[:,1]+200)-height(p[:,0],p[:,1]-200))/400)
sites=[]
for name,fraction in [('Trailhead',.02),('Woodland',.26),('Wet hollow',.52),('Ridge return',.78)]:
 target=int((len(p)-1)*fraction);indices=np.arange(len(p));score=np.abs(indices-target)+np.where(route_slope<.14,0,100000);i=int(score.argmin());a=p[i];b=p[min(i+1,len(p)-1)]
 sites.append(dict(name=name,center=a.tolist(),center_height_cm=float(height(*a)),yaw=math.degrees(math.atan2(*(b-a)[::-1]))))
 for_tree=np.hypot(tx-a[0],ty-a[1]);keep &=for_tree>1200
trees=[[round(float(a),2),round(float(b),2),round(float(h),2),int(k),round(float(sc),2),round(float(yaw),2)] for a,b,h,k,sc,yaw in zip(tx[keep],ty[keep],height(tx[keep],ty[keep]),rng.integers(0,3,keep.sum()),rng.uniform(1100,2200,keep.sum()),rng.uniform(0,360,keep.sum()))]
(OUT/'trees.json').write_text(json.dumps(trees,separators=(',',':')))
# Shrubs form thickets at multiple scales across the coverage, with extra verges.
under=[]
ux,uy=np.meshgrid(np.arange(ORIGIN+4000,-ORIGIN-4000,1500),np.arange(ORIGIN+1000,-ORIGIN-1000,1500));ux=ux.ravel()+rng.uniform(-650,650,ux.size);uy=uy.ravel()+rng.uniform(-650,650,uy.size)
centres=np.stack([ux,uy],-1)
for a in centres:
 if sample(slope,*a)>.65 or sample(broad,*a)<.4:continue
 for _ in range(int(rng.integers(1,5))):
  px,py=a+rng.normal(0,450,2)
  if sample(road,px,py)>.015:continue
  kind=int(rng.choice([0,1,2],p=[.72,.12,.16]));under.append(dict(kind=kind,p=[float(px),float(py),float(height(px,py))],height_cm=float(rng.uniform(70,200) if kind==0 else rng.uniform(25,65)),yaw=float(rng.uniform(0,360))))
for a in p[::5]:
 for _ in range(10):
  px,py=a+rng.uniform(-2200,2200,2)
  if sample(road,px,py)>.02 or sample(slope,px,py)>.6:continue
  under.append(dict(kind=0,p=[float(px),float(py),float(height(px,py))],height_cm=float(rng.uniform(40,150)),yaw=float(rng.uniform(0,360))))
(OUT/'understory.json').write_text(json.dumps(under,separators=(',',':')))
# DEM does not measure bathymetry. Only road-basin pools will be authored by
# the existing spill-limited generator; do not invent lakes from low elevations.
domain=np.tile(np.array([0,-1,0,0],dtype='<f4'),(4,4,1));(OUT/'water-domain.bin').write_bytes(struct.pack('<5i3f',0x47545744,4,4,1,1,ORIGIN,ORIGIN,SIZE/4)+domain.tobytes()+bytes([0]))
save('waterflow',np.full((4,4,4),[.5,.5,0,0]));save('waterShore',np.full((4,4,4),[0,0,0,1]))
preview=np.stack([.18+.2*rock+.17*road,.27-.1*road+.08*broad,.10+.1*rock],-1);save('surface-plan',preview)
im=Image.open(OUT/'surface-plan.png');d=ImageDraw.Draw(im)
for site in sites:
 a=(np.array(site['center'])-ORIGIN)/STEP;d.ellipse((a[0]-8,a[1]-8,a[0]+8,a[1]+8),fill='orange');d.text((a[0]+12,a[1]),site['name'],fill='white')
im.resize((1024,1024)).save(OUT/'route-preview.png')
report=dict(ok=True,source_files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files},source='LINZ NZ 1m DEM',horizontal_crs='EPSG:2193',vertical_datum='NZVD2016',source_bounds=[1195326,4863161,1198963,4866862],world_mapping='X east, Y south, Z NZVD2016 cm; central pixel E1197144.5 N4865011.5',padding_east_west_m=32,origin=[ORIGIN,ORIGIN],size=SIZE,height_resolution=2017,landscape_spacing_m=3700/2016,height_span_cm=span,z_scale=span*128/65535,landscape_z_cm=span*32768/65535,terrain_sha256=hashlib.sha256((OUT/'height.r16').read_bytes()).hexdigest(),trees=len(trees),understory=len(under),sites=sites,route_length_m=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()/100),route_grade_p95=float(np.percentile(np.abs(np.diff(height(p[:,0],p[:,1])))/np.maximum(np.linalg.norm(np.diff(p,axis=0),axis=1),1),95)),driving_tested=False,land_use='Host-authored woodland, not reconstructed real vegetation',source_minmax_m=[float(raw.min()),float(raw.max())])
(OUT/'route.json').write_text(json.dumps(p.tolist()));(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
