"""Restore Gaea's actual network, refine shallow native banks, bake fixed-bed flow.

Gaea supplies topology. The regional gravel shelves are an authored refinement,
not a sediment-transport simulation. No post-build raw Gaea water is installed.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, map_coordinates, distance_transform_edt
from scipy.spatial import cKDTree
import reshape_benmore_channel as hydraulic
import bake_benmore_river_life as life

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'GaeaCreek'
GAEA=BASE/'review/CoherentCreek'
N=2017;STEP=2500/2016

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    original=np.fromfile(BASE/'candidate/height_local_south_up.f32','<f4').reshape(N,N)
    current=np.fromfile(BASE/'ChannelShape/height_local_south_up.f32','<f4').reshape(N,N)
    source=np.load(GAEA/'network-paths.npz');paths=[source[k] for k in source.files]
    outlet=np.load(BASE/'ChannelShape/original-paths.npz')['0']
    for k,p in enumerate(paths):
        match=np.flatnonzero((p[:,0]<-835)&(p[:,0]>-850)&(p[:,1]<50))
        assert len(match)
        d,near=cKDTree(outlet[:,:2]).query(p[match,:2]);at=match[d.argmin()];tail=outlet[near[d.argmin()]:]
        assert d.min()<3
        paths[k]=np.vstack([p[:at],tail])
    starts=[];ends=[];widths=[];curves=[]
    for p in paths:
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
        tang=np.gradient(p[:,:2],axis=0);tang/=np.linalg.norm(tang,axis=1)[:,None]
        angle=np.unwrap(np.arctan2(tang[:,1],tang[:,0]))
        curve=gaussian_filter1d(np.gradient(angle,arc),3)
        ground=hydraulic.native(original,p[:,0],p[:,1])
        grade=np.maximum(0,-np.gradient(gaussian_filter1d(ground,3),arc))
        width=2.0+.55*(1-np.clip(grade/.10,0,1))
        normal=np.c_[-tang[:,1],tang[:,0]]
        bankground=np.stack([hydraulic.native(original,p[:,0]+normal[:,0]*offset,p[:,1]+normal[:,1]*offset) for offset in [-3,-1.5,0,1.5,3]])
        # Centre elevation alone misses the lower transverse bank. Cut beneath
        # that bank without raising a berm; water depth remains a solver result.
        floor=np.minimum.accumulate(bankground.min(0)-.34-.04*np.clip(abs(curve)*25,0,1))
        q=np.c_[p[:,:2],floor]
        starts.extend(q[:-1]);ends.extend(q[1:]);widths.extend(width[:-1]);curves.extend(curve[:-1])
    a,b=np.array(starts),np.array(ends);width=np.array(widths);curve=np.array(curves)
    vec=b[:,:2]-a[:,:2];l2=np.sum(vec*vec,axis=1);assert l2.min()>0
    xx,yy=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N));xy=np.c_[xx.ravel(),yy.ravel()]
    distance,nearest=cKDTree((a[:,:2]+b[:,:2])/2).query(xy)
    chosen=np.flatnonzero(distance<22);p=xy[chosen]
    _,ids=cKDTree((a[:,:2]+b[:,:2])/2).query(p,k=8)
    diff=p[:,None,:]-a[ids,:2];fraction=np.clip(np.sum(diff*vec[ids],axis=2)/l2[ids],0,1)
    residual=diff-fraction[:,:,None]*vec[ids];dd=np.sum(residual*residual,axis=2)
    row=np.arange(len(p));best=dd.argmin(1);s=ids[row,best];f=fraction[row,best]
    d=np.sqrt(dd[row,best]);signed=(vec[s,0]*residual[row,best,1]-vec[s,1]*residual[row,best,0])/np.sqrt(l2[s])
    inside=signed*curve[s]>0;bend=np.clip(abs(curve[s])*32,0,1)
    wetwidth=width[s]
    bankwidth=wetwidth+np.where(inside,2.8+bend*4.5,1.6-bend*.5)
    floor=a[s,2]+f*(b[s,2]-a[s,2]);base=original.ravel()[chosen]
    # A shallow inside shelf grades into the untouched land; outside banks turn
    # upward sooner. No raised berms and no independent circular excavation.
    t=hydraulic.smooth((d-1.3)/np.maximum(wetwidth-1.3,.4))
    shelf=floor+.18+t*.07
    core=floor+(shelf-floor)*t
    bankt=hydraulic.smooth((d-wetwidth)/np.maximum(bankwidth-wetwidth,.5))
    target=np.where(d<=wetwidth,core,shelf+(base-shelf)*bankt)
    protect=np.load(BASE/'source/protect_2017.npy').ravel()[chosen]
    cut=np.clip(base-target,0,1.25)*(1-protect)
    proposed=original.copy().ravel();proposed[chosen]-=cut;proposed=proposed.reshape(N,N)
    transition=hydraulic.smooth((xx+875)/65)
    proposed=current+(proposed-current)*transition
    packed=np.uint16(np.rint(proposed*64+32768));h=(packed.astype(np.float32)-32768)/64
    fixed=np.load(BASE/'source/protect_2017.npy')>=.999999
    assert np.array_equal(h[fixed],original[fixed])
    packed.astype('<u2').tofile(OUT/'H_GaeaCreek_2017.r16');h.astype('<f4').tofile(OUT/'height_local_south_up.f32')
    Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'T_GC_HeightRG.png')
    zone=np.zeros(original.size);zone[chosen]=1-hydraulic.smooth((d-(bankwidth+1.5))/4)
    inner=np.zeros(original.size);inner[chosen]=inside*bend
    zone.reshape(N,N).astype('<f4').tofile(OUT/'bankfull_mask.f32')
    inner.reshape(N,N).astype('<f4').tofile(OUT/'inside_bar.f32')
    np.savez_compressed(OUT/'network-paths.npz',**{str(i):p for i,p in enumerate(paths)})
    np.savez_compressed(OUT/'channel-paths.npz',a=a,b=b,arc=np.zeros(len(a)))
    # Start the fixed-bed solver only in a bounded offline corridor. This does
    # not change the existing 60 m runtime interaction patch or vehicle tuning.
    old=np.load(BASE/'ChannelShape/flow-bake.npz');x,y=old['x'],old['y'];gx,gy=np.meshgrid(x,y)
    bed=np.where(gx>=-1250,hydraulic.native(h,gx,gy),old['bed'])
    pts=np.concatenate([p[:,:2] for p in paths]);dist=cKDTree(pts).query(np.c_[gx.ravel(),gy.ravel()])[0].reshape(gx.shape)
    active=old['active']|(dist<110)|((gx<-1210)&(bed<life.LAKE+2))
    # Extend coverage to the preserved real shoreline / lake reservoir.
    active|=(gx<-1250)&old['active']
    z=bed[active].astype(float)
    previous=np.load(BASE/'ChannelShape/flow-state.npz');prioridx=previous['cell_indices'];dest=np.searchsorted(np.flatnonzero(active),prioridx)
    depth=np.maximum(0,life.LAKE-z);hu=depth*0;hv=depth*0
    depth[dest]=np.maximum(0,previous['bed']+previous['h']-z[dest])
    hu[dest]=previous['hu']/np.maximum(previous['h'],.003)*depth[dest]
    hv[dest]=previous['hv']/np.maximum(previous['h'],.003)*depth[dest]
    np.savez_compressed(OUT/'flow-bake.npz',x=x,y=y,bed=bed,active=active,coverage=old['coverage'])
    np.savez_compressed(OUT/'initial-state.npz',x=x,y=y,cell_indices=np.flatnonzero(active),bed=z,h=depth,hu=hu,hv=hv)
    sources=[(float(p[0,0]),float(p[0,1]),q) for p,q in zip(paths,[.36,.22,.22])]
    (OUT/'sources.json').write_text(json.dumps(sources,indent=2))
    changed=abs(h-current)>.008;prefix=np.zeros((2018,2018),dtype='<u4');prefix[1:,1:]=changed.cumsum(0).cumsum(1);prefix.tofile(OUT/'changed-prefix.u32')
    support=np.argwhere(changed);support=support[np.linspace(0,len(support)-1,24).astype(int)]
    (OUT/'support-checks.json').write_text(json.dumps([[-1250+i*STEP,-1250+j*STEP] for j,i in support]))
    report=dict(ok=True,course_source=str(GAEA/'Benmore_PairedCreek.terrain'),network_source=str(GAEA/'build/M_Rivers.tif'),
        topology='Gaea river mask with 4 m raster smoothing; join within 3 m to the existing tested outlet at X=-843 m, preserving its protected road/shoreline grades',
        morphology='Shallow active channel, asymmetric inside gravel shelves / outside banks, no raised berm',
        raw_gaea_surface_installed=False,raw_gaea_out_rejected_reason='Rivers raises some ground by 9 m; restore network, refine original protected terrain and rebake on its exact final samples',
        sediment_transport=False,maximum_cut_below_original_m=float((original-h).max()),old_artificial_channel_restored="Upper reach restored; tested lower outlet retained",
        protected_samples_equal=True,changed_native_samples=int(changed.sum()),active_offline_cells=int(active.sum()),
        retained_tested_outlet_west_of_x_m=-875,transition_to_new_gaea_reach_x_m=[-875,-810],
        main_course_length_m=float(np.linalg.norm(np.diff(paths[0][:,:2],axis=0),axis=1).sum()),
        sources_m3s=sources,height_sha256=hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest())
    (OUT/'shape-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)

def bake(seconds,resume):
    hydraulic.OUT=OUT;life.SOURCES=json.loads((OUT/'sources.json').read_text())
    hydraulic.bake(seconds,resume,initial_dir=OUT)

def prune_offline_domain():
    """Remove dry far-field work, retaining a 50 m buffer and exact wet state.

    Run only between completed bake chunks. The edge-wet gate remains mandatory.
    """
    st=np.load(OUT/'flow-state.npz');b=np.load(OUT/'flow-bake.npz')
    full=np.zeros(b['active'].shape);full.ravel()[st['cell_indices']]=st['h']
    xx,yy=np.meshgrid(b['x'],b['y']);paths=np.load(OUT/'network-paths.npz')
    points=np.concatenate([paths[k][:,:2] for k in paths.files])
    distance=cKDTree(points).query(np.c_[xx.ravel(),yy.ravel()])[0].reshape(full.shape)
    active=b['active']&((distance_transform_edt(full<.001)*life.DX<50)|(distance<50))
    keep=active.ravel()[st['cell_indices']];removed=float(st['h'][~keep].sum()*life.DX**2)
    assert removed<.001,'Do not prune a wet domain'
    state={k:st[k] for k in st.files}
    for key in ['bed','h','hu','hv']:state[key]=st[key][keep]
    state['cell_indices']=np.flatnonzero(active);state['mass0']=float(st['mass0'])-removed
    np.savez_compressed(OUT/'flow-state.npz',**state)
    data={k:b[k] for k in b.files};data['active']=active;np.savez_compressed(OUT/'flow-bake.npz',**data)
    report=json.loads((OUT/'shape-report.json').read_text())
    report.update(active_offline_cells=int(active.sum()),offline_prune_at_seconds=float(st['time']),
                  offline_removed_shallow_volume_m3=removed,offline_boundary_buffer_m=50)
    (OUT/'shape-report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--prune',action='store_true');p.add_argument('--seconds',type=float,default=0);p.add_argument('--resume',action='store_true');args=p.parse_args()
    if args.prepare:prepare()
    if args.prune:prune_offline_domain()
    if args.seconds:bake(args.seconds,args.resume)
