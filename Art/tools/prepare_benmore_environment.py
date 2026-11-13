"""Deterministic road relief, rock underside samples, and real DEM backdrop."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
import rasterio as rio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreEnvironment';OUT.mkdir(exist_ok=True)
ROAD=ROOT/'Art/Export/BenmoreRoads';n=2017;step=2500/2016
baseline=OUT/'before_height_local_south_up.f32'
if not baseline.exists():baseline.write_bytes((ROAD/'height_local_south_up.f32').read_bytes())
old=np.fromfile(baseline,dtype='<f4').reshape(n,n)
routes=json.loads((ROAD/'road-manifest.json').read_text())['routes']
nearest=np.full((n,n),1e6);delta=np.zeros((n,n))
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
for r in routes:
    for p,q in zip(r['points'][:-1],r['points'][1:]):
        a=np.array([p['x_m'],p['y_m']]);v=np.array([q['x_m'],q['y_m']])-a;length=np.linalg.norm(v)
        if length<.001:continue
        reach=r['width_m']/2+1
        lo=np.maximum(0,np.floor((np.minimum(a,a+v)-reach+1250)/step).astype(int));hi=np.minimum(n-1,np.ceil((np.maximum(a,a+v)+reach+1250)/step).astype(int));sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
        x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)*step-1250,np.arange(lo[1],hi[1]+1)*step-1250)
        t=np.clip(((x-a[0])*v[0]+(y-a[1])*v[1])/length**2,0,1);dist=np.hypot(x-a[0]-t*v[0],y-a[1]-t*v[1]);take=dist<nearest[sl]
        s=p['arc_m']+t*length;lat=((y-a[1])*v[0]-(x-a[0])*v[1])/length
        # Wavelengths exceed the grid spacing; small washboard stays in shading.
        patch=.45+.55*smooth(-.7,.7,np.sin(s*.029)+.25*np.sin(s*.081))
        bumps=(.040*np.sin(s*2*math.pi/8.5+lat*.35)+.023*np.sin(s*2*math.pi/15.7-lat*.51))*patch
        wheel=-.020*np.exp(-((abs(lat)-1.05)/.45)**2)
        edge=1-smooth(r['width_m']/2-.65,r['width_m']/2+.8,dist)
        seam=smooth(0,18,s)*(1-smooth(r['length_m']-18,r['length_m'],s))
        d=(bumps+wheel)*edge*seam
        delta[sl]=np.where(take,d,delta[sl]);nearest[sl]=np.minimum(nearest[sl],dist)
new=np.round((old+delta)*64)/64;actual=new-old;new.astype('<f4').tofile(OUT/'height_local_south_up.f32')
enc=np.uint16(np.round(new*64+32768));rgba=np.zeros((n,n,4),np.uint8);rgba[:,:,0]=enc>>8;rgba[:,:,1]=enc&255;rgba[:,:,3]=255;Image.fromarray(rgba).save(OUT/'T_Benmore_RoadReliefRG.png')
def sample(grid,x,y):
    f=np.clip((np.asarray(x)+1250)/step,0,2015.999999);g=np.clip((np.asarray(y)+1250)/step,0,2015.999999);i=f.astype(int);j=g.astype(int);a=f-i;b=g-j
    return (grid[j,i]*(1-a)+grid[j,i+1]*a)*(1-b)+(grid[j+1,i]*(1-a)+grid[j+1,i+1]*a)*b
checks=[]
for r in routes:
    p=r['points'];x=np.array([v['x_m'] for v in p]);y=np.array([v['y_m'] for v in p]);h=sample(new,x,y)
    grade=np.abs(np.diff(h))/np.maximum(np.hypot(np.diff(x),np.diff(y)),.001)
    checks.append({'route':r['name'],'max_grade_percent':float(grade.max()*100),'max_added_height_m':float(np.max(abs(sample(new,x,y)-sample(old,x,y))))})
anchors=[(int(y),int(x)) for y in range(80,2017,260) for x in range(80,2017,260)];anchors += [np.unravel_index(np.argmax(actual),actual.shape),np.unravel_index(np.argmin(actual),actual.shape)]
report={'ok':True,'max_raise_m':float(actual.max()),'max_cut_m':float(-actual.min()),'changed_vertices':int(np.count_nonzero(abs(actual)>.001)),'routes':checks,'anchors':[{'pixel':[int(x),int(y)],'z_m':float(new[y,x])} for y,x in anchors]}
assert np.max(abs(actual))<=.095
(OUT/'height-report.json').write_text(json.dumps(report,indent=2))
# Sample vertical intersections with all source triangles, retaining the underside.
inspection=json.loads((OUT/'inspection.json').read_text());undersides={}
for key,mesh in inspection['meshes'].items():
    v=np.array(mesh['vertices'])/100;tris=np.array(mesh['triangles']).reshape(-1,3)
    xs=np.arange(v[:,0].min()+.08,v[:,0].max(),.4);ys=np.arange(v[:,1].min()+.08,v[:,1].max(),.4);xx,yy=np.meshgrid(xs,ys);zz=np.full(xx.shape,np.inf)
    for tri in tris:
        a,b,c=v[tri];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8:continue
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;w=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;t=1-u-w
        hit=(u>=0)&(w>=0)&(t>=0);zz=np.where(hit,np.minimum(zz,u*a[2]+w*b[2]+t*c[2]),zz)
    valid=np.isfinite(zz);undersides[key]=np.stack([xx[valid],yy[valid],zz[valid]],axis=1).tolist()
(OUT/'rock-undersides.json').write_text(json.dumps(undersides))
# Resample the existing geographic source, preserving metres and cardinal axes.
srcfile=ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif'
with rio.open(srcfile) as src:
    bounds=list(src.bounds);spacing=10.;w=int((bounds[2]-bounds[0])/spacing);h=int((bounds[3]-bounds[1])/spacing)
    dem=np.full((h,w),-9999,np.float32);tr=from_origin(bounds[0],bounds[3],spacing,spacing)
    reproject(rio.band(src,1),dem,src_transform=src.transform,src_crs=src.crs,dst_transform=tr,dst_crs=src.crs,resampling=Resampling.average)
    assert np.min(dem)>0
cx,cy=1383300,5081149;datum=360.531005859375
def terrain(x,y):
    f=np.clip((x+cx-bounds[0])/spacing-.5,0,w-1.00001);g=np.clip((bounds[3]-y-cy)/spacing-.5,0,h-1.00001);i=f.astype(int);j=g.astype(int);a=f-i;b=g-j
    return (dem[j,i]*(1-a)+dem[j,i+1]*a)*(1-b)+(dem[j+1,i]*(1-a)+dem[j+1,i+1]*a)*b-datum
local=[bounds[0]-cx+20,bounds[1]-cy+20,bounds[2]-cx-20,bounds[3]-cy-20]
corners=np.array([[local[0],local[1]],[local[2],local[1]],[local[2],local[3]],[local[0],local[3]]]);inner=np.array([[-1245,-1245],[1245,-1245],[1245,1245],[-1245,1245]])
# Four patches, dense at the playable boundary, progressively coarser outwards.
parts=[];edge_count=1009;rings=np.r_[0,.001,.003,.006,.012,.02,np.linspace(.03,1,45)]
for side in range(4):
    t=np.linspace(0,1,edge_count)[:,None];a=inner[side]*(1-t)+inner[(side+1)%4]*t;b=corners[side]*(1-t)+corners[(side+1)%4]*t
    xy=a[None,:,:]*(1-rings[:,None,None])+b[None,:,:]*rings[:,None,None];x=xy[:,:,0];y=xy[:,:,1];z=terrain(x,y)
    distance=np.maximum(abs(x),abs(y))-1250;blend=smooth(-5,35,distance)
    edgeh=sample(new,np.clip(x,-1250,1250),np.clip(y,-1250,1250))
    z=np.where(distance<35,edgeh*(1-blend)+z*blend-.20*(1-blend),z)
    verts=np.stack([x,y,z],axis=-1).reshape(-1,3)
    # Binary arrays for Blender, with vertices already in UE metre axes.
    name='SM_Benmore_Backdrop_'+str(side);verts.astype('<f4').tofile(OUT/(name+'.f32'))
    parts.append({'name':name,'rows':len(rings),'columns':edge_count,'vertices':len(verts)})
back={'source':str(srcfile),'attribution':'LINZ Data Service / Toitu Te Whenua, CC BY 4.0','bounds_nztm':bounds,'local_bounds_m':local,'playable_hole_m':2490,'geographic_heights':True,'scenery_only':True,'parts':parts,'triangles':len(parts)*(len(rings)-1)*(edge_count-1)*2}
(OUT/'backdrop.json').write_text(json.dumps(back,indent=2));print(json.dumps({'height':{k:v for k,v in report.items() if k!='anchors'},'underside_samples':{k:len(v) for k,v in undersides.items()},'backdrop':back},indent=2))
