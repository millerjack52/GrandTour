"""Bake the existing conservative solver over the approved Gaea Landscape.

Discharge is authored, not surveyed. A shallow native bed incision is baked;
no sediment or runtime fluid simulation. Coordinates: metres, south-up arrays.
"""
from pathlib import Path
import argparse,json,time,hashlib
from collections import deque
import heapq
import numpy as np
from numba import njit
from scipy.ndimage import map_coordinates,distance_transform_edt,label,gaussian_filter,gaussian_filter1d
from scipy.spatial import cKDTree
from PIL import Image
import bake_benmore_river as old
from benmore_shallow_water import step_for,check_solver

ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'RiverLife'
DX=1.25;BOUNDS=(-1480.,-300.,-220.,775.);LAKE=.60
SOURCES=[(-350.94246,709.3254,.36),(-394.3452,689.4841,.22),(-282.7381,710.5655,.22)]
H=np.fromfile(BASE/'candidate/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)

@njit(cache=True)
def spill_levels(bed,lake):
    """Priority-flood spill elevation for a wet initial condition in real basins."""
    ny,nx=bed.shape;seen=np.zeros((ny,nx),np.bool_);filled=bed.copy();queue=[(0.,0)]
    queue.pop()
    for j in range(ny):
        for i in range(nx):
            if j==0 or i==0 or j==ny-1 or i==nx-1 or bed[j,i]<lake:
                seen[j,i]=True;filled[j,i]=max(bed[j,i],lake);heapq.heappush(queue,(filled[j,i],j*nx+i))
    while queue:
        level,k=heapq.heappop(queue);j=k//nx;i=k%nx
        for dj,di in ((-1,0),(1,0),(0,-1),(0,1)):
            v=j+dj;w=i+di
            if 0<=v<ny and 0<=w<nx and not seen[v,w]:
                seen[v,w]=True;filled[v,w]=max(bed[v,w],level);heapq.heappush(queue,(filled[v,w],v*nx+w))
    return filled

def terrain(x,y):
    x,y=np.broadcast_arrays(x,y);outside=(x<-1250)|(x>1250)|(y<-1250)|(y>1250)
    fx=np.clip((x+1250)/2500*2016,0,2015.999999);fy=np.clip((y+1250)/2500*2016,0,2015.999999)
    i=fx.astype(int);j=fy.astype(int);s=fx-i;t=fy-j;q=H[j,i];r=H[j,i+1];v=H[j+1,i];w=H[j+1,i+1]
    z=np.where(s>=t,q+(r-q)*s+(w-r)*t,q+(w-v)*s+(v-q)*t)
    if outside.any():z[outside]=old.terrain(x[outside],y[outside])
    return z

def sample(a,x,y):
    return map_coordinates(a,[(np.asarray(y)-BOUNDS[1])/DX,(np.asarray(x)-BOUNDS[0])/DX],order=1,mode='nearest')

def run(seconds,resume,prime=False):
    global H
    OUT.mkdir(parents=True,exist_ok=True)
    x=np.arange(BOUNDS[0],BOUNDS[2]+DX/2,DX);y=np.arange(BOUNDS[1],BOUNDS[3]+DX/2,DX);xx,yy=np.meshgrid(x,y)
    bed=terrain(xx,yy)
    if resume and (OUT/'H_RiverLife_2017.r16').exists():
        H=np.fromfile(OUT/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    else:
        # The protected Gaea blend left a shallow runoff sheet rather than a bed.
        # Incise only its natural drainage, using the native Landscape heightfield.
        paths=[]
        for sx,sy,q in SOURCES:
            old.SOURCE=(sx,sy)
            line=old.drainage(bed[::3,::3],xx[::3,::3],yy[::3,::3])
            line[:,:2]=gaussian_filter1d(line[:,:2],1.15,axis=0,mode='nearest')
            line[:,2]=terrain(line[:,0],line[:,1]);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(line[:,:2],axis=0),axis=1))]
            profile=np.minimum.accumulate(line[:,2]-.48-.12*(.5+.5*np.sin(arc/37)))
            paths.append(np.c_[line[:,:2],profile])
        channels=np.concatenate(paths);tree=cKDTree(channels[:,:2])
        yyh,xxh=np.meshgrid(np.linspace(-1250,1250,2017),np.linspace(-1250,1250,2017),indexing='ij')
        distance,near=tree.query(np.c_[xxh.ravel(),yyh.ravel()]);distance=distance.reshape(H.shape);near=near.reshape(H.shape)
        smooth=lambda v:np.clip(v,0,1)**2*(3-2*np.clip(v,0,1))
        width=3.6+.6*np.sin(xxh*.023+yyh*.013)
        strength=1-smooth((distance-.7)/(width-.7))
        # Roads and shoreline remain protected; the cut fades well before the edge.
        roadprotect=np.load(BASE/'source/protect_2017.npy')
        strength*=1-roadprotect
        delta=np.minimum(np.maximum(H-channels[near,2],0),1.25)*strength
        packed=np.uint16(np.rint(np.clip((H-delta)*64+32768,0,65535)))
        H=(packed.astype(np.float32)-32768)/64
        (OUT/'H_RiverLife_2017.r16').write_bytes(packed.astype('<u2').tobytes());H.astype('<f4').tofile(OUT/'height_local_south_up.f32')
        rgb=np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],axis=-1).astype(np.uint8)
        Image.fromarray(rgb).save(OUT/'T_RL_HeightRG.png')
        (OUT/'channel-edit.json').write_text(json.dumps({'native_landscape':True,'maximum_cut_m':float(delta.max()),'edited_samples':int(np.count_nonzero(delta>.008)),'raised_banks':False,'roads_protected':True,'original_height_sha256':hashlib.sha256((BASE/'candidate/H_Benmore_Gaea_2017.r16').read_bytes()).hexdigest(),'height_sha256':hashlib.sha256((OUT/'H_RiverLife_2017.r16').read_bytes()).hexdigest()},indent=2))
    bed=terrain(xx,yy)
    gaea=np.asarray(Image.open(BASE/'integration/T_Gaea_Banks.png'))[:,:,1]/255
    coverage=map_coordinates(gaea,[(yy+1250)/2500*2016,(xx+1250)/2500*2016],order=1,mode='constant')
    # The approved mask identifies the valley; only terrain governs the solve.
    dist=distance_transform_edt(coverage<.22)*DX
    old.SOURCE=SOURCES[0][:2]
    path=old.drainage(bed[::3,::3],xx[::3,::3],yy[::3,::3])
    pd=cKDTree(path[:,:2]).query(np.c_[xx.ravel(),yy.ravel()])[0].reshape(xx.shape)
    corridor=np.minimum(dist,pd)
    radius=np.where(xx<-850,400.,100.)
    active=(corridor<radius)|((xx<-1280)&(bed<LAKE+.3))
    ids=np.full(bed.shape,-1,np.int32);ids[active]=np.arange(active.sum())
    aa=[];bb=[];axes=[]
    for axis,(s,t) in enumerate([(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]):
        ok=(s>=0)&(t>=0);aa.extend(s[ok]);bb.extend(t[ok]);axes.extend([axis]*int(ok.sum()))
    a=np.array(aa,np.int32);b=np.array(bb,np.int32);axes=np.array(axes);z=bed[active].astype(float)
    src=[];weights=[];flow=sum(s[2] for s in SOURCES)
    for sx,sy,q in SOURCES:
        near=np.flatnonzero((xx[active]-sx)**2+(yy[active]-sy)**2<2.5**2)
        assert len(near)>0
        w=np.exp(-(z[near]-z[near].min())*10);w*=q/flow/w.sum();src.extend(near);weights.extend(w)
    src=np.array(src,np.int64);weights=np.array(weights)
    reservoir=np.flatnonzero((xx[active]<-1400)&(z<LAKE)).astype(np.int64);assert len(reservoir)>25
    h=np.maximum(0,LAKE-z);hu=h*0;hv=h*0;t=0.;totalin=0.;totalout=0.;mass0=h.sum()*DX*DX;steps=0
    statefile=OUT/'flow-state.npz'
    if resume and statefile.exists():
        st=np.load(statefile)
        old_indices=st['cell_indices'] if 'cell_indices' in st else np.flatnonzero(np.load(OUT/'flow-bake.npz')['active'])
        prior=np.load(OUT/'flow-bake.npz');px=st['x'] if 'x' in st else prior['x'];py=st['y'] if 'y' in st else prior['y']
        oj,oi=np.divmod(old_indices,len(px));mapped=np.rint((py[oj]-y[0])/DX).astype(int)*len(x)+np.rint((px[oi]-x[0])/DX).astype(int)
        old_indices=mapped;new_indices=np.flatnonzero(active);dest=np.searchsorted(new_indices,old_indices)
        assert np.array_equal(new_indices[dest],old_indices) and np.array_equal(st['bed'],z[dest])
        extra=float(h.sum()-h[dest].sum())*DX*DX
        h[dest]=st['h'];hu[dest]=st['hu'];hv[dest]=st['hv'];t=float(st['time']);totalin=float(st['totalin']);totalout=float(st['totalout']);mass0=float(st['mass0'])+extra;steps=int(st['steps'])
    initial_added=0.
    if prime:
        pools=np.maximum(spill_levels(bed,LAKE)-bed,0)[active]
        # Only already wetted basins; do not introduce unrelated hilltop ponds.
        target=np.where(h>.003,np.maximum(h,pools),h);initial_added=float((target-h).sum()*DX*DX)
        h=target;mass0+=initial_added
        print('Initial pond storage added at natural spill levels: '+str(initial_added)+' m3',flush=True)
    checks=check_solver();history=[];previous=h.copy();start=time.monotonic();mean_h=h*0;mean_u=h*0;mean_v=h*0;samples=0
    stability=deque([(t,h.copy(),hu/np.maximum(h,.003),hv/np.maximum(h,.003))],maxlen=6)
    while t<seconds:
        duration=min(40,seconds-t)
        added,removed,count,dt,negative=step_for(z,h,hu,hv,a,b,axes,DX,src,weights,flow,reservoir,LAKE,duration,.055)
        assert negative<1e-7,negative
        t+=duration;totalin+=added;totalout+=removed;steps+=count
        error=h.sum()*DX*DX-mass0-totalin-totalout;delta=float(np.max(abs(h-previous)));previous[:]=h
        row=dict(time_s=t,outflow_m3s=-removed/duration,depth_change_m=delta,mass_error_m3=float(error),wall_s=round(time.monotonic()-start,1))
        history.append(row);print(json.dumps(row),flush=True)
        stability.append((t,h.copy(),hu/np.maximum(h,.003),hv/np.maximum(h,.003)))
        if t>=seconds-120:mean_h+=h;mean_u+=hu/np.maximum(h,.003);mean_v+=hv/np.maximum(h,.003);samples+=1
        if int(t)%200==0 or t>=seconds:
            np.savez_compressed(statefile,x=x,y=y,cell_indices=np.flatnonzero(active),bed=z,h=h,hu=hu,hv=hv,time=t,totalin=totalin,totalout=totalout,mass0=mass0,steps=steps)
            (OUT/'flow-progress.json').write_text(json.dumps(row,indent=2))
    depth=np.zeros_like(bed);vx=depth.copy();vy=depth.copy()
    depth[active]=mean_h/samples;vx[active]=mean_u/samples;vy[active]=mean_v/samples
    wet=(depth>.028)&(bed>LAKE-.20)
    labels,n=label(wet,np.ones((3,3)));lids=set()
    for sx,sy,q in SOURCES:
        near=(xx-sx)**2+(yy-sy)**2<36;lids.update(labels[near&wet].tolist())
    lids.discard(0);wet=np.isin(labels,list(lids))
    wet|=(distance_transform_edt(~wet)*DX<3)&(bed<LAKE+.08)&(depth>.028)
    edge=(corridor>radius-4)&(bed>LAKE+.20)&(depth>.05)
    speed=np.hypot(vx,vy);froude=speed/np.sqrt(9.81*np.maximum(depth,.03))
    strain=np.hypot(np.gradient(vx,DX,axis=1),np.gradient(vy,DX,axis=0))
    foam=np.clip((froude-.7)*.15+np.maximum(strain-.18,0)*.08,0,.35)*np.clip(depth/.09,0,1)
    foam=gaussian_filter(foam,.55)
    routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
    roadclear=min(float((cKDTree([[p['x_m'],p['y_m']] for p in r['points']]).query(np.c_[xx[wet],yy[wet]])[0]-r['width_m']/2-1.1).min()) for r in routes)
    checks.update(mass_error_m3=float(error),outflow_m3s=history[-1]['outflow_m3s'],depth_change_m=history[-1]['depth_change_m'],artificial_edge_wet_cells=int(edge.sum()),connected_to_lake=bool(np.any(wet&(bed<LAKE+.05))),road_edge_clearance_m=roadclear)
    converged=abs(checks['outflow_m3s']-flow)/flow<.035 and checks['depth_change_m']<.015
    # A static art bake can use a stable transient: the broad non-playable
    # outlet basin continues filling slowly. Preserve global convergence as a
    # separate result; validate actual depth AND velocity drift over 200 s.
    t0,h0,u0,v0=stability[0];window=t-t0
    rendered=(h>.028)&(h0>.028)
    changing_depth=float(np.max(np.abs(h-h0)[rendered]))
    visible=(h>.055)&(h0>.055)
    changing_speed=float(np.max(np.hypot(hu/np.maximum(h,.003)-u0,hv/np.maximum(h,.003)-v0)[visible]))
    stable_transient=window>=199.9 and changing_depth<.003 and changing_speed<.01
    checks.update(stability_window_s=window,max_visible_depth_drift_m=changing_depth,max_all_depth_drift_m=float(np.max(np.abs(h-h0))),max_visible_velocity_drift_mps=changing_speed,storage_rate_m3s=float((h-h0).sum()*DX*DX/max(window,1)),stable_visual_bake=bool(stable_transient))
    ok=(converged or stable_transient) and abs(error)<1e-5*max(totalin,1) and edge.sum()==0 and checks['connected_to_lake'] and roadclear>12
    report=dict(ok=bool(ok),converged=bool(converged),method='Existing conservative 2D shallow-water solver on Gaea terrain with a shallow native riverbed incision',sources=SOURCES,total_inflow_m3s=flow,grid_m=DX,active_cells=int(active.sum()),simulated_seconds=t,steps=steps,validation=checks,depth_percentiles_m=np.percentile(depth[wet],[10,50,90,99]).tolist(),speed_percentiles_mps=np.percentile(speed[wet],[10,50,90,99]).tolist(),wet_area_m2=float(wet.sum()*DX*DX),terrain_changed=True,runtime_simulation=False,vehicle_water_coupling=False,height_sha256=hashlib.sha256((OUT/'H_RiverLife_2017.r16').read_bytes()).hexdigest(),history=history)
    report['initial_pond_storage_added_m3']=initial_added
    np.savez_compressed(OUT/'flow-bake.npz',x=x,y=y,bed=bed,depth=depth,surface=bed+depth,vx=vx,vy=vy,foam=foam,wet=wet,active=active,coverage=coverage)
    (OUT/'flow-report.json').write_text(json.dumps(report,indent=2));plot(xx,yy,bed,depth,speed,wet)
    print('FLOW_BAKE_OK' if ok else 'FLOW_BAKE_NEEDS_REVIEW',flush=True)

def plot(xx,yy,bed,depth,speed,wet):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(16,8),layout='constrained')
    for ax,z,title in [(axs[0],depth,'Water depth (m)'),(axs[1],speed,'Flow speed (m/s)')]:
        ax.contour(xx,yy,bed,levels=np.arange(0,140,5),colors='#b7af9c',linewidths=.3)
        im=ax.pcolormesh(xx,yy,np.where(wet,z,np.nan),shading='nearest',cmap='viridis');fig.colorbar(im,ax=ax)
        ax.set(title=title,aspect='equal',xlabel='X east (m)',ylabel='Y north (m)')
    fig.savefig(OUT/'Flow_Review.png',dpi=120);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=2400);p.add_argument('--resume',action='store_true');p.add_argument('--prime-pools',action='store_true');args=p.parse_args();run(args.seconds,args.resume,args.prime_pools)
