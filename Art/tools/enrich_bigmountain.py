"""Authored Downhill-inspired road ecology; not a decoded native STG generator.

Native evidence: BigMountainResearch/placement-native.txt. Rebuilds from a saved
first-pass baseline so repeated runs never cumulatively carve the terrain.
"""
from pathlib import Path
import json, math, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BigMountain'
BASE=OUT/'FirstPass';BASE.mkdir(exist_ok=True)
for name in ['authoring.json','height.r16','paint.png','style.png','rest.png','macro.png','trees.json','understory.json','route.json','water-domain.bin','waterflow.png','waterShore.png']:
 if not (BASE/name).exists():shutil.copy2(OUT/name,BASE/name)
data=json.loads((BASE/'authoring.json').read_text());SPAN=data['height_span_cm'];O=-250000.;SIZE=500000.;N=2048
H=np.fromfile(BASE/'height.r16',dtype='<u2').reshape(1009,1009).astype(np.float32)/65535*SPAN
original=H.copy();p=np.array(json.loads((BASE/'route.json').read_text()));rng=np.random.default_rng(515928)
chain=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def resize(a,n):return np.array(Image.fromarray(a.astype(np.float32)).resize((n,n),Image.Resampling.BILINEAR))
def height(x,y):
 fx=np.clip((np.asarray(x)-O)/SIZE*1008,0,1007.999);fy=np.clip((np.asarray(y)-O)/SIZE*1008,0,1007.999)
 i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def sample(a,x,y):
 i=np.clip(((np.asarray(x)-O)/SIZE*a.shape[1]).astype(int),0,a.shape[1]-1);j=np.clip(((np.asarray(y)-O)/SIZE*a.shape[0]).astype(int),0,a.shape[0]-1);return a[j,i]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(name+'.png'))
def pack(name,a):
 q=np.uint16(np.clip(a,0,1)*65535+.5);Image.fromarray(np.stack([q>>8,q&255,np.zeros_like(q),np.full_like(q,255)],-1).astype('uint8')).save(OUT/(name+'.png'))
# Two bypass tracks reconnect to the main route; lengths follow landform.
paths=[p];types=[0]
for fraction,side in [(.22,1),(.72,-1)]:
 k=int(fraction*len(p));part=p[k:k+34].copy();t=np.linspace(0,1,len(part));d=np.gradient(part,axis=0);d/=np.maximum(np.linalg.norm(d,axis=1)[:,None],1)
 part+=np.stack([-d[:,1],d[:,0]],-1)*(side*2000*np.sin(np.pi*t)**2)[:,None]
 paths.append(part);types.append(1)
def roadfield(n,vertices=False):
 step=SIZE/(n-1 if vertices else n);coords=O+(np.arange(n)+(0 if vertices else .5))*step
 best=np.full((n,n),1e10,dtype=np.float32);signed=best.copy();along=np.zeros_like(best);target=np.zeros_like(best);branch=np.zeros_like(best)
 for path,kind in zip(paths,types):
  h=height(path[:,0],path[:,1]);h=np.convolve(np.pad(h,(4,4),mode='edge'),np.ones(9)/9,mode='valid');s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
  for k,(a,b) in enumerate(zip(path,path[1:])):
   lo=np.clip(np.floor((np.minimum(a,b)-O-14000)/step).astype(int),0,n-1);hi=np.clip(np.ceil((np.maximum(a,b)-O+14000)/step).astype(int)+1,0,n)
   sl=np.s_[lo[1]:hi[1],lo[0]:hi[0]];yy,xx=np.meshgrid(coords[lo[1]:hi[1]],coords[lo[0]:hi[0]],indexing='ij');v=b-a;l=max(np.dot(v,v),.01);t=np.clip(((xx-a[0])*v[0]+(yy-a[1])*v[1])/l,0,1)
   dx=xx-a[0]-t*v[0];dy=yy-a[1]-t*v[1];dist=np.hypot(dx,dy);mask=dist<best[sl]
   best[sl][mask]=dist[mask];signed[sl][mask]=np.sign(v[0]*dy-v[1]*dx)[mask]*dist[mask]
   along[sl][mask]=(s[k]+t*(s[k+1]-s[k]))[mask];target[sl][mask]=(h[k]+t*(h[k+1]-h[k]))[mask];branch[sl][mask]=kind
 return best,signed,along,target,branch
dist,side,along,target,branch=roadfield(1009,True)
width=np.where(branch>.5,240,380+100*np.sin(along/6100)+55*np.sin(along/1700))
blend=1-smooth(width,width+850,dist)
# Cross-slope bench/crown and shallow discontinuous shoulder drainage.
desired=target+10*np.maximum(0,1-dist/width)-18*np.exp(-((dist-width-190)/170)**2)
H+=np.clip(desired-H,-160,160)*blend
gy,gx=np.gradient(H,SIZE/1008);slope=np.hypot(gx,gy)
pools=[];used=[]
# Puddles are placed at surveyed low-gradient route locations, not arbitrary
# world-space circles. Their irregular basin beds and water mean agree.
for distance in np.linspace(10000,chain[-1]-15000,38):
 k=int(np.argmin(abs(chain-distance)));candidates=[]
 for q in p[max(0,k-20):min(len(p),k+20):2]:
  for offset in [(0,0),(600,0),(-600,0),(0,600),(0,-600)]:
   c=q+offset;g=float(sample(slope,*c));pen=np.linalg.norm(c-p[k])/12000
   if all(np.linalg.norm(c-v)>6500 for v in used):candidates.append((g+pen,c))
 if not candidates:continue
 score,c=min(candidates,key=lambda a:a[0])
 if float(sample(slope,*c))>.14:continue
 if any(np.linalg.norm(c-np.array(s['center']))<1800 for s in data['sites']):continue
 angle=float(rng.uniform(0,math.pi));rx=float(rng.uniform(700,1000));ry=float(rng.uniform(500,750));depth=float(rng.uniform(14,32));level=float(height(*c))-8
 probe=np.linspace(-max(rx,ry)*2.6,max(rx,ry)*2.6,11);qy,qx=np.meshgrid(probe+c[1],probe+c[0],indexing='ij')
 if float(np.max(np.abs(height(qx,qy)-level)))>600:continue
 used.append(c);pools.append(dict(center=c.tolist(),rx=rx,ry=ry,angle=angle,level_cm=level,depth_cm=depth))
def poolq(pool,x,y):
 dx=x-pool['center'][0];dy=y-pool['center'][1];a=pool['angle'];u=(dx*np.cos(a)+dy*np.sin(a))/pool['rx'];v=(-dx*np.sin(a)+dy*np.cos(a))/pool['ry'];theta=np.arctan2(v,u)
 return np.hypot(u,v)/(1+.13*np.sin(3*theta+a)+.07*np.cos(5*theta))
cy,cx=np.meshgrid(np.linspace(O,-O,1009),np.linspace(O,-O,1009),indexing='ij')
for pool in pools:
 q=poolq(pool,cx,cy);desired=pool['level_cm']-pool['depth_cm']*(1-np.minimum(q,1)**2)+22*np.maximum(q-1,0);a=1-smooth(1.8,2.6,q);H=H*(1-a)+desired*a
# Keep stable recovery pads; these are not part of the puddle challenge.
for s in data['sites']:
 x,y=s['center'];q=np.hypot(cx-x,cy-y);a=1-smooth(450,1250,q);H=H*(1-a)+float(height(x,y))*a
assert H.min()>=0 and H.max()<=SPAN+.1
encoded=np.uint16(H/SPAN*65535+.5);H=encoded.astype(np.float32)/65535*SPAN
encoded.astype('<u2').tofile(OUT/'height.r16');pack('HeightRG',encoded/65535.)
dist,side,along,target,branch=roadfield(N)
coord=O+(np.arange(N)+.5)*SIZE/N;yy,xx=np.meshgrid(coord,coord,indexing='ij');z=height(xx,yy)
broad=resize(rng.random((51,51)),N);fine=resize(rng.random((287,287)),N)
width=np.where(branch>.5,230,380+100*np.sin(along/6100)+55*np.sin(along/1700));road=1-smooth(width-70,width+170+(fine-.5)*170,dist)
wetpatch=np.zeros_like(road)
for center,length in [(16000,6000),(48000,4000),(83000,7500),(132000,8500),(194000,5500),(244000,11000),(311000,6000),(375000,7500)]:wetpatch=np.maximum(wetpatch,np.exp(-((along-center)/length)**4))
wetpatch*=.6+.4*fine
poolmask=np.zeros_like(road);poolwet=np.zeros_like(road)
for pool in pools:
 q=poolq(pool,xx,yy);poolwet=np.maximum(poolwet,1-smooth(1,2.3,q));poolmask=np.maximum(poolmask,((q<1.4)&(z<pool['level_cm'])).astype(float))
paint=np.array(Image.open(BASE/'paint.png')).astype(float)/255;style=np.array(Image.open(BASE/'style.png')).astype(float)/255
gy,gx=np.gradient(z,SIZE/N);slope=np.hypot(gx,gy);mud=np.maximum(wetpatch*road,poolwet)
firm=road*(1-wetpatch)*(1-poolwet)
depth=paint[:,:,0]*124;depth=depth*(1-road)+(3+wetpatch*47)*road;depth=np.maximum(depth,poolwet*(35+40*broad))
paint[:,:,0]=depth/124;paint[:,:,2]=firm*.88;paint[:,:,3]=np.maximum(paint[:,:,3]*(1-road)+(.25+.68*wetpatch)*road,poolwet*.95)
style[:,:,0]*=1-road;style[:,:,1]*=1-road*.99
style[:,:,1]=np.maximum(style[:,:,1],(1-smooth(40,140,dist))*(branch>.5)*.8)
style[:,:,1]*=1-poolmask;style[:,:,2]=np.maximum(style[:,:,2]*(1-road)+(.20+.75*wetpatch)*road,poolwet*.96)
style[:,:,3]*=1-road*.8
paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
save('paint',paint);save('style',style);pack('macro',z/65536)
old=np.array(Image.open(BASE/'rest.png'));rest=((old[:,:,0].astype(float)*256+old[:,:,1])/65535*65-50)
rut=-(3+11*fine)*mud+3*np.sin(along/500)*road
pack('rest',(rest*(1-resize(road,1024))+resize(rut,1024)+50)/65)
# Existing native mean-water domain remains unchanged outside the new basins.
blob=(BASE/'water-domain.bin').read_bytes();domain=np.frombuffer(blob[32:-1],dtype='<f4').reshape(1009,1009,4).copy()
dc=O+(np.arange(1009)+.5)*SIZE/1009;dy,dx=np.meshgrid(dc,dc,indexing='ij');bed=height(dx,dy);poolcells=np.zeros((1009,1009),bool)
for pool in pools:
 q=poolq(pool,dx,dy);mask=(q<1.4)&(bed<pool['level_cm']-.5);domain[mask,0]=pool['level_cm'];domain[mask,1]=(pool['level_cm']-bed[mask])/100;domain[mask,2:]=0;poolcells|=mask
(OUT/'water-domain.bin').write_bytes(blob[:32]+domain.astype('<f4').tobytes()+blob[-1:])
flow=np.array(Image.open(BASE/'waterflow.png')).copy();flow[poolcells]=np.uint8([128,128,0,255]);flow[:,:,2][poolcells]=np.uint8(np.clip(domain[:,:,1][poolcells]/2,0,1)*255);Image.fromarray(flow).save(OUT/'waterflow.png')
shore=np.array(Image.open(BASE/'waterShore.png')).astype(float)/255
sc=O+(np.arange(1024)+.5)*SIZE/1024;sy,sx=np.meshgrid(sc,sc,indexing='ij')
for pool in pools:
 q=poolq(pool,sx,sy);mask=(q<1.4)&(height(sx,sy)<pool['level_cm']);shore[mask,0]=1;shore[mask,1]=np.clip(.5+(1-q[mask])*min(pool['rx'],pool['ry'])/400,0,1)
save('waterShore',shore)
# Clip fine local triangles against the very same imported landscape bed.
verts=faces=0
with (OUT/'Puddles.obj').open('w') as f:
 for pool in pools:
  r=max(pool['rx'],pool['ry'])*1.9;xs=np.arange(pool['center'][0]-r,pool['center'][0]+r,150);ys=np.arange(pool['center'][1]-r,pool['center'][1]+r,150)
  for y in ys[:-1]:
   for x in xs[:-1]:
    corners=[(x,y),(x+150,y),(x+150,y+150),(x,y+150)]
    if min(poolq(pool,*v) for v in corners)>1.4:continue
    for ids in [(0,1,2),(0,2,3)]:
     poly=[(*corners[k],float(pool['level_cm']-height(*corners[k]))) for k in ids];clip=[]
     for a,b in zip(poly,poly[1:]+poly[:1]):
      if a[2]>=0:clip.append(a)
      if (a[2]>=0)!=(b[2]>=0):
       t=a[2]/(a[2]-b[2]);clip.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),0))
     if len(clip)<3:continue
     for a in clip:f.write('v %.4f %.4f %.4f\n'%(a[0],-a[1],pool['level_cm']))
     for k in range(1,len(clip)-1):f.write(f'f {verts+1} {verts+k+2} {verts+k+1}\n');faces+=1
     verts+=len(clip)
# Habitat clusters, multiple heights/species, shared cell-occupancy rejection.
items=[];occupied=set()
def add(kind,x,y,h):
 cell=(int(x//125),int(y//125))
 if cell in occupied or sample(poolmask,x,y)>.1 or sample(dist,x,y)<sample(width,x,y)+100:return
 if sample(slope,x,y)>.65:return
 if any(np.hypot(x-s['center'][0],y-s['center'][1])<700 for s in data['sites']):return
 occupied.add(cell);items.append(dict(kind=kind,p=[float(x),float(y),float(height(x,y))],height_cm=float(h),yaw=float(rng.uniform(0,360))))
for a in p[::4]:
 for _ in range(4):
  c=a+rng.uniform(-9500,9500,2);patch=float(sample(broad,*c))
  if patch<.28:continue
  habitat=int(rng.choice([0,1,2,3]));count=int(rng.integers(9,27))
  for _ in range(count):
   x,y=c+rng.normal(0,650,2);kind=int(rng.choice([0,1,2,3,4,5,6],p=[.25,.19,.11,.12,.12,.13,.08]))
   if habitat==0 and rng.random()<.65:kind=0
   if habitat==1 and rng.random()<.65:kind=1
   if habitat==2 and rng.random()<.55:kind=4
   heights=[(65,150),(45,115),(130,280),(30,65),(25,50),(13,35),(35,80)]
   add(kind,x,y,rng.uniform(*heights[kind]))
# Rocks appear as outcrops plus loose fragments; no impenetrable road blockages.
for a in p[::12]:
 sign=rng.choice([-1,1]);c=a+np.array([sign*rng.uniform(900,2300),rng.uniform(-1500,1500)])
 for _ in range(int(rng.integers(4,11))):
  x,y=c+rng.normal(0,460,2);add(int(rng.integers(7,10)),x,y,rng.uniform(18,85))
trees=json.loads((BASE/'trees.json').read_text());kept=[]
for row in trees:
 x,y,z0,k,h,yaw=row
 if sample(dist,x,y)<sample(width,x,y)+230 or sample(poolwet,x,y)>.3:continue
 row[2]=float(height(x,y));kept.append(row)
(OUT/'trees.json').write_text(json.dumps(kept,separators=(',',':')))
(OUT/'ecology.json').write_text(json.dumps(items,separators=(',',':')))
for s in data['sites']:s['center_height_cm']=float(height(*s['center']))
data['terrain_sha256']=hashlib.sha256((OUT/'height.r16').read_bytes()).hexdigest();data['trees']=len(kept);data['understory']=len(items)
(OUT/'authoring.json').write_text(json.dumps(data,indent=2))
report=dict(ok=True,reference='MudRunner Downhill (levels/level_hill.dds)',puddles=pools,puddle_triangles=faces,puddle_domain_cells=int(poolcells.sum()),puddle_max_depth_cm=float(domain[:,:,1][poolcells].max()*100),instances=len(items),types={str(k):sum(i['kind']==k for i in items) for k in range(10)},trees=len(kept),bypass_lengths_m=[float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()/100) for q in paths[1:]],max_cut_cm=float((original-H).max()),max_fill_cm=float((H-original).max()),height_sha256=data['terrain_sha256'],driving_tested=False)
print('Authoring validation:',len(pools),len(items),report['puddle_max_depth_cm'])
assert len(pools)>=4 and len(items)>5000 and report['puddle_max_depth_cm']<50
(OUT/'enrichment-authoring.json').write_text(json.dumps(report,indent=2))
preview=np.stack([.19+.22*firm+.12*mud,.28-.07*road,.12+.06*firm],-1);preview[poolmask>.5]=[.1,.32,.43];save('enrichment-plan',preview)
print(json.dumps({k:v for k,v in report.items() if k!='puddles'},indent=2))
