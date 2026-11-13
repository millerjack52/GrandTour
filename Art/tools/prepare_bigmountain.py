"""First playable Big Mountain authoring. Gaea geometry + authored road/ecology.

Road width and separate visual/physical coverage follow inspected MudRunner
presets. Routing, ecology masks and distribution here are host authoring rules,
not a decoded MudRunner STG map generator.
"""
from pathlib import Path
import json, math, heapq, struct, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BigMountain'
N=2048;SIZE=500000.;ORIGIN=-250000.;STEP=SIZE/N
raw=np.array(Image.open(OUT/'Masks/HeightRaw.tif'));base=float(raw.min())
source=np.array(Image.open(OUT/'Build/H_Lake_Out.png'),dtype=np.uint16)
definition=json.loads((OUT/'Build/definition.json').read_text());span=definition['Height']*100
source_height_sha256=hashlib.sha256(source.astype('<u2').tobytes()).hexdigest()
raw_depth=np.array(Image.open(OUT/'Masks/LakeDepth.tif'))
vertical_offset_cm=float(math.ceil(float(raw_depth.max())*250000)+100)
depth1009=np.array(Image.fromarray(raw_depth).resize((1009,1009),Image.Resampling.BILINEAR))*250000
H=source.astype(np.float32)/65535*span-depth1009+vertical_offset_cm
span=float(H.max());source=np.uint16(np.clip(H/span,0,1)*65535+.5);H=source.astype(np.float32)/65535*span
def resize(a,n):return np.array(Image.fromarray(a.astype(np.float32)).resize((n,n),Image.Resampling.BILINEAR))
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def height(x,y):
 fx=np.clip((np.asarray(x)-ORIGIN)/SIZE*1008,0,1007.99999);fy=np.clip((np.asarray(y)-ORIGIN)/SIZE*1008,0,1007.99999)
 i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def sample(a,x,y):
 i=np.clip(((np.asarray(x)-ORIGIN)/SIZE*a.shape[1]).astype(int),0,a.shape[1]-1);j=np.clip(((np.asarray(y)-ORIGIN)/SIZE*a.shape[0]).astype(int),0,a.shape[0]-1);return a[j,i]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(name+'.png'))
water=np.array(Image.open(OUT/'Masks/LakeWater.tif'))>.5
level=(np.array(Image.open(OUT/'Masks/LakeSurface.tif'))-base)*250000+vertical_offset_cm
# Extend level onto adjacent dry cells for shoreline clipping, without diluting it
# with the zero value which Gaea writes outside its water mask.
valid=water.copy()
for _ in range(8):
 total=np.zeros_like(level);count=np.zeros_like(level)
 for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
  v=np.roll(valid,(dy,dx),(0,1));total+=np.roll(level,(dy,dx),(0,1))*v;count+=v
 add=(~valid)&(count>0);level[add]=total[add]/count[add];valid|=add
level[~valid]=0
# Path search on actual grades, with water excluded. The selected destinations
# trace the southern shelf, upland hollows and east shore.
K=256;hh=resize(H,K);ww=resize(water,K)>.12
dy,dx=np.gradient(hh,SIZE/(K-1));sl=np.hypot(dx,dy)
waypoints=[(220,740),(365,695),(570,710),(620,615),(725,520),(800,440)]
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
 width=7+1.6*math.sin(k*.07)+.7*math.sin(k*.19)
 draw.line([tuple((a-ORIGIN)/STEP),tuple((b-ORIGIN)/STEP)],fill=255,width=max(2,round(width*100/STEP)))
road=np.array(roadimg.filter(ImageFilter.GaussianBlur(.65)),dtype=np.float32)/255
rng=np.random.default_rng(812467)
def noise(n):return resize(rng.random((n,n)).astype(np.float32),N)
yy,xx=np.mgrid[:N,:N];x=ORIGIN+(xx+.5)*STEP;y=ORIGIN+(yy+.5)*STEP;z=height(x,y)
gy,gx=np.gradient(z,STEP);slope=np.hypot(gx,gy);broad=noise(67);fine=noise(263)
wetmask=resize(water,N)>.5;levels=resize(level,N);shore=np.exp(-np.abs(z-levels)/220)*resize(valid,N)
rock=smooth(.32,.75,slope)*(.65+.35*broad)
sand=shore*(1-wetmask)*(.5+.5*fine)*(1-road)*(1-rock)
wetland=(1-smooth(.06,.18,slope))*smooth(.47,.73,broad)*(1-rock)
mud=np.maximum(road*(.35+.65*fine),wetland*.7)*(1-rock)
wet=np.clip(.30+.5*wetland+.35*shore+.18*road,0,1)
# Vegetation cover is independent of soft substrate, as in the native presets.
grass=np.clip((1-road*.98)*(1-sand*.9)*(1-rock)*(.65+.35*fine),0,1);grass[wetmask]=0
depth=np.clip((5+mud*(16+64*wetland)+sand*8)*(1-rock),0,110);depth[rock>.5]=0
paint=np.stack([depth/124,np.ones_like(depth),road*(1-mud),.25+.65*wet],-1)
paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
save('paint',paint)
save('style',np.stack([sand,grass,wet,rock],-1))
rest=-mud*(1.5+4*wetland)
def pack(name,values):
 q=np.uint16(np.clip(values,0,1)*65535+.5);Image.fromarray(np.stack([q>>8,q&255,np.zeros_like(q),np.full_like(q,255)],-1).astype('uint8')).save(OUT/(name+'.png'))
pack('rest',(resize(rest,1024)+50)/65);pack('macro',z/65536)
Image.fromarray(np.stack([source>>8,source&255,np.zeros_like(source),np.full_like(source,255)],-1).astype('uint8')).save(OUT/'HeightRG.png')
source.astype('<u2').tofile(OUT/'height.r16')
sites=[]
for name,fraction in [('Trailhead',.04),('Woodland',.32),('Hollows',.63),('Lakeside',.98)]:
 i=min(len(p)-2,int((len(p)-1)*fraction));a=p[i];b=p[i+1];sites.append(dict(name=name,center=a.tolist(),center_height_cm=float(height(*a)),yaw=math.degrees(math.atan2(*(b-a)[::-1]))))
# The first stationary check exposed excessive side slope at the nominal
# Hollows stop. Keep its recovery point on the nearest flatter route segment.
route_slope=np.hypot((height(p[:,0]+300,p[:,1])-height(p[:,0]-300,p[:,1]))/600,(height(p[:,0],p[:,1]+300)-height(p[:,0],p[:,1]-300))/600)
site=next(s for s in sites if s['name']=='Hollows');distance=np.linalg.norm(p-np.array(site['center']),axis=1)
i=int(np.argmin(np.where(route_slope<.16,distance,1e10)));a=p[i];d=p[min(i+1,len(p)-1)]-p[max(0,i-1)]
site.update(center=a.tolist(),center_height_cm=float(height(*a)),yaw=math.degrees(math.atan2(d[1],d[0])))
tx,ty=np.meshgrid(np.arange(ORIGIN+1200,-ORIGIN-1200,850),np.arange(ORIGIN+1200,-ORIGIN-1200,850));tx=tx.ravel()+rng.uniform(-330,330,tx.size);ty=ty.ravel()+rng.uniform(-330,330,ty.size)
cluster=sample(broad,tx,ty);gs=sample(grass,tx,ty);rs=sample(road,tx,ty);ss=sample(slope,tx,ty);tz=height(tx,ty)
keep=(gs>.45)&(rs<.015)&(ss<.55)&(rng.random(tx.size)<np.clip((cluster-.18)*1.5,.06,.75))
for s in sites:keep&=np.hypot(tx-s['center'][0],ty-s['center'][1])>800
trees=[[round(float(a),2),round(float(b),2),round(float(h),2),int(k),round(float(sc),2),round(float(yaw),2)] for a,b,h,k,sc,yaw in zip(tx[keep],ty[keep],tz[keep],rng.integers(0,3,keep.sum()),rng.uniform(950,1850,keep.sum()),rng.uniform(0,360,keep.sum()))]
(OUT/'trees.json').write_text(json.dumps(trees,separators=(',',':')))
# Bush/sapling/debris clusters across a bounded 75m corridor, not uniform dots.
under=[]
for a in p[::4]:
 for _ in range(12):
  px,py=a+rng.uniform(-7500,7500,2)
  if sample(grass,px,py)<.42 or sample(road,px,py)>.02 or sample(slope,px,py)>.45 or rng.random()>sample(broad,px,py):continue
  kind=int(rng.choice([0,1,2],p=[.65,.15,.2]));under.append(dict(kind=kind,p=[float(px),float(py),float(height(px,py))],height_cm=float(rng.uniform(65,180) if kind==0 else rng.uniform(25,55)),yaw=float(rng.uniform(0,360))))
(OUT/'understory.json').write_text(json.dumps(under,separators=(',',':')))
# Domain and static geometry use the same Gaea mean surface and terrain bed.
D=1009;coord=ORIGIN+(np.arange(D)+.5)*SIZE/D;wy,wx=np.meshgrid(coord,coord,indexing='ij');bed=height(wx,wy);wl=resize(level,D);wm=resize(water,D)>.5
dep=(wl-bed)/100;wet=wm&(dep>.005);domain=np.stack([wl,np.where(wet,dep,-1),np.zeros_like(wl),np.zeros_like(wl)],-1).astype('<f4')
(OUT/'water-domain.bin').write_bytes(struct.pack('<5i3f',0x47545744,D,D,1,1,ORIGIN,ORIGIN,SIZE/D)+domain.tobytes()+bytes([0]))
assert np.count_nonzero(wet)>10000,'Lake bed must be below its surface'
site=sites[-1];cost=np.where((dep>.2)&(dep<.8)&wet,(wx-site['center'][0])**2+(wy-site['center'][1])**2,1e20)
j,i=np.unravel_index(cost.argmin(),cost.shape);assert cost[j,i]<1e20
(OUT/'water-probe.json').write_text(json.dumps(dict(point=[float(wx[j,i]),float(wy[j,i])],surface_cm=float(wl[j,i]),depth_m=float(dep[j,i])),indent=2))
flow=np.stack([np.full_like(dep,.5),np.full_like(dep,.5),np.clip(dep/2,0,1),wet.astype(float)],-1);save('waterflow',flow)
rawlevel=np.array(Image.open(OUT/'Masks/LakeSurface.tif'))
rawbed=raw-raw_depth
gy,gx=np.gradient(rawbed*2500,5000/1023)
bank_distance=(rawlevel-rawbed)*2500/np.maximum(np.hypot(gx,gy),.02)
bank_distance=np.where(water,bank_distance,-2)
save('waterShore',np.stack([water.astype(float),.5+np.clip(bank_distance,-2,2)/4,np.zeros_like(raw),np.ones_like(raw)],-1))
# Mesh triangles clipped at the shoreline height intersection. Coarser interior
# water vertices are sufficient; the existing moving grid supplies near waves.
M=1009;coord=np.linspace(ORIGIN,-ORIGIN,M);my,mx=np.meshgrid(coord,coord,indexing='ij');mb=height(mx,my);ml=resize(level,M);mw=resize(water,M)>.5
f=OUT/'Water.obj';verts=0;faces=0
with f.open('w') as out:
 for j in range(M-1):
  for i in range(M-1):
   ids=[(j,i),(j,i+1),(j+1,i+1),(j+1,i)]
   if not any(mw[t] for t in ids):continue
   surf=float(np.median([ml[t] for t in ids if mw[t]]))
   for indices in [(0,1,2),(0,2,3)]:
    poly=[(float(mx[ids[k]]),float(my[ids[k]]),float(surf-mb[ids[k]])) for k in indices];clipped=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
     if a[2]>=0:clipped.append(a)
     if (a[2]>=0)!=(b[2]>=0):
      t=a[2]/(a[2]-b[2]);clipped.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),0))
    if len(clipped)<3:continue
    for a in clipped:out.write('v %.4f %.4f %.4f\n'%(a[0],-a[1],surf))
    for k in range(1,len(clipped)-1):out.write(f'f {verts+1} {verts+k+2} {verts+k+1}\n');faces+=1
    verts+=len(clipped)
preview=np.stack([.22+.15*rock+.1*road,.29-.09*road,.12+.13*rock],-1);preview[wetmask]=[.1,.28,.36];save('surface-plan',preview)
im=Image.open(OUT/'surface-plan.png');d=ImageDraw.Draw(im)
for s in sites:
 a=(np.array(s['center'])-ORIGIN)/STEP;d.ellipse((a[0]-8,a[1]-8,a[0]+8,a[1]+8),fill='orange');d.text((a[0]+12,a[1]),s['name'],fill='white')
im.resize((1024,1024)).save(OUT/'route-preview.png')
report=dict(ok=True,source_height_sha256=source_height_sha256,vertical_offset_cm=vertical_offset_cm,bed_reconstructed_from_gaea_depth=True,origin=[ORIGIN,ORIGIN],size=SIZE,height_resolution=1009,height_span_cm=span,z_scale=span*128/65535,landscape_z_cm=span*32768/65535,terrain_sha256=hashlib.sha256((OUT/'height.r16').read_bytes()).hexdigest(),trees=len(trees),understory=len(under),sites=sites,route_length_m=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()/100),water_vertices=verts,water_triangles=faces,wet_domain_cells=int(np.count_nonzero(wet)),maximum_lake_depth_m=float(dep[wet].max()),route_grade_p95=float(np.percentile(np.abs(np.diff(height(p[:,0],p[:,1])))/np.maximum(np.linalg.norm(np.diff(p,axis=0),axis=1),1),95)),water_source='Gaea Lake Surface; mean levels retained, no synthetic circular basins',driving_tested=False)
(OUT/'route.json').write_text(json.dumps(p.tolist()))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
