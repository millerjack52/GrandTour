"""Turn the numerical bake into clipped surface meshes and bank placements."""
from pathlib import Path
import sys,json
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter,distance_transform_edt
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from prepare_benmore_composition import height,clearance
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreRivers'

def run():
    d=np.load(OUT/'river_bake.npz');x=d['x'];y=d['y'];xx,yy=np.meshgrid(x,y);wet=d['wet'];depth=d['depth'];bed=d['bed'];surface=d['surface']
    d['shore'].astype('<f4').tofile(OUT/'bank_distance.f32')
    d['bank_delta'].astype('<f4').tofile(OUT/'bank_delta.f32')
    (bed-.018*(1-np.minimum(1,d['bank_delta']/.05))).astype('<f4').tofile(OUT/'bank_surface.f32')
    # Remove sub-metre numerical ripples from the static sheet; animated small
    # waves remain a shader treatment. Clip against the actual DEM, not a box.
    support=gaussian_filter((depth>.025).astype(float),.9)
    eta=gaussian_filter(surface*(depth>.025),.9)/np.maximum(support,1e-10)
    eta=np.where(support>.05,eta,surface)
    eta=np.maximum(bed+.005,eta)
    eta=np.where(bed<.62,np.maximum(.60,eta),eta)
    clipped=np.minimum(eta-bed,depth);clipped=np.where(distance_transform_edt(~wet)<1.5,clipped,0.)
    parts=[];bankparts=[];totalfaces=0
    for chunk in range(6):
        left=x[0]+chunk*240;right=left+240;origin=np.array([left,0.,0.]);vertices=[];faces=[];lookup={}
        def vert(v):
            key=tuple(np.round(v,5))
            if key not in lookup:lookup[key]=len(vertices);vertices.append((v-origin).tolist())
            return lookup[key]
        candidates=np.argwhere((np.maximum.reduce([clipped[:-1,:-1],clipped[1:,:-1],clipped[:-1,1:],clipped[1:,1:]])>.055)&(xx[:-1,:-1]>=left)&(xx[:-1,:-1]<right))
        for j,i in candidates:
            for tri in [[(j,i),(j,i+1),(j+1,i+1)],[(j,i),(j+1,i+1),(j+1,i)]]:
                poly=[(np.array([xx[a,b],yy[a,b],eta[a,b]]),clipped[a,b]-.04) for a,b in tri];out=[]
                for k,(p,h) in enumerate(poly):
                    q,hq=poly[(k+1)%3]
                    if h>=0:out.append(p)
                    if (h>=0)!=(hq>=0):out.append(p+(q-p)*h/(h-hq))
                if len(out)>=3:
                    ids=[vert(v) for v in out]
                    for k in range(1,len(ids)-1):faces.append([ids[0],ids[k],ids[k+1]])
        if not faces:continue
        name='SM_Benmore_River_'+str(chunk).zfill(2)
        (OUT/(name+'.json')).write_text(json.dumps(dict(vertices=vertices,faces=faces)))
        parts.append(dict(name=name,origin_m=origin.tolist(),vertices=len(vertices),triangles=len(faces)));totalfaces+=len(faces)
        # The banks are separate collision geometry resting on the unchanged
        # landscape. Their heights are the exact bed used by the simulation.
        bank=d['bank_delta'];vertices=[];faces=[];lookup={}
        candidates=np.argwhere((np.maximum.reduce([bank[:-1,:-1],bank[1:,:-1],bank[:-1,1:],bank[1:,1:]])>.008)&(xx[:-1,:-1]>=left)&(xx[:-1,:-1]<right))
        for j,i in candidates:
            ids=[]
            for a,b in [(j,i),(j,i+1),(j+1,i+1),(j+1,i)]:
                z=bed[a,b]-.018*(1-min(1,bank[a,b]/.05))
                ids.append(vert(np.array([xx[a,b],yy[a,b],z])))
            faces.extend([[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]])
        name='SM_Benmore_RiverBank_'+str(chunk).zfill(2)
        (OUT/(name+'.json')).write_text(json.dumps(dict(vertices=vertices,faces=faces)))
        bankparts.append(dict(name=name,origin_m=origin.tolist(),vertices=len(vertices),triangles=len(faces)))
    # River-local replacement of the existing numeric grass density map.
    old=np.array(Image.open(ROOT/'Art/Export/BenmoreVegetation/T_Benmore_VegetationMask.png'))
    a=np.linspace(-1250,1250,2017);gx,gy=np.meshgrid(a,a)
    shore=map_coordinates(d['shore'],[gy-y[0],gx-x[0]],order=1,mode='constant',cval=100)
    keep=np.clip((shore-7)/5.,0,1)
    new=np.uint8(np.round(old*keep[...,None]));Image.fromarray(new).save(OUT/'T_Benmore_VegetationMask.png')
    assert np.all(new[shore>12]==old[shore>12])
    # Reuse sourced gravel meshes; varied grouped bars rather than uniform dots.
    rng=np.random.default_rng(81026);stones=[]
    cells=np.argwhere((d['shore']>.7)&(d['shore']<7.5)&(xx>-1235)&(xx<-340)&(bed>.9))
    rng.shuffle(cells);used=set()
    for j,i in cells:
        px=float(x[i]+rng.uniform(-.4,.4));py=float(y[j]+rng.uniform(-.4,.4));key=(round(px/1.4),round(py/1.4))
        if key in used or clearance(px,py)<40:continue
        patch=.5+.5*np.sin(px*.037+py*.049)*np.cos(py*.091)
        if rng.random()>patch*.66:continue
        used.add(key);stones.append(dict(x=px,y=py,z=float(height(px,py)),size_m=float(rng.uniform(.17,.55)),yaw=float(rng.uniform(0,360)),kind=int(rng.integers(1,5))))
        if len(stones)>=1700:break
    samples=[]
    for j,i in np.argwhere(wet&(xx>-1220)&(xx<-335))[::120]:samples.append([float(x[i]),float(y[j]),float(d['base'][j,i]),float(eta[j,i])])
    path=d['path'];k=int(np.argmin(abs(path[:,0]+720)));target=path[max(0,k-12)];at=path[k];direction=(target[:2]-at[:2]);direction/=np.linalg.norm(direction)
    close=at[:2]+np.array([-direction[1],direction[0]])*11-direction*12
    close_z=float(height(*close))+float(map_coordinates(d['bank_delta'],[[close[1]-y[0]],[close[0]-x[0]]],order=1)[0])+3.2
    delta=target-np.r_[close,close_z];yaw=float(np.degrees(np.arctan2(delta[1],delta[0])));pitch=float(np.degrees(np.arctan2(delta[2],np.linalg.norm(delta[:2]))))
    cameras=[dict(name='Close',position_m=[*close,close_z],yaw=yaw,pitch=pitch),dict(name='Reach',position_m=[-610,310,float(height(-610,310))+27],yaw=-155,pitch=-19)]
    report=dict(parts=parts,bank_parts=bankparts,triangles=totalfaces,stones=stones,cameras=cameras,support_samples_m=samples,vegetation_pixels_changed=int(np.any(new!=old,axis=-1).sum()),bank_blend_m=12.,grass_clear_m=7.,grass_fade_end_m=12.)
    (OUT/'assets.json').write_text(json.dumps(report,indent=2));print({k:len(v) if isinstance(v,list) else v for k,v in report.items()})

if __name__=='__main__':run()
