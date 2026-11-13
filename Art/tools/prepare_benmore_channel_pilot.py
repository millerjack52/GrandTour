"""Refine a river surface against existing native ground; no deepening or new flow.

The wet-weight interpolation matches UGTWaterDomain::Sample. Output geometry
and geographic material masks are confined to the first ford reach.
"""
from pathlib import Path
import hashlib, json
import numpy as np
from scipy.ndimage import map_coordinates, distance_transform_edt
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea'
OUT=BASE/'ChannelPilot'
BOUNDS=(-725.,105.,-550.,310.)
CELL=.25

def smooth(v):
    v=np.clip(v,0,1);return v*v*(3-2*v)

def refine(vertices,faces,selected):
    edges=set()
    for a,b,c in faces[selected]:edges.update([tuple(sorted((a,b))),tuple(sorted((b,c))),tuple(sorted((c,a)))])
    vv=vertices.tolist();mid={}
    for a,b in sorted(edges):mid[a,b]=len(vv);vv.append(((vertices[a]+vertices[b])/2).tolist())
    ff=[]
    for tri in faces.tolist():
        m=[mid.get(tuple(sorted((tri[k],tri[(k+1)%3])))) for k in range(3)]
        count=sum(v is not None for v in m)
        if count==0:ff.append(tri)
        elif count==3:
            a,b,c=tri;ab,bc,ca=m;ff.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
        elif count==1:
            k=next(i for i,v in enumerate(m) if v is not None);a,b,c=[tri[(k+j)%3] for j in range(3)];ab=m[k];ff.extend([[a,ab,c],[ab,b,c]])
        else:
            k=next(i for i in range(3) if m[i] is not None and m[(i+1)%3] is not None);a,b,c=[tri[(k+j)%3] for j in range(3)];ab,bc=m[k],m[(k+1)%3];ff.extend([[b,bc,ab],[a,ab,c],[ab,bc,c]])
    return np.array(vv),np.array(ff)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources=[BASE/'RiverLife/height_local_south_up.f32',BASE/'RiverScale/water-domain.bin']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    h=np.fromfile(sources[0],dtype='<f4').reshape(2017,2017)
    with np.load(BASE/'RiverScale/water-domain.npz') as z:d={k:z[k] for k in z.files}
    valid=d['depth']>.005
    def sample(a,p):
        return map_coordinates(a,[(p[...,1]-d['y'][0])/1.25,(p[...,0]-d['x'][0])/1.25],order=1,mode='nearest')
    def mean(p):
        w=sample(valid.astype(float),p)
        return sample(d['mean']*valid,p)/np.maximum(w,1e-8),w
    def ground(p):
        uv=(p+1250)*2016/2500;i,j=uv[...,0].astype(int),uv[...,1].astype(int);s,t=uv[...,0]-i,uv[...,1]-j
        q,r,v,w=h[j,i],h[j,i+1],h[j+1,i],h[j+1,i+1]
        return np.where(s>=t,q+(r-q)*s+(w-r)*t,q+(w-v)*s+(v-q)*t)
    def core(p):
        e=np.minimum(p-np.array(BOUNDS[:2]),np.array(BOUNDS[2:])-p).min(-1)
        return smooth(e/12)
    x=np.arange(BOUNDS[0],BOUNDS[2]+CELL*.5,CELL);y=np.arange(BOUNDS[1],BOUNDS[3]+CELL*.5,CELL)
    xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],-1);surface,weight=mean(p);bed=ground(p)
    depth=surface-bed
    wet=(weight>=.5)&(depth>.005)
    shore=distance_transform_edt(~wet)*CELL
    inset=distance_transform_edt(wet)*CELL
    speed=np.hypot(sample(d['vx'],p),sample(d['vy'],p))
    influence=core(p)*(1-smooth((shore-1.2)/3.8))
    # Geographic material zones, derived from bed/current and shore distance.
    # No painted/generated art maps: actual texture detail comes from licensed sources.
    coarse=np.clip(.22+speed*.70+smooth(inset/1.5)*.18,0,1)
    silt=(1-smooth((speed-.12)/.65))*(1-smooth(shore/1.8))*.62
    damp=1-smooth(shore/.8)
    zones=np.stack([coarse,silt,damp,influence],-1)
    Image.fromarray(np.uint8(np.rint(zones*255))).save(OUT/'T_CP_BedZones.png')
    coverage=np.minimum(weight-.5,(depth-.005)*4)
    mask=np.stack([np.clip(.5+coverage,0,1),wet,wet,core(p)],-1)
    Image.fromarray(np.uint8(np.rint(mask*255))).save(OUT/'T_CP_Shore.png')
    old=json.loads((BASE/'RiverScale/SM_RS_RiverSurface.json').read_text());v=np.array(old['vertices']);f=np.array(old['faces']);before=len(f)
    for _ in range(2):v,f=refine(v,f,core(v[f].mean(1)[:,:2])>0)
    m,w=mean(v[:,:2]);v[:,2]=v[:,2]+(m-v[:,2])*core(v[:,:2])*(w>.01)
    # Trim subdivided shoreline triangles against both the query coverage and native bed.
    signed=np.minimum(w-.5,(v[:,2]-ground(v[:,:2])-.005)*4)
    signed=np.where(core(v[:,:2])>.999,signed,1)
    vv=v.tolist();ff=[];edges={}
    for tri in f:
        polygon=[]
        for k,a in enumerate(tri):
            b=tri[(k+1)%3];da,db=signed[a],signed[b]
            if da>=0:polygon.append(int(a))
            if (da>=0)!=(db>=0):
                edge=tuple(sorted((int(a),int(b))))
                if edge not in edges:edges[edge]=len(vv);vv.append((v[a]+(v[b]-v[a])*da/(da-db)).tolist())
                polygon.append(edges[edge])
        for k in range(1,len(polygon)-1):ff.append([polygon[0],polygon[k],polygon[k+1]])
    v=np.array(vv);f=np.array(ff);area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]
    f=f[area>1e-10];assert np.isfinite(v).all()
    (OUT/'SM_CP_RiverSurface.json').write_text(json.dumps(dict(vertices=v.tolist(),faces=f.tolist()),separators=(',',':')))
    # Sparse decorative aggregate. Exclude live crossing/approach patches so stones
    # cannot hang above subsequently deformed ruts. No new physics obstacles.
    rng=np.random.default_rng(8102026);stones=[]
    pathmask=np.fromfile(BASE/'RiverLife/path_mask.f32',dtype='<f4').reshape(2017,2017)
    candidates=np.argwhere((influence>.7)&(shore<1.8)&(depth<.32)&(depth>-.14)&(coarse>.45))
    used=set()
    for j,i in candidates[rng.permutation(len(candidates))]:
        xy=p[j,i]+rng.uniform(-.1,.1,2);key=tuple(np.floor(xy/.45).astype(int))
        if key in used or np.linalg.norm(xy-[-661.25,177.5])<13:continue
        if map_coordinates(pathmask,[[(xy[1]+1250)/2500*2016],[(xy[0]+1250)/2500*2016]],order=1)[0]>.02:continue
        used.add(key)
        stones.append(dict(xy_m=xy.tolist(),diameter_cm=float(rng.uniform(7,19)),flatten=float(rng.uniform(.35,.60)),yaw=float(rng.uniform(0,360)),mesh=int(rng.integers(1,5))))
        if len(stones)==550:break
    (OUT/'stones.json').write_text(json.dumps(stones,separators=(',',':')))
    assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==digest for k,digest in hashes.items())
    report=dict(ok=True,bounds_m=BOUNDS,mask_spacing_m=CELL,mask_dimensions=[len(x),len(y)],source_hashes=hashes,
                terrain_heights_changed=False,water_query_data_changed=False,source_triangles=before,triangles=len(f),vertices=len(v),stones=len(stones),
                surface_method='Wet-weight interpolation of unchanged physics domain, clipped to native bed; conforming local subdivision',
                source_texture='https://polyhaven.com/a/river_small_rocks',source_texture_repeat_m=2.9,
                limitations=['No new ambient wave renderer','Coarse hydraulic wet-domain outline remains the outer bound','No change to riverbed collision or depth'])
    (OUT/'prepare-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
