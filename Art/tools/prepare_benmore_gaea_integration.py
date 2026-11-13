"""Prepare a terrain-fitted water preview and replacement bank placements.

No second erosion pass and no raised banks. Water is an art preview fitted to
the approved bed, not a new hydraulic simulation or vehicle water volume.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import distance_transform_edt,gaussian_filter,map_coordinates,label
from PIL import Image
from convert_benmore_gaea import OUT,read_height,sha
from prepare_benmore_gaea import resample,smooth01

N=2017;STEP=2500/(N-1);DST=OUT/'integration'


def sample(a,x,y):
    value=map_coordinates(a,[(np.atleast_1d(y)+1250)/STEP,(np.atleast_1d(x)+1250)/STEP],order=1,mode='nearest')
    return value[0] if np.ndim(x)==0 else value


def run(water_only=False):
    DST.mkdir(exist_ok=True)
    h=np.fromfile(OUT/'candidate/height_local_south_up.f32',dtype='<f4').reshape(N,N)
    edit=resample(read_height(OUT/'input/M_FirstPass_Edit_2048.png')[::-1],N)
    protect=np.load(OUT/'source/protect_2017.npy')
    river=resample(read_height(OUT/'return/M_Rivers.tif')[::-1],N)
    depth=resample(read_height(OUT/'return/M_Depth.tif')[::-1],N)*512
    # Limit this review to the approved edit area. Do not place water on roads
    # or across the unchanged tile boundary. Outlet work remains a separate step.
    cover=gaussian_filter(river,.72)*smooth01((edit-.025)/.15)*(1-protect)
    wet=cover>.24
    assert wet.sum()>100
    dist=distance_transform_edt(~wet)*STEP
    (dist.astype('<f4')).tofile(DST/'shore_distance.f32')
    # Low, shallow surface: small Gaea depth variation retained, never use the
    # unblended Gaea surface (which can stand metres above the protected ground).
    waterdepth=np.clip(.065+depth*.8,.065,.20)
    eta=h+waterdepth
    # Match the Landscape's diagonal in every cell. Clip along the river mask.
    yy,xx=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N),indexing='ij')
    vertices=[];faces=[];lookup={}
    def vert(v):
        key=tuple(np.round(v,5))
        if key not in lookup:lookup[key]=len(vertices);vertices.append(v.tolist())
        return lookup[key]
    cells=np.argwhere(np.maximum.reduce([cover[:-1,:-1],cover[1:,:-1],cover[:-1,1:],cover[1:,1:]])>.24)
    for j,i in cells:
        for tri in [[(j,i),(j,i+1),(j+1,i+1)],[(j,i),(j+1,i+1),(j+1,i)]]:
            poly=[(np.array([xx[a,b],yy[a,b],eta[a,b]]),cover[a,b]-.24) for a,b in tri];clipped=[]
            for k,(p,v) in enumerate(poly):
                q,w=poly[(k+1)%3]
                if v>=0:clipped.append(p)
                if (v>=0)!=(w>=0):clipped.append(p+(q-p)*v/(v-w))
            if len(clipped)>=3:
                ids=[vert(v) for v in clipped]
                faces.extend([[ids[0],ids[k],ids[k+1]] for k in range(1,len(ids)-1)])
    verts=np.asarray(vertices);triangles=verts[np.asarray(faces)]
    assert np.isfinite(verts).all()
    assert np.all(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])[:,2]>0)
    (DST/'SM_Benmore_GaeaCreeks.json').write_text(json.dumps({'vertices':vertices,'faces':faces}))
    # World-space direction is only for ripple advection, not simulated velocity.
    gy,gx=np.gradient(gaussian_filter(h,3.0),STEP);speed=np.hypot(gx,gy)
    flow=np.stack([.5-.5*gx/np.maximum(speed,.0001),.5-.5*gy/np.maximum(speed,.0001),np.clip(depth/.20,0,1),np.clip(speed*.5,0,.35)],axis=-1)
    Image.fromarray(np.uint8(np.rint(flow*255))).save(DST/'T_Gaea_Flow.png')
    wear=resample(read_height(OUT/'return/M_Wear.tif')[::-1],N)*edit
    deposits=resample(read_height(OUT/'return/M_Deposits.tif')[::-1],N)*edit
    banks=np.stack([np.clip(dist/16,0,1),np.clip(cover,0,1),np.clip(wear/.025,0,1),np.clip(deposits/.006,0,1)],axis=-1)
    Image.fromarray(np.uint8(np.rint(banks*255))).save(DST/'T_Gaea_Banks.png')
    # Start with pre-river vegetation so the retired channel regrows naturally.
    original=np.asarray(Image.open(OUT.parent/'BenmoreVegetation/T_Benmore_VegetationMask.png'))
    keep=smooth01((dist-2.5)/4.5)
    Image.fromarray(np.uint8(np.rint(original*keep[...,None]))).save(DST/'T_Gaea_VegetationMask.png')
    if water_only:
        manifest=json.loads((DST/'assets.json').read_text())
        manifest.update(vertices=len(vertices),triangles=len(faces),wet_samples=int(wet.sum()),
                        water_depth_range_m=[float(waterdepth[wet].min()),float(waterdepth[wet].max())],
                        edge_filter_sigma_samples=.72,bank_placements_preserved=True)
        (DST/'assets.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));return
    snapshot=json.loads((OUT/'source/placement-snapshot.json').read_text())
    rng=np.random.default_rng(8102026);placements={};counts={}
    for actor in snapshot['actors']:
        name=actor['label']
        if not (name.startswith('Benmore_River_Art_') or name=='Benmore_River_GravelBars'):continue
        tree=name.endswith('trees');rock=name.endswith('rocks') or name.endswith('GravelBars')
        dmin,dmax=(7,19) if tree else ((1.6,8) if rock else (3,15))
        candidates=np.argwhere((dist>dmin)&(dist<dmax)&(edit>.6)&(speed<(.65 if rock else .8))&((h<55) if tree else True))
        assert len(candidates)>10,(name,len(candidates))
        weights=(.2+.8*(.5+.5*np.sin(xx[candidates[:,0],candidates[:,1]]*.031+yy[candidates[:,0],candidates[:,1]]*.017)))**2
        weights/=weights.sum();used=set();rows=[]
        for component in actor['components']:
            transforms=component.get('instances_world_xyz_quat_xyzw_scale',[]);out=[]
            for tr in transforms:
                for attempt in range(120):
                    j,i=candidates[rng.choice(len(candidates),p=weights)]
                    x=float(xx[j,i]+rng.uniform(-.3,.3));y=float(yy[j,i]+rng.uniform(-.3,.3))
                    key=(round(x/(5 if tree else (1.25 if rock else 1.0))),round(y/(5 if tree else (1.25 if rock else 1.0))))
                    if key not in used:used.add(key);break
                else:raise RuntimeError('Bank placement capacity exhausted: '+name)
                out.append({'x_m':x,'y_m':y,'quat_xyzw':tr[3:7],'scale':tr[7:10]})
            rows.append({'mesh':component['mesh'],'materials':component['materials'],'transforms':out})
        placements[name]=rows;counts[name]=sum(len(row['transforms']) for row in rows)
    (DST/'bank-placements.json').write_text(json.dumps(placements,separators=(',',':')))
    # Close and reach views target the same main creek; a long vista gives context.
    targets=[(-705,215),(-408,443)]
    cameras=[]
    for name,(x,y),offset in zip(['Creek_Close','Creek_Reach'],targets,[(8,-13,3.0),(75,-75,38)]):
        j,i=min(np.argwhere(wet),key=lambda ji:(xx[tuple(ji)]-x)**2+(yy[tuple(ji)]-y)**2)
        target=np.array([xx[j,i],yy[j,i],eta[j,i]])
        pos=target+np.array(offset);pos[2]=max(pos[2],float(sample(h,pos[0],pos[1]))+offset[2])
        cameras.append({'name':name,'position_m':pos.tolist(),'target_m':target.tolist(),'fov':72})
    cameras.append({'name':'Long_Vista','position_m':[750,500,float(sample(h,750,500))+1.9],'target_m':[-800,350,25],'fov':82})
    manifest={'ok':True,'height_sha256':sha(OUT/'candidate/H_Benmore_Gaea_2017.r16'),
              'source_map_sha256':json.loads((OUT/'package-manifest.json').read_text())['source_map_sha256'],
              'vertices':len(vertices),'triangles':len(faces),'bank_counts':counts,'cameras':cameras,
              'wet_samples':int(wet.sum()),'water_depth_range_m':[float(waterdepth[wet].min()),float(waterdepth[wet].max())],
              'water_mode':'Terrain-fitted shallow preview, not hydraulic simulation or vehicle water',
              'road_or_fixed_edge_wet_samples':int(np.count_nonzero(wet&(protect==1))),
              'source_return_sha256':{p.name:sha(p) for p in (OUT/'return').glob('*.tif')},
              'outlets':'Water is limited to the protected catchment; lake outlets are not extended in this pass.'}
    assert manifest['road_or_fixed_edge_wet_samples']==0
    (DST/'assets.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--water-only',action='store_true')
    run(parser.parse_args().water_only)
