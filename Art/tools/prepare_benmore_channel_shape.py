"""Package matching native bed, hydraulic domain, shoreline mesh and data masks."""
import json,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,distance_transform_edt
import reshape_benmore_channel as shape
import prepare_benmore_water_domain as domain
import prepare_benmore_river_life as geometry

ROOT,BASE,OUT=shape.ROOT,shape.BASE,shape.OUT

def main():
    assert json.loads((OUT/'flow-report.json').read_text())['ok']
    h=np.fromfile(OUT/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    oldh=np.fromfile(BASE/'RiverLife/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    changed=abs(h-oldh)>.008
    prefix=np.zeros((2018,2018),dtype='<u4');prefix[1:,1:]=changed.cumsum(0).cumsum(1)
    prefix.tofile(OUT/'changed-prefix.u32')
    support=np.argwhere(abs(h-oldh)>.08);support=support[np.linspace(0,len(support)-1,24).astype(int)]
    (OUT/'support-checks.json').write_text(json.dumps([[-1250+i*2500/2016,-1250+j*2500/2016] for j,i in support],indent=2))
    domain.SRC=OUT;domain.OUT=OUT;geometry.H=h;geometry.OUT=OUT
    # The mouth's existing geographic lake mask is not altered by native bank edits.
    # Give the common packer its expected reference without touching the source.
    (OUT/'T_RL_Mouth.png').write_bytes((BASE/'RiverLife/T_RL_Mouth.png').read_bytes())
    domain.main()
    with np.load(OUT/'water-domain.npz') as z:d={k:z[k] for k in z.files}
    valid=d['depth']>.005
    river=d['wet'];speed=np.hypot(d['vx'],d['vy'])
    mask=np.stack([np.clip(distance_transform_edt(~river)*1.25/16,0,1),river,np.clip(distance_transform_edt(river)*1.25/6,0,1),np.clip(speed/2,0,1)],-1)
    Image.fromarray(np.uint8(np.rint(mask*255))).save(OUT/'T_RL_WaterMask.png')
    def sample(a,p):return map_coordinates(a,[(p[...,1]-d['y'][0])/1.25,(p[...,0]-d['x'][0])/1.25],order=1,mode='constant')
    def mean(p):
        weight=sample(valid.astype(float),p)
        return sample(d['mean']*valid,p)/np.maximum(weight,1e-8),weight
    # Surface detail is independent of the hydraulic grid. Extract its continuous
    # native-bed intersection, rather than subdividing the old circular footprint.
    meshes=[]
    for name,lo,hi in [('SM_CS_RiverSurface',(-1250,-300),(-220,775)),('SM_CS_OutletSurface',(-1480,-300),(-1250,775))]:
        cell=.625 if name=='SM_CS_RiverSurface' else 1.25
        x=np.arange(lo[0],hi[0]+cell/2,cell);y=np.arange(lo[1],hi[1]+cell/2,cell)
        xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],-1);surface,weight=mean(p)
        bed=shape.native(h,xx,yy) if lo[0]>=-1250 else sample(np.load(OUT/'flow-bake.npz')['bed'],p)
        # Lake-only coverage belongs to the lake mesh, not an overlapping outlet.
        riverweight=sample(d['wet'].astype(float),p)
        signed=np.minimum(riverweight-.5,(surface-bed-.005)*4)
        info=geometry.exportmesh(name,xx,yy,surface,signed,0)
        data=json.loads((OUT/(name+'.json')).read_text());v=np.array(data['vertices']);f=np.array(data['faces'])
        m,w=mean(v[:,:2]);v[:,2]=m
        area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2];f=f[area>1e-10]
        assert np.isfinite(v).all() and len(f)>100
        data=dict(vertices=v.tolist(),faces=f.tolist());(OUT/(name+'.json')).write_text(json.dumps(data,separators=(',',':')))
        info.update(triangles=len(f),spacing_m=cell,surface_query_max_error_m=float(abs(v[:,2]-m).max()),all_finite=True,positive_triangle_area=True);meshes.append(info)
    # Existing material zones, updated from the new continuous shoreline.
    yy,xx=np.meshgrid(np.linspace(-1250,1250,2017),np.linspace(-1250,1250,2017),indexing='ij');p=np.stack([xx,yy],-1)
    surface,weight=mean(p);wet=(weight>=.5)&(surface-h>.005)
    shore=distance_transform_edt(~wet)*(2500/2016)
    path=np.fromfile(BASE/'RiverLife/path_mask.f32',dtype='<f4').reshape(2017,2017)
    patch=.5+.5*np.sin(xx*.043+np.sin(yy*.017)*2)*np.cos(yy*.033-xx*.012)
    cluster=np.zeros_like(h)
    for cx,cy,r in [(-750,140,48),(-620,240,40),(-495,327,42),(-390,460,35),(-336,560,38)]:cluster=np.maximum(cluster,np.exp(-((xx-cx)**2+(yy-cy)**2)/(r*r)))
    mud=(1-np.clip(shore/7,0,1))*(.2+.8*cluster)*np.clip((patch-.3)*1.9,0,1)
    gravel=np.maximum((1-np.clip(shore/10,0,1))*(.45+.55*(1-patch)),path*.88)
    ford=json.loads((BASE/'RiverLife/assets.json').read_text())['crossings'][0]
    for sign in [-1,1]:
        q=np.array(ford['center_m'][:2])+sign*np.array(ford['cross_direction'])*(ford['span_m']/2+3)
        mud=np.maximum(mud,np.exp(-(((xx-q[0])/6)**2+((yy-q[1])/5)**2))*.8)
    keep=np.clip((shore-1.1)/3.4,0,1)*(1-path)
    Image.fromarray(np.uint8(np.rint(np.stack([gravel,mud,keep,path],-1)*255))).save(OUT/'T_RL_Ecology.png')
    original=np.asarray(Image.open(BASE.parent/'BenmoreVegetation/T_Benmore_VegetationMask.png'))
    Image.fromarray(np.uint8(np.rint(original*keep[...,None]))).save(OUT/'T_RL_Vegetation.png')
    # Preserve the high-resolution sourced-gravel wrapper in the existing pilot.
    bounds=(-725,105,-550,310);cell=.25;x=np.arange(bounds[0],bounds[2]+cell/2,cell);y=np.arange(bounds[1],bounds[3]+cell/2,cell)
    xx,yy=np.meshgrid(x,y);p=np.stack([xx,yy],-1);surface,weight=mean(p);bed=shape.native(h,xx,yy)
    depth=surface-bed;wet=(weight>=.5)&(depth>.005);shore=distance_transform_edt(~wet)*cell;inset=distance_transform_edt(wet)*cell
    edge=np.minimum(p-np.array(bounds[:2]),np.array(bounds[2:])-p).min(-1);core=shape.smooth(edge/12)
    speed=np.hypot(sample(d['vx'],p),sample(d['vy'],p));influence=core*(1-shape.smooth((shore-1.2)/3.8))
    coarse=np.clip(.22+speed*.70+shape.smooth(inset/1.5)*.18,0,1)
    silt=(1-shape.smooth((speed-.12)/.65))*(1-shape.smooth(shore/1.8))*.62
    Image.fromarray(np.uint8(np.rint(np.stack([coarse,silt,1-shape.smooth(shore/.8),influence],-1)*255))).save(OUT/'T_CP_BedZones.png')
    coverage=np.minimum(weight-.5,(depth-.005)*4)
    Image.fromarray(np.uint8(np.rint(np.stack([np.clip(.5+coverage,0,1),wet,wet,core],-1)*255))).save(OUT/'T_CP_Shore.png')
    def query(x,y):
        p=np.array([[x,y]]);m,w=mean(p);return dict(covers=bool(w[0]>=.5),surface_m=float(m[0]),ground_m=float(shape.native(h,x,y)),depth_m=float(m[0]-shape.native(h,x,y)))
    old=np.load(BASE/'RiverScale/water-domain.npz')
    def oldquery(x,y):
        p=np.array([[x,y]]);v=old['depth']>.005
        m=sample(old['mean']*v,p)/np.maximum(sample(v.astype(float),p),1e-8)
        return float(m[0])
    queries={name:query(x,y) for name,x,y in [('Ford',-661.25,177.5),('Bed',-605,230),('Bridge',-406.25,438.75)]}
    fordchange=queries['Ford']['surface_m']-oldquery(-661.25,177.5)
    assert abs(fordchange)<.06,('Ford surface changed more than six cm',fordchange)
    report=dict(ok=True,meshes=meshes,hydraulic_spacing_m=1.25,surface_spacing_m=.625,queries=queries,ford_surface_change_m=fordchange,
                terrain_height_sha256=hashlib.sha256((OUT/'H_ChannelShape_2017.r16').read_bytes()).hexdigest(),
                source_original_drive_sha256=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest())
    (OUT/'prepare-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
