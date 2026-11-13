"""Replace point-stamp incision with a continuous native channel, then rebake.

Coordinates are metres, south-up. No runtime solver or vehicle settings change.
The existing profile/depth target is retained; only its spatial interpolation
changes. Roads and the ford/approaches retain their installed height samples.
"""
from pathlib import Path
import argparse, hashlib, json, time
from collections import deque
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d, map_coordinates, label, distance_transform_edt, gaussian_filter, binary_erosion
from PIL import Image
import bake_benmore_river_life as life
from benmore_shallow_water import step_for, check_solver

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea'; OUT=BASE/'ChannelShape'
DX=life.DX; N=2017

def smooth(v):
    v=np.clip(v,0,1); return v*v*(3-2*v)

def native(h,x,y):
    x,y=np.broadcast_arrays(x,y)
    fx=np.clip((x+1250)*2016/2500,0,2015.999999); fy=np.clip((y+1250)*2016/2500,0,2015.999999)
    i=fx.astype(int); j=fy.astype(int); s=fx-i; t=fy-j
    q,r,v,w=h[j,i],h[j,i+1],h[j+1,i],h[j+1,i+1]
    return np.where(s>=t,q+(r-q)*s+(w-r)*t,q+(w-v)*s+(v-q)*t)

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    base=np.fromfile(BASE/'candidate/height_local_south_up.f32',dtype='<f4').reshape(N,N)
    before=np.fromfile(BASE/'RiverLife/height_local_south_up.f32',dtype='<f4').reshape(N,N)
    x=np.arange(life.BOUNDS[0],life.BOUNDS[2]+DX/2,DX);y=np.arange(life.BOUNDS[1],life.BOUNDS[3]+DX/2,DX)
    xx,yy=np.meshgrid(x,y);life.H=base; bed=life.terrain(xx,yy)
    recovered=np.load(OUT/'original-paths.npz')
    paths=[recovered[k] for k in recovered.files]; starts=[]; ends=[]; arcs=[]
    for p in paths:
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
        starts.extend(p[:-1]);ends.extend(p[1:]);arcs.extend(arc[:-1])
    channels=np.concatenate(paths);a=np.array(starts); b=np.array(ends); arc=np.array(arcs)
    vec=b[:,:2]-a[:,:2]; length2=np.einsum('ij,ij->i',vec,vec)
    assert length2.min()>0
    yh,xh=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N),indexing='ij')
    xy=np.c_[xh.ravel(),yh.ravel()];dist,near=cKDTree(channels[:,:2]).query(xy)
    width=3.6+.6*np.sin(xh*.023+yh*.013)
    protect=np.load(BASE/'source/protect_2017.npy')
    oldstrength=(1-smooth((dist.reshape(base.shape)-.7)/(width-.7)))*(1-protect)
    olddelta=np.minimum(np.maximum(base-channels[near,2].reshape(base.shape),0),1.25)*oldstrength
    reconstructed=np.uint16(np.rint(np.clip((base-olddelta)*64+32768,0,65535)))
    original=np.fromfile(BASE/'RiverLife/H_RiverLife_2017.r16',dtype='<u2').reshape(N,N)
    mismatch=int(np.count_nonzero(reconstructed!=original))
    print(json.dumps({'reconstruction_mismatch':mismatch,'maximum_reconstruction_error_m':float(abs(reconstructed.astype(float)-original).max()/64)}),flush=True)
    assert mismatch==0,'Input differs from original native incision'
    # Only nearby native samples require projection. Eight nearby segment midpoints
    # cover the drainage grid's short segments, including tributary junctions.
    selected=np.flatnonzero(dist<10)
    tree=cKDTree((a[:,:2]+b[:,:2])/2);p=xy[selected]
    _,ids=tree.query(p,k=8)
    d=p[:,None,:]-a[ids,:2]
    f=np.clip(np.einsum('nki,nki->nk',d,vec[ids])/length2[ids],0,1)
    residual=d-f[:,:,None]*vec[ids]
    dd=np.einsum('nki,nki->nk',residual,residual)
    choice=dd.argmin(1);r=np.arange(len(p));seg=ids[r,choice];fraction=f[r,choice]
    distance=np.sqrt(dd[r,choice]);target=a[seg,2]+fraction*(b[seg,2]-a[seg,2])
    strength=(1-smooth((distance-.7)/(width.ravel()[selected]-.7)))*(1-protect.ravel()[selected])
    cut_cap=float((base-before).max())
    delta=np.zeros(base.size);delta[selected]=np.minimum(np.maximum(base.ravel()[selected]-target,0),cut_cap)*strength
    proposed=base-delta.reshape(base.shape)
    # Keep the crossing and its authored walk/drive approaches exactly as installed.
    path=np.fromfile(BASE/'RiverLife/path_mask.f32',dtype='<f4').reshape(N,N)
    blend=1-smooth(path/.02); fixed=path>=.02
    crossings=json.loads((BASE/'RiverLife/assets.json').read_text())['crossings']
    for crossing in crossings:
        p=np.array(crossing['center_m'][:2]);flow=np.array(crossing['flow_direction']);cross=np.array(crossing['cross_direction'])
        along=abs((xh-p[0])*flow[0]+(yh-p[1])*flow[1])
        across=abs((xh-p[0])*cross[0]+(yh-p[1])*cross[1])
        # Preserve a strip across the actual crossing, not a circular patch of
        # river. A wide protected disk would retain the very scallops being fixed.
        keep=(1-smooth((along-1.8)/3.2))*(1-smooth((across-12)/4))
        blend*=1-keep;fixed|=(along<=1.8)&(across<=12)
    proposed=before+(proposed-before)*blend
    packed=np.uint16(np.rint(np.clip(proposed*64+32768,0,65535)))
    after=(packed.astype(np.float32)-32768)/64
    fixed|=protect>=.999
    assert np.array_equal(after[fixed],before[fixed])
    change=after-before; edited=abs(change)>.008
    assert np.count_nonzero(edited)>1000
    assert float((base-after).max())<=1.265625
    (OUT/'H_ChannelShape_2017.r16').write_bytes(packed.astype('<u2').tobytes())
    after.astype('<f4').tofile(OUT/'height_local_south_up.f32')
    Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype(np.uint8)).save(OUT/'T_CS_HeightRG.png')
    np.savez_compressed(OUT/'channel-paths.npz',a=a,b=b,arc=arc)
    report=dict(ok=True,method='Distance to continuous line segments; linearly interpolated original longitudinal bed profile',
        native_landscape=True,profile_target_changed=False,raised_bank_berms=False,roads_and_ford_protected=True,
        crossing_protection='Original cross-channel profiles in a 3.6 m wide strip, blended over 3.2 m along the river; paths unchanged',maximum_original_cut_m=cut_cap,
        edited_samples=int(edited.sum()),changed_area_m2=float(edited.sum()*(2500/2016)**2),
        cut_fill_change_percentiles_m=np.percentile(change[edited],[0,5,50,95,100]).tolist(),
        source_height_sha256=hashlib.sha256((BASE/'RiverLife/H_RiverLife_2017.r16').read_bytes()).hexdigest(),
        height_sha256=hashlib.sha256((OUT/'H_ChannelShape_2017.r16').read_bytes()).hexdigest(),
        longest_path_segment_m=float(np.sqrt(length2).max()),projection_candidates=8,
        fixed_samples_equal=True,ford_ground_m=float(native(after,-661.25,177.5)))
    (OUT/'shape-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
    plot_shape(base,before,after)

def plot_shape(base,before,after):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    lo=(-710,125);hi=(-565,285)
    i0,j0=np.floor((np.array(lo)+1250)*2016/2500).astype(int);i1,j1=np.ceil((np.array(hi)+1250)*2016/2500).astype(int)
    extent=[-1250+i0*2500/2016,-1250+i1*2500/2016,-1250+j0*2500/2016,-1250+j1*2500/2016]
    fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
    for ax,h,title in zip(axs,[before,after],['Before: separate point cuts','After: continuous channel']):
        im=ax.imshow((base-h)[j0:j1,i0:i1],origin='lower',extent=extent,vmin=0,vmax=.8,cmap='cividis')
        ax.set(title=title,aspect='equal',xlabel='East (m)',ylabel='North (m)')
        ax.plot(-661.25,177.5,'r+',ms=10)
    fig.colorbar(im,ax=axs,label='Native incision below original Gaea terrain (m)')
    fig.savefig(OUT/'Native_Channel_Comparison.png',dpi=140);plt.close(fig)

def bake(seconds,resume,initial_dir=None):
    initial_dir=Path(initial_dir) if initial_dir else BASE/'RiverLife'
    before=np.load(initial_dir/'flow-bake.npz');st=np.load(OUT/'flow-state.npz' if resume else initial_dir/('initial-state.npz' if (initial_dir/'initial-state.npz').exists() else 'flow-state.npz'))
    x,y=st['x'],st['y'];xx,yy=np.meshgrid(x,y);active=before['active'];assert np.array_equal(st['cell_indices'],np.flatnonzero(active))
    hgrid=np.fromfile(OUT/'height_local_south_up.f32',dtype='<f4').reshape(N,N)
    bed=np.where(xx>=-1250,native(hgrid,xx,yy),before['bed']);z=bed[active].astype(float)
    ids=np.full(bed.shape,-1,np.int32);ids[active]=np.arange(active.sum())
    aa=[];bb=[];axes=[]
    for axis,(s,t) in enumerate([(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]):
        ok=(s>=0)&(t>=0);aa.extend(s[ok]);bb.extend(t[ok]);axes.extend([axis]*int(ok.sum()))
    a=np.array(aa,np.int32);b=np.array(bb,np.int32);axes=np.array(axes)
    flow=sum(q for sx,sy,q in life.SOURCES);src=[];weights=[]
    for sx,sy,q in life.SOURCES:
        near=np.flatnonzero((xx[active]-sx)**2+(yy[active]-sy)**2<2.5**2)
        w=np.exp(-(z[near]-z[near].min())*10);w*=q/flow/w.sum();src.extend(near);weights.extend(w)
    src=np.array(src,np.int64);weights=np.array(weights);reservoir=np.flatnonzero((xx[active]<-1400)&(z<life.LAKE)).astype(np.int64)
    if resume:
        assert np.array_equal(st['bed'],z);h=st['h'].copy();hu=st['hu'].copy();hv=st['hv'].copy()
        t=float(st['time']);totalin=float(st['totalin']);totalout=float(st['totalout']);mass0=float(st['mass0']);steps=int(st['steps'])
    else:
        # Preserve the previous free surface and momentum velocity as a warm start;
        # account for the new stored volume, then solve against the changed bed.
        h=np.maximum(0,st['bed']+st['h']-z)
        hu=st['hu']/np.maximum(st['h'],.003)*h;hv=st['hv']/np.maximum(st['h'],.003)*h
        t=0.;totalin=totalout=0.;mass0=h.sum()*DX*DX;steps=0
    end=t+seconds;start=time.monotonic();previous=h.copy();history=[]
    stability=deque([(t,h.copy(),hu/np.maximum(h,.003),hv/np.maximum(h,.003))],maxlen=6)
    sums=[h*0,h*0,h*0];samples=0
    while t<end:
        duration=min(40,end-t)
        added,removed,count,dt,negative=step_for(z,h,hu,hv,a,b,axes,DX,src,weights,flow,reservoir,life.LAKE,duration,.055)
        assert negative<1e-7
        t+=duration;totalin+=added;totalout+=removed;steps+=count
        error=h.sum()*DX*DX-mass0-totalin-totalout
        row=dict(time_s=t,outflow_m3s=-removed/duration,depth_change_m=float(np.max(abs(h-previous))),mass_error_m3=float(error),wall_s=round(time.monotonic()-start,1))
        previous[:]=h;history.append(row);print(json.dumps(row),flush=True)
        u=hu/np.maximum(h,.003);v=hv/np.maximum(h,.003);stability.append((t,h.copy(),u.copy(),v.copy()))
        if t>=end-120:sums[0]+=h;sums[1]+=u;sums[2]+=v;samples+=1
        if int(t)%200==0 or t>=end:
            np.savez_compressed(OUT/'flow-state.npz',x=x,y=y,cell_indices=np.flatnonzero(active),bed=z,h=h,hu=hu,hv=hv,time=t,totalin=totalin,totalout=totalout,mass0=mass0,steps=steps)
    depth=np.zeros_like(bed);vx=depth.copy();vy=depth.copy()
    depth[active]=sums[0]/samples;vx[active]=sums[1]/samples;vy[active]=sums[2]/samples
    wet=(depth>.028)&(bed>life.LAKE-.20);labels,n=label(wet,np.ones((3,3)));lids=set()
    for sx,sy,q in life.SOURCES:lids.update(labels[((xx-sx)**2+(yy-sy)**2<36)&wet].tolist())
    lids.discard(0);wet=np.isin(labels,list(lids));wet|=(distance_transform_edt(~wet)*DX<3)&(bed<life.LAKE+.08)&(depth>.028)
    speed=np.hypot(vx,vy);froude=speed/np.sqrt(9.81*np.maximum(depth,.03));strain=np.hypot(np.gradient(vx,DX,axis=1),np.gradient(vy,DX,axis=0))
    foam=gaussian_filter(np.clip((froude-.7)*.15+np.maximum(strain-.18,0)*.08,0,.35)*np.clip(depth/.09,0,1),.55)
    t0,h0,u0,v0=stability[0];rendered=(h>.028)&(h0>.028);visible=(h>.055)&(h0>.055)
    depthdrift=float(np.max(abs(h-h0)[rendered]));velocitydrift=float(np.max(np.hypot(u-u0,v-v0)[visible]))
    connected=bool(np.any(wet&(bed<life.LAKE+.05)))
    edge=active&~binary_erosion(active,structure=np.ones((3,3)),border_value=0)
    edgewet=int(np.count_nonzero(edge&(bed>life.LAKE+.20)&(depth>.05)))
    routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
    roadclear=min(float((cKDTree([[p['x_m'],p['y_m']] for p in r['points']]).query(np.c_[xx[wet],yy[wet]])[0]-r['width_m']/2-1.1).min()) for r in routes)
    stable=t-t0>=199.9 and depthdrift<.003 and velocitydrift<.01
    checks=check_solver();checks.update(mass_error_m3=float(error),stable_visual_bake=bool(stable),stability_window_s=t-t0,max_visible_depth_drift_m=depthdrift,max_visible_velocity_drift_mps=velocitydrift,connected_to_lake=connected,artificial_edge_wet_cells=edgewet,road_edge_clearance_m=roadclear)
    converged=abs(history[-1]['outflow_m3s']-flow)/flow<.035 and history[-1]['depth_change_m']<.015
    report=dict(ok=bool(stable and connected and edgewet==0 and roadclear>12 and abs(error)<1e-5*max(totalin,1)),converged=bool(converged),method='Warm-started existing conservative shallow-water solver on reshaped native terrain',simulated_seconds=t,wall_seconds=time.monotonic()-start,active_cells=int(active.sum()),runtime_simulation=False,total_inflow_m3s=flow,validation=checks,history=history,wet_area_m2=float(wet.sum()*DX*DX))
    np.savez_compressed(OUT/'flow-bake.npz',x=x,y=y,bed=bed,depth=depth,surface=bed+depth,vx=vx,vy=vy,foam=foam,wet=wet,active=active,coverage=before['coverage'])
    (OUT/'flow-report.json').write_text(json.dumps(report,indent=2));print('CHANNEL_SHAPE_BAKE_OK' if report['ok'] else 'CHANNEL_SHAPE_BAKE_NEEDS_MORE_SETTLING',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--seconds',type=float,default=0);p.add_argument('--resume',action='store_true');args=p.parse_args()
    if args.prepare:prepare()
    if args.seconds:bake(args.seconds,args.resume)
