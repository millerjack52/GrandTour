"""Native MudRunner surface inputs, mapped onto the owner's LiDAR route.

DDS pixels are converted losslessly, not repainted. Route masks, ecology and
seed addressing are host authoring. Candidate coordinates are the executed
native editor pattern bank; this does not claim full editor rebuild parity.
"""
from pathlib import Path
import hashlib,json,math,shutil
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/LidarStudy/Place/TrackDetail'
MEDIA=Path('C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor/Media')
ID='fce56694-1591-406d-8ac5-75b330a90436'
VERSION='LT4-native-1'
N=1024
SOURCES=['tiles_forest__d_a','overlays_dirt_road__d_a','overlays_dirt_path__d_a','overlays_dirt_road_smooth__d_a']

def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 roadfile=ROOT/'Art/Export/LidarStudy/Place/roads.json'
 path=next(r['authoring'] for r in json.loads(roadfile.read_text()) if r.get('authoring',{}).get('id')==ID)
 pts=np.array(path['points_cm'],dtype=float)/100;knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
 widths=np.array(path.get('widths_m',[path['width_m']]*len(pts)))
 lo=np.floor(pts[:,:2].min(0)-12);span=float(np.ceil(max(pts[:,:2].max(0)-lo)+12))
 yy,xx=np.mgrid[:N,:N];x=lo[0]+(xx+.5)*span/N;y=lo[1]+(yy+.5)*span/N
 dist=np.full((N,N),np.inf);station=np.zeros_like(dist);across=np.zeros_like(dist);width=np.zeros_like(dist)
 for k,(a,b) in enumerate(zip(pts,pts[1:])):
  # Restrict projection to each segment's expanded bounding rectangle.
  mn=np.maximum(0,np.floor((np.minimum(a[:2],b[:2])-12-lo)*N/span).astype(int));mx=np.minimum(N,np.ceil((np.maximum(a[:2],b[:2])+12-lo)*N/span).astype(int))
  sl=np.s_[mn[1]:mx[1],mn[0]:mx[0]];dx,dy=b[:2]-a[:2];l2=dx*dx+dy*dy
  t=np.clip(((x[sl]-a[0])*dx+(y[sl]-a[1])*dy)/l2,0,1)
  ox=x[sl]-a[0]-t*dx;oy=y[sl]-a[1]-t*dy;ds=ox*ox+oy*oy;take=ds<dist[sl]
  dist[sl][take]=ds[take];station[sl][take]=(knots[k]+t*(knots[k+1]-knots[k]))[take]
  across[sl][take]=((-dy*ox+dx*oy)/math.sqrt(l2))[take]
  width[sl][take]=(widths[k]*(1-t)+widths[k+1]*t)[take]
 valid=np.isfinite(dist)
 # Extend UV coordinates outside the corridor for clean filtering at its edge.
 inds=distance_transform_edt(~valid,return_distances=False,return_indices=True)
 for a in [station,across,width]:a[~valid]=a[tuple(inds[:,~valid])]
 wet=np.full((N,N),path['wetness']);firm=np.full_like(wet,path['firmness']);churn=np.zeros_like(wet)
 for c in path['conditions']:
  b=max(.01,c['blend_metres']);w=smooth(c['start_metres']-b,c['start_metres']+b,station)*(1-smooth(c['end_metres']-b,c['end_metres']+b,station))
  wet=wet*(1-w)+c['wetness']*w;firm=firm*(1-w)+c['firmness']*w;churn=churn*(1-w)+c.get('churn',0)*w
 # A painted composition in the owner's route frame: broad patches, one-sided
 # accumulation and cleaner tyre paths. Not claimed recovered artist brush history.
 variation=.5+.24*np.sin(station*.153+np.sin(station*.037))+.18*np.sin(station*.47+across*1.3)
 edge=smooth(.65,1.7,np.abs(across));wheel=np.exp(-((np.abs(across)-.82)/.27)**2)
 litter=np.clip(1.65*(.18+.65*firm)*(variation*.65+edge*.45)*(1-.8*wheel)*(1-.65*churn),0,.85)
 litter*=smooth(158,190,station)
 coverage=(1-smooth(width*.5+.25,width*.5+1.5,np.sqrt(dist)))*smooth(0,4,station)*(1-smooth(knots[-1]-4,knots[-1],station))
 # Preserve the river bed and cobble point; the firm dirt reaches each bank.
 for a,b in [(77,94),(139,155)]:coverage*=1-smooth(a-2,a+2,station)*(1-smooth(b-2,b+2,station))
 selector=np.clip(.5+.5*np.sin(station*.083+.7*np.sin(station*.019)),0,1)
 mask=np.stack([coverage,litter,np.clip(churn+(1-firm)*.4,0,1),selector],axis=-1)
 Image.fromarray(np.uint8(np.clip(mask*255,0,255))).save(OUT/'T_Composition.png')
 # Two 16-bit values in RG/BA; decode before interpolation is a linear dot.
 # Do not compress this lookup: block compression would wobble the route UVs.
 ss=np.uint16(np.round(station/1024*65535));aa=np.uint16(np.round((np.clip(across,-32,32)+32)/64*65535))
 uv=np.stack([ss>>8,ss&255,aa>>8,aa&255],axis=-1).astype('uint8')
 Image.fromarray(uv).save(OUT/'T_RouteUV.png')
 sources={}
 for name in SOURCES:
  src=MEDIA/'_t'/(name+'.dds');im=Image.open(src).convert('RGBA');im.save(OUT/(name+'.png'))
  sources[name]=dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),size=list(im.size))
 # Reuse the native editor's 200-candidate/8m-square pattern bank and native
 # probability gate. Host cell seeds/masks choose placement on this route.
 bankfile=ROOT/'Art/Export/MudRunnerEditorResearch/Deep/pattern-bank-800.npy';bank=np.load(bankfile)
 rng=np.random.default_rng(191019);instances=[]
 for cy in range(math.floor(lo[1]/8),math.ceil((lo[1]+span)/8)):
  for cx in range(math.floor(lo[0]/8),math.ceil((lo[0]+span)/8)):
   pattern=bank[(cx*73856093^cy*19349663)&15]
   for ox,oy in pattern:
    px=cx*8+4+float(ox);py=cy*8+4+float(oy);ix=int((px-lo[0])*N/span);iy=int((py-lo[1])*N/span)
    if not(0<=ix<N and 0<=iy<N):continue
    s=float(station[iy,ix]);off=float(across[iy,ix]);hw=float(width[iy,ix])*.5
    if s<170 or s>knots[-1]-3 or not valid[iy,ix] or abs(off)>hw+2.2:continue
    density=float(litter[iy,ix])*(.7 if abs(off)<hw else 1.25)
    probability=max(0,(density-.01)*.06/.99)
    if probability<.0001 or rng.random()>probability:continue
    # Fine visual litter is non-colliding; keep the clear wheel path and pools.
    if abs(abs(off)-.82)<.28 or (churn[iy,ix]>.35 and abs(off)<hw):continue
    mesh=['SM_NZ_TwigLitter_A','SM_NZ_TwigLitter_B','SM_NZ_LeafLitter_A'][int(rng.integers(3))]
    instances.append(dict(mesh=mesh,x_cm=px*100,y_cm=py*100,station_m=round(s,2),across_m=round(off,2),scale=round(float(rng.uniform(.55,.95)),3),yaw=float(rng.uniform(0,360))))
 report=dict(version=VERSION,design_id=ID,route_sha256=hashlib.sha256(roadfile.read_bytes()).hexdigest(),origin_cm=(lo*100).tolist(),span_cm=span*100,resolution=N,texel_cm=span*100/N,length_m=float(knots[-1]),sources=sources,
  instances=instances,density_multiplier=.06,candidate_budget=800,candidate_bank_sha256=hashlib.sha256(bankfile.read_bytes()).hexdigest(),native_source='TerrainCommon.fxh ApplyOverlay; native road default width/aspect; recovered native candidate patterns and density gate',
  host_adapters=['Route masks and section profile selection','Nearest-segment world-to-route lookup','NZ litter mesh substitutions and seed addressing','Mip streaming/compression for UE','No new terrain displacement, POM or additional physics bodies'],
  mask_channels='R corridor; G forest litter; B authored churn; A road profile selector')
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['instances','sources']},indent=2));print('Litter instances:',len(instances))

if __name__=='__main__':main()
