"""Road-relative surface coordinates and small loose aggregate placements."""
from pathlib import Path
import numpy as np,json,math,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreReferenceRoads';OUT.mkdir(exist_ok=True)
REF=ROOT/'Art/References/Environment/BenmoreUserPhotos';REF.mkdir(exist_ok=True)
for i,name in enumerate(['5c71e5cf-8395-4e6c-a653-2cc1c707eaf1','4c351ce0-0b21-4887-9f28-fdcddf6ec46e','f597df2a-c4ee-4d0d-babf-48cc8daf1057','6fc0a6d8-90ef-4d69-af3e-434cbcf79ee1','f35b38c4-904c-4d50-af27-820b86eb88cd'],1):
    shutil.copy2(Path('C:/Users/mille/AppData/Local/Temp')/('codex-clipboard-'+name+'.png'),REF/('Reference_'+str(i)+'.png'))
roads=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
n=2017;step=2500/(n-1);best=np.full((n,n),1e6);m=np.full((n,n,4),.5)
for r in roads:
    pts=r['points'];half=r['width_m']/2
    for p,q in zip(pts[:-1],pts[1:]):
        a=np.array([p['x_m'],p['y_m']]);b=np.array([q['x_m'],q['y_m']]);v=b-a;length=np.linalg.norm(v)
        if length<.001:continue
        lo=np.maximum(0,np.floor((np.minimum(a,b)-18+1250)/step).astype(int));hi=np.minimum(n-1,np.ceil((np.maximum(a,b)+18+1250)/step).astype(int));sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
        X,Y=np.meshgrid(np.arange(lo[0],hi[0]+1)*step-1250,np.arange(lo[1],hi[1]+1)*step-1250)
        t=np.clip(((X-a[0])*v[0]+(Y-a[1])*v[1])/(length*length),0,1);dist=np.hypot(X-a[0]-t*v[0],Y-a[1]-t*v[1]);take=dist<best[sl]
        signed=((Y-a[1])*v[0]-(X-a[0])*v[1])/length
        values=[signed/32+.5,np.full_like(X,half/8),np.full_like(X,v[0]/length*.5+.5),np.full_like(X,v[1]/length*.5+.5)]
        for channel,value in enumerate(values):m[sl+(channel,)]=np.where(take,value,m[sl+(channel,)])
        best[sl]=np.minimum(best[sl],dist)
Image.fromarray(np.uint8(np.clip(m,0,1)*255)).save(OUT/'T_Benmore_RoadCoordinates.png')
h=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(n,n)
def height(x,y):
    f=(x+1250)/step;g=(y+1250)/step;i=int(f);j=int(g);u=f-i;v=g-j
    return float((h[j,i]*(1-u)+h[j,i+1]*u)*(1-v)+(h[j+1,i]*(1-u)+h[j+1,i+1]*u)*v)
rng=np.random.default_rng(7102);stones=[]
for ri,r in enumerate(roads):
    for p in r['points'][::2]:
        a=math.radians(p['yaw']);tangent=np.array([math.cos(a),math.sin(a)]);side=np.array([-tangent[1],tangent[0]])
        for k in range(8):
            # Loose aggregate favours centre and shoulders, leaving compact wheel paths.
            d=float(rng.uniform(-r['width_m']/2-.3,r['width_m']/2+.3))
            if abs(abs(d)-1.05)<.4 and rng.random()<.88:continue
            xy=np.array([p['x_m'],p['y_m']])+side*d+tangent*rng.uniform(-2,2)
            stones.append({'kind':int(rng.integers(1,5)),'xyz':[float(xy[0]),float(xy[1]),height(*xy)-.008],'yaw':float(rng.uniform(0,360)),'scale':float(rng.uniform(.025,.085))})
report={'ok':True,'references':str(REF),'coordinate_encoding':'R signed lateral metres /32 +.5; G half width /8; BA tangent XY *.5+.5; south-up','stones':stones,'terrain_heights_changed':False}
(OUT/'surface-data.json').write_text(json.dumps(report,indent=2));print({'stones':len(stones),'coordinate_map':str(OUT/'T_Benmore_RoadCoordinates.png')})
