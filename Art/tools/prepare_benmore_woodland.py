"""Benmore landform and water masks, new continuous woodland surface authoring.
Material distribution is authored; recovered shader/soil arithmetic lives elsewhere.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreWoodland';OUT.mkdir(parents=True,exist_ok=True)
HEIGHT=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/reloaded-native-height.r16'
H=(np.fromfile(HEIGHT,dtype='<u2').reshape(2017,2017).astype(np.float32)-32768)*200/128
N=2048;SIZE=250000.;ORIGIN=-125000.;STEP=SIZE/N
def height(x,y):
 fx=np.clip((np.asarray(x)+125000)*2016/250000,0,2015.999999);fy=np.clip((np.asarray(y)+125000)*2016/250000,0,2015.999999)
 i=fx.astype(int);j=fy.astype(int);a=fx-i;b=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
 return np.where(a>=b,q+(r-q)*a+(w-r)*b,q+(w-v)*a+(v-q)*b)
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def sample(a,x,y,origin=(ORIGIN,ORIGIN),size=(SIZE,SIZE)):
 ix=np.clip(((x-origin[0])/size[0]*a.shape[1]).astype(int),0,a.shape[1]-1);iy=np.clip(((y-origin[1])/size[1]*a.shape[0]).astype(int),0,a.shape[0]-1);return a[iy,ix]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(OUT/(name+'.png'))
rng=np.random.default_rng(817321)
def noise(n):return np.asarray(Image.fromarray(np.uint8(rng.random((n,n))*255)).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255
yy,xx=np.mgrid[:N,:N];x=ORIGIN+(xx+.5)*STEP;y=ORIGIN+(yy+.5)*STEP;z=height(x,y)
gy,gx=np.gradient(z,STEP);slope=np.hypot(gx,gy);broad=noise(47);fine=noise(213)
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
roadimg=Image.new('L',(N,N));draw=ImageDraw.Draw(roadimg)
for r in routes:
 points=[((p['x_m']*100-ORIGIN)/STEP,(p['y_m']*100-ORIGIN)/STEP) for p in r['points']]
 draw.line(points,fill=255,width=4,joint='curve')
# A connecting crossing keeps the saved river geometry intact.
draw.line([((-67050-ORIGIN)/STEP,(20500-ORIGIN)/STEP),((-68950-ORIGIN)/STEP,(23500-ORIGIN)/STEP)],fill=255,width=4)
road=np.asarray(roadimg.filter(ImageFilter.GaussianBlur(.7)),dtype=np.float32)/255
bed=np.asarray(Image.open(ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/T_GC_ExtendedBedZones.png'),dtype=np.float32)/255
zones=sample(bed,x,y,(-158110.11904762,-125000),(283234.12698413,250124.00793651))
bank=zones[:,:,3];wetbank=zones[:,:,2];silt=zones[:,:,1]
rock=smooth(.38,.8,slope)*(.5+.5*broad)
sand=bank*(1-smooth(.25,.6,silt))*(1-rock)
low=(1-smooth(3500,9500,z))*(1-smooth(.04,.22,slope))
wetland=smooth(.54,.78,broad)*low
# One accessible large bog, feathered by two noise scales, beside the existing route.
q=np.hypot((x+59550)/3100,(y+59475)/1800)
bog=(1-smooth(.55,1.1+(fine-.5)*.25,q))*(1-smooth(.15,.3,slope))
wetland=np.maximum(wetland,bog)
wet=np.clip(.28+.38*wetland+.45*wetbank+.22*road,0,1)
mud=np.maximum(wetland,np.maximum(road*(.45+.55*smooth(.25,.65,broad)),bank*silt))*(1-sand)*(1-rock)
grass=np.clip((1-road)*(1-sand)*(1-rock)*(1-mud),0,1)
depth=(grass*5+sand*11+mud*(15+80*wetland+18*fine))*(1-rock)
depth=np.clip(depth,0,120);depth[depth<.7]=0
depth[rock>.5]=0;grass[rock>.5]=0 # Source rock_slope: IsExtrudable=false, NoGrass=true.
paint=np.stack([depth/124,np.ones_like(x),road*(1-mud),.25+.65*wet],-1)
paint[[0,-1],:,:]=[0,1,0,0];paint[:,[0,-1],:]=[0,1,0,0]
save('paint',paint);save('style',np.stack([sand,grass,wet,rock],-1))
# Rest relief is deliberately independent of the source landform and water depth.
rest=(-1.2-2.2*wetland)*mud;rest=np.asarray(Image.fromarray(rest.astype(np.float32)).resize((1024,1024),Image.Resampling.BILINEAR))
packed=np.uint16(np.clip((rest+50)/65,0,1)*65535+.5)
Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'rest.png')
packed=np.uint16(np.clip(z/32768,0,1)*65535+.5)
Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'macro.png')
preview=np.stack([.11*grass+.27*mud+.37*sand+.25*rock,.23*grass+.18*mud+.32*sand+.26*rock,.09*grass+.10*mud+.21*sand+.26*rock],-1)
save('surface-plan',preview)
# Clustered evergreen stands, with open roads, bogs and river margins.
tx,ty=np.meshgrid(np.arange(-123500,124000,1250),np.arange(-123500,124000,1250));tx=tx.ravel()+rng.uniform(-500,500,tx.size);ty=ty.ravel()+rng.uniform(-500,500,ty.size)
cluster=sample(broad,tx,ty);gs=sample(grass,tx,ty);rs=sample(road,tx,ty);ss=sample(slope,tx,ty);bs=sample(bank,tx,ty)
keep=(rs<.015)&(gs>.22)&(ss<.65)&(bs<.1)&(rng.random(tx.size)<np.clip((cluster-.1)*1.65,.12,.94))
trees=[]
for a,b,h,k,sc,yaw in zip(tx[keep],ty[keep],height(tx[keep],ty[keep]),rng.integers(0,3,np.sum(keep)),rng.uniform(1050,1900,np.sum(keep)),rng.uniform(0,360,np.sum(keep))):trees.append([round(float(a),2),round(float(b),2),round(float(h),2),int(k),round(float(sc),2),round(float(yaw),2)])
(OUT/'trees.json').write_text(json.dumps(trees,separators=(',',':')))
sites=[dict(name=n,center=[a,b],center_height_cm=float(height(float(a),float(b)))) for n,a,b in [('Road',-76250,-43375),('Ford',-68000,22000),('Bog',-59550,-59475)]]
for s in sites:
 a,b=s['center'];s['depth_cm']=float(sample(depth,np.array(a),np.array(b)));s['style']=sample(np.stack([sand,grass,wet,rock],-1),np.array(a),np.array(b)).tolist()
report=dict(terrain_sha256=hashlib.sha256(HEIGHT.read_bytes()).hexdigest(),terrain_edited=False,origin=[ORIGIN,ORIGIN],size=SIZE,resolution=N,trees=len(trees),sites=sites,depth_max_cm=float(depth.max()),native_grid_spacing_cm=12.5)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
