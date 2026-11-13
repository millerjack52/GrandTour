"""Offline Saint-Venant shallow-water bake over the existing Benmore terrain.

Gravity, free-surface head, wet/dry faces, bed friction and conservative fluxes
and momentum transport are simulated. This graphics authoring model omits sediment,
3D overturning and rainfall hydrology. Input discharge is an art parameter.
Numeric maps are simulation data; no photographic textures are generated.
"""
from pathlib import Path
import sys, json, hashlib, heapq, time, argparse
import numpy as np
import rasterio as rio
from rasterio.windows import from_bounds
from scipy.ndimage import map_coordinates, gaussian_filter, gaussian_filter1d, distance_transform_edt, label
from scipy.spatial import cKDTree
from benmore_shallow_water import step_for, check_solver
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from prepare_benmore_composition import height, clearance, HFILE
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreRivers';OUT.mkdir(exist_ok=True)
DX=1.;BOUNDS=(-1570.,-20.,-240.,665.);SOURCE=(-320.,600.);FLOW=6.;LAKE=.60

def terrain(x,y):
    x,y=np.broadcast_arrays(x,y)
    with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
        win=from_bounds(1383300+x.min()-3,5081149+y.min()-3,1383300+x.max()+3,5081149+y.max()+3,src.transform).round_offsets().round_lengths()
        a=src.read(1,window=win);tr=src.window_transform(win)
        j=(5081149+y-tr.f)/tr.e-.5;i=(1383300+x-tr.c)/tr.a-.5
        z=map_coordinates(a,[j.ravel(),i.ravel()],order=1,mode='nearest').reshape(x.shape)-360.531005859375
    return np.where((x>=-1250)&(x<=1250)&(y>=-1250)&(y<=1250),height(x,y),z)

def drainage(bed,xx,yy):
    ny,nx=bed.shape;seen=np.zeros(bed.shape,bool);rec=np.full(bed.size,-1,np.int32);queue=[]
    for j,i in np.argwhere((bed<LAKE)|(xx==xx.min())|(xx==xx.max())|(yy==yy.min())|(yy==yy.max())):
        seen[j,i]=True;heapq.heappush(queue,(float(bed[j,i]),int(j),int(i)))
    while queue:
        z,j,i=heapq.heappop(queue)
        for dj,di in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            v,w=j+dj,i+di
            if not(0<=v<ny and 0<=w<nx) or seen[v,w]:continue
            seen[v,w]=True;rec[v*nx+w]=j*nx+i
            heapq.heappush(queue,(max(z+.00001,float(bed[v,w])),v,w))
    k=np.argmin((xx-SOURCE[0])**2+(yy-SOURCE[1])**2);path=[]
    while k>=0:
        j,i=divmod(int(k),nx);path.append([xx[j,i],yy[j,i],bed[j,i]])
        if bed[j,i]<LAKE:break
        k=rec[k]
    assert path[-1][2]<LAKE,('Drainage did not reach lake',path[-1])
    return np.array(path)

def run(seconds=2480,resume=False):
    checks=check_solver();x=np.arange(BOUNDS[0],BOUNDS[2]+DX/2,DX);y=np.arange(BOUNDS[1],BOUNDS[3]+DX/2,DX);xx,yy=np.meshgrid(x,y)
    base=terrain(xx,yy);path=drainage(base[::4,::4],xx[::4,::4],yy[::4,::4])
    path[:,:2]=gaussian_filter1d(path[:,:2],1.5,axis=0,mode='nearest');path[0,:2]=SOURCE
    path[:,2]=terrain(path[:,0],path[:,1])
    dist,nearest=cKDTree(path[:,:2]).query(np.c_[xx.ravel(),yy.ravel()]);dist=dist.reshape(base.shape);nearest=nearest.reshape(base.shape)
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path[:,:2],axis=0),axis=1))]
    width=4.8+1.0*np.sin(arc[nearest]/43)+.5*np.sin(arc[nearest]/17)
    smooth=lambda v:np.clip(v,0,1)**2*(3-2*np.clip(v,0,1))
    rim=smooth((dist-width+1)/3.0)*(1-smooth((dist-width-2)/7.0))
    mouth_fade=smooth((arc[-1]-arc[nearest]-12)/65)
    source_fade=smooth((arc[nearest]+5)/12)
    bank_delta=np.maximum(0,path[nearest,2]+1.65-base)*rim*mouth_fade*source_fade
    # Trim dry crowns against the accepted waterline. A blanket reduction caused
    # overflow across the alluvial fan; the wet bed and necessary containment stay.
    crown_file=OUT/'bank-crown-reference.npz'
    if crown_file.exists():
        crown=np.load(crown_file)
        assert np.array_equal(crown['x'],x) and np.array_equal(crown['y'],y)
        low=np.maximum(0,path[nearest,2]+.78+.16*np.sin(arc[nearest]/49)-base)*rim*mouth_fade*source_fade
        bank_delta=np.minimum(bank_delta,np.maximum(low,crown['minimum_fill']))
    bed=base+bank_delta
    radius=np.where(arc[nearest]>arc[-1]-160,110.,45.)
    active=(dist<radius)|((bed<LAKE)&(xx<-1320)&(yy<200));ids=np.full(bed.shape,-1,np.int32);ids[active]=np.arange(active.sum())
    a=[];b=[];axes=[]
    for axis,(s,t) in enumerate([(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]):
        m=(s>=0)&(t>=0);a.extend(s[m]);b.extend(t[m]);axes.extend([axis]*int(m.sum()))
    a=np.array(a,np.int32);b=np.array(b,np.int32);axes=np.array(axes);z=bed[active].astype(np.float64)
    source=np.flatnonzero(((xx[active]-SOURCE[0])**2+(yy[active]-SOURCE[1])**2)<3**2)
    weights=np.exp(-(z[source]-z[source].min())*8);weights/=weights.sum()
    reservoir=np.flatnonzero((bed[active]<LAKE)&(xx[active]<-1390)).astype(np.int64)
    assert len(reservoir)>30
    h=np.maximum(0,LAKE-z);hu=np.zeros(len(z));hv=np.zeros(len(z));simtime=0.;mass0=h.sum()*DX*DX;totalin=0.;totalout=0.;steps=0
    if resume:
        state=np.load(OUT/'solver_banked_state.npz')
        old_indices=state['cell_indices'] if 'cell_indices' in state else np.flatnonzero((dist<45)|((bed<LAKE)&(xx<-1320)&(yy<200)))
        new_indices=np.flatnonzero(active);assert np.all(np.isin(old_indices,new_indices))
        dest=np.searchsorted(new_indices,old_indices);assert np.max(abs(state['bed']-z[dest]))<1e-9
        initial_extra=float(h.sum()-h[dest].sum())*DX*DX
        h[dest]=state['h'];hu[dest]=state['hu'];hv[dest]=state['hv'];simtime=float(state['time']);mass0=float(state['mass0'])+initial_extra;totalin=float(state['totalin']);totalout=float(state['totalout']);steps=int(state['steps'])
    history=[];start=time.monotonic();previous=h.copy();mean_h=np.zeros_like(h);mean_vx=h.copy()*0;mean_vy=h.copy()*0;samples=0
    while simtime<seconds:
        length=min(40.,seconds-simtime)
        added,removed,count,dt,negative=step_for(z,h,hu,hv,a,b,axes,DX,source,weights,FLOW,reservoir,LAKE,length,.045)
        assert negative<1e-8
        simtime+=length;totalin+=added;totalout+=removed;steps+=count
        err=h.sum()*DX*DX-mass0-totalin-totalout
        vx=hu/np.maximum(h,.005);vy=hv/np.maximum(h,.005);wet=(h>.06)&(z>LAKE)
        delta=float(np.max(np.abs(h-previous)));previous[:]=h
        row=dict(time_s=simtime,wet_cells=int(wet.sum()),max_depth_m=float(h[wet].max()),depth_change_40s_m=delta,outflow_m3s=-removed/length,mass_error_m3=float(err),elapsed_wall_s=round(time.monotonic()-start,1))
        history.append(row);print(json.dumps(row),flush=True)
        if simtime>seconds-120:mean_h+=h;mean_vx+=vx;mean_vy+=vy;samples+=1
    np.savez_compressed(OUT/'solver_banked_state.npz',cell_indices=np.flatnonzero(active),bed=z,h=h,hu=hu,hv=hv,time=simtime,mass0=mass0,totalin=totalin,totalout=totalout,steps=steps)
    h=mean_h/samples;vx=mean_vx/samples;vy=mean_vy/samples
    depth=np.zeros_like(bed);depth[active]=h
    vxx=np.zeros_like(bed);vyy=np.zeros_like(bed);vxx[active]=vx;vyy[active]=vy
    surface=bed+depth
    wet=(depth>.025)&(bed>LAKE-.02)
    labels,n=label(wet,structure=np.ones((3,3)));near_source=((xx-SOURCE[0])**2+(yy-SOURCE[1])**2)<36
    candidates=labels[near_source&wet];assert len(candidates)>0
    sizes=np.bincount(labels.ravel());source_label=max(set(candidates),key=lambda k:sizes[k])
    assert source_label>0
    connected=labels==source_label
    # Include the connected mouth's underwater skirt, where it meets the lake.
    connected|=(distance_transform_edt(~connected)<8)&(bed<LAKE+.08)
    plot(xx,yy,bed,depth,np.hypot(vxx,vyy),wet,path)
    assert np.any(connected&(bed<LAKE+.02)), 'River has not filled all the way to the lake'
    edgewet=wet&(dist>radius-3)&(bed>LAKE+.2)
    assert edgewet.sum()==0,('Wetted artificial corridor wall',int(edgewet.sum()))
    assert np.isfinite(depth).all() and np.isfinite(vxx).all()
    assert abs(err)<.0001*max(totalin,1)
    assert abs(history[-1]['outflow_m3s']-FLOW)/FLOW<.03, 'Continue settling until discharge balances'
    assert history[-1]['depth_change_40s_m']<.01, 'Continue settling until depth changes are below one centimetre per forty seconds'
    speed=np.hypot(vxx,vyy);froude=speed/np.sqrt(9.81*np.maximum(depth,.03))
    strain=np.hypot(np.gradient(vxx,axis=1),np.gradient(vyy,axis=0))/DX
    foam=np.clip((froude-.65)*.32+np.maximum(0,strain-.20)*.14,0,.65)
    foam*=np.clip(depth/.14,0,1);foam=gaussian_filter(foam,.65)
    # Shore distance is used for gravel/vegetation blending in world space.
    shore=distance_transform_edt(~connected)*DX
    flow=np.stack((np.clip(vxx/12+.5,0,1),np.clip(vyy/12+.5,0,1),np.clip(depth/4,0,1),foam),axis=-1)
    Image.fromarray(np.uint8(np.round(flow*255))).save(OUT/'T_Benmore_RiverFlow.png')
    ecology=np.stack((np.clip(shore/16,0,1),connected.astype(float),np.clip(depth,0,1),np.clip(speed/6,0,1)),axis=-1)
    Image.fromarray(np.uint8(np.round(ecology*255))).save(OUT/'T_Benmore_RiverBanks.png')
    np.savez_compressed(OUT/'river_bake.npz',x=x,y=y,base=base,bank_delta=bank_delta,bed=bed,surface=surface,depth=depth,vx=vxx,vy=vyy,foam=foam,wet=connected,shore=shore,path=path)
    checks['min_road_clearance_m']=min(clearance(float(px),float(py)) for px,py in zip(xx[connected][::20],yy[connected][::20]))
    assert checks['min_road_clearance_m']>35
    checks.update(mass_error_m3=float(err),final_outflow_m3s=history[-1]['outflow_m3s'],final_depth_change_40s_m=history[-1]['depth_change_40s_m'],corridor_edge_wet_cells=int(edgewet.sum()),river_connected_to_lake=True,finite=True)
    report=dict(ok=True,method='2D Saint-Venant shallow water; Rusanov finite volumes, hydrostatic reconstruction, Manning friction; no erosion',bounds_m=BOUNDS,cell_m=DX,active_cells=int(active.sum()),simulated_seconds=simtime,steps=steps,inflow_m3s=FLOW,lake_level_m=LAKE,source_m=SOURCE,path_length_m=float(np.linalg.norm(np.diff(path[:,:2],axis=0),axis=1).sum()),wet_area_m2=float(connected.sum()*DX*DX),
        depth_percentiles_m=np.percentile(depth[connected],[10,50,90,99]).tolist(),speed_percentiles_mps=np.percentile(speed[connected],[10,50,90,99]).tolist(),history=history,validation=checks,
        height_sha256=hashlib.sha256(HFILE.read_bytes()).hexdigest(),terrain_modified=False,authored_bank_geometry=True,maximum_bank_fill_m=float(bank_delta.max()),flow_encoding='RG = world XY velocity / 12 + 0.5; B = depth metres / 4; A = procedural foam potential; linear data, row zero south',runtime_simulation=False,vehicle_interaction=False)
    (OUT/'bake-report.json').write_text(json.dumps(report,indent=2));plot(xx,yy,bed,depth,speed,connected,path)
    print('BENMORE_RIVER_BAKE_OK',flush=True)

def plot(xx,yy,bed,depth,speed,wet,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(15,12))
    for ax,data,title in [(axes[0],depth,'Baked depth (m)'),(axes[1],speed,'Baked current speed (m/s)')]:
        ax.contour(xx,yy,bed,levels=np.arange(0,120,4),colors='#b0a492',linewidths=.4)
        im=ax.pcolormesh(xx,yy,np.where(wet,data,np.nan),cmap='viridis',shading='nearest');fig.colorbar(im,ax=ax)
        ax.plot(*SOURCE,'r*');ax.set(aspect='equal',xlabel='East (m)',ylabel='North (m)',title=title)
    fig.tight_layout();fig.savefig(OUT/'Simulation_Review.png',dpi=130)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=2480);p.add_argument('--resume',action='store_true');args=p.parse_args();run(args.seconds,args.resume)
