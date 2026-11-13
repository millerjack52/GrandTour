"""Bed-first Otago gravel-creek interpretation on the native Landscape.

Gaea defines the valley and tributaries. Independent gravel margins, discrete
sediment bars and separate low-flow grooves define the bed; the existing
conservative fixed-bed solver determines the water footprint. No sediment
transport or surveyed regional dimensions are claimed.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d, map_coordinates
from scipy.spatial import cKDTree
import reshape_benmore_channel as hydraulic
import bake_benmore_river_life as life
from prepare_benmore_gaea import resample

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'Morphology';N=2017;STEP=2500/2016

def interp(knots, s):
    q=np.asarray(knots,float)
    return PchipInterpolator(q[:,0],q[:,1])(np.clip(s,q[0,0],q[-1,0]))

def resampled(p):
    p=p[:,:2];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    s=np.linspace(0,arc[-1],int(arc[-1]/1.5)+1)
    xy=np.stack([np.interp(s,arc,p[:,k]) for k in [0,1]],1)
    xy[1:-1]=gaussian_filter1d(xy,1.25,axis=0)[1:-1]
    return xy

def geometry(original):
    data=np.load(BASE/'review/CoherentCreek/network-paths.npz')
    main=resampled(data['0'])
    tail=np.load(BASE/'ChannelShape/original-paths.npz')['0'];tail=tail[tail[:,0]<=-1260,:2]
    main=resampled(np.vstack([main,tail]))
    paths=[main]
    joins=[None]
    for key in ['1','2']:
        p=resampled(data[key]);d,j=cKDTree(main).query(p)
        # The source branches share Gaea's downstream valley. Build shared bed
        # once, avoiding different profiles competing at the same confluence.
        k=next(k for k in range(8,len(p)-5) if np.all(d[k:k+5]<2))
        paths.append(resampled(np.vstack([p[:k],main[j[k]]])))
        joins.append(int(j[k]))
    reaches=[]
    for number,xy in enumerate(paths):
        s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
        tang=np.gradient(xy,axis=0);tang/=np.linalg.norm(tang,axis=1)[:,None]
        normal=np.c_[-tang[:,1],tang[:,0]];length=s[-1]
        if number==0:
            # Independently specified banks, using different control stations.
            # These are sediment-corridor bounds, not offsets of the wet groove.
            left=interp([(0,4),(280,4.5),(490,5),(690,8),(820,6),(950,9),
                (1030,16),(1120,9),(1180,7),(1260,16),(1340,8),(1410,14),
                (1490,8),(1550,12),(length,6)],s)
            right=interp([(0,4),(240,5),(520,4),(650,6),(760,10),(900,5),
                (990,8),(1070,11),(1160,6),(1220,11),(1310,7),(1390,6),
                (1470,16),(1530,10),(length,6)],s)
            offset=interp([(0,0),(500,0),(690,-1),(800,2),(930,-1),
                (1010,-2),(1060,-4),(1115,1),(1180,1),(1250,-4),(1320,1),
                (1390,2),(1465,5),(1520,-2),(1590,0),(length,0)],s)
            half=interp([(0,2.2),(450,2.25),(740,2.5),(930,2.9),(1030,3.2),
                (1110,2.3),(1210,2.8),(1280,3.5),(1360,2.4),(1450,3.1),
                (1540,2.5),(length,3)],s)
            # Short split/rejoin grooves, not continuous parallel ditches.
            branches=[(1015,1040,1080,6.8),(1190,1248,1322,8.0)]
            bars=[(1045,1.7,18,3.3,.47),(1258,2.0,38,4.2,.49),
                  (1458,-.6,31,4.1,.46),(1150,-3.3,16,2.3,.43),
                  (1350,-2.8,18,2.5,.45)]
        else:
            left=np.full_like(s,3.6);right=np.full_like(s,4.1)
            offset=np.zeros_like(s);half=np.full_like(s,1.9);branches=[];bars=[]
        bankground=np.stack([hydraulic.native(original,xy[:,0]+normal[:,0]*(np.where(f>0,left,right)+3)*f,
            xy[:,1]+normal[:,1]*(np.where(f>0,left,right)+3)*f) for f in np.linspace(-1,1,23)])
        ground=hydraulic.native(original,xy[:,0],xy[:,1])
        # Read the valley's low transverse envelope. A shallow shelf sits above
        # the groove; outer banks blend back to untouched land, without berms.
        floor=gaussian_filter1d(bankground.min(0),2)-.48
        if number==0:
            # Two short steep turns at the middle transition otherwise throw a
            # thin run-up film over the downhill lip. Seat the shallow groove
            # below that lip; this changes bed seating, not discharge/depth.
            floor-=.24*hydraulic.smooth((s-525)/35)*(1-hydraulic.smooth((s-705)/35))
            half+=.45*hydraulic.smooth((s-515)/45)*(1-hydraulic.smooth((s-715)/45))
        # Constrain the broad hydraulic grade, retaining local riffle/scour
        # relief below. Do not flatten every bed sample into a downhill ramp.
        for i in range(1,len(s)):
            floor[i]=min(floor[i],floor[i-1]-.0015*(s[i]-s[i-1]))
        if number==0:
            native_end=np.flatnonzero(xy[:,0]>=-1250)[-1]
            t=np.clip((s-s[native_end])/(length-s[native_end]),0,1)
            floor[native_end:]=floor[native_end]*(1-t[native_end:])+(life.LAKE-.15)*t[native_end:]
        else:
            desired=reaches[0]['floor'][joins[number]]
            blend=hydraulic.smooth((s-(length-35))/35)
            floor+=blend*(desired-floor[-1])
        relief=np.zeros_like(s)
        if number==0:
            for at in [560,716,845,948,1135,1190,1336,1538]:
                relief+=.06*np.exp(-((s-at)/4.5)**2)
            for at in [1020,1230,1440]:relief-=.03*np.exp(-((s-at)/12)**2)
        reach=dict(xy=xy,s=s,normal=normal,left=left,right=right,offset=offset,
            half=half,floor=floor,relief=relief,branches=branches,bars=bars,
            ground=ground,number=number)
        reach['tree']=cKDTree((xy[:-1]+xy[1:])/2);reaches.append(reach)
    return reaches

def coordinates(reach,points):
    xy=reach['xy'];v=np.diff(xy,axis=0);l2=np.sum(v*v,1)
    _,idx=reach['tree'].query(points,k=8)
    delta=points[:,None,:]-xy[idx];t=np.clip(np.sum(delta*v[idx],2)/l2[idx],0,1)
    r=delta-t[:,:,None]*v[idx];d2=np.sum(r*r,2);row=np.arange(len(points));pick=d2.argmin(1)
    k=idx[row,pick];f=t[row,pick];res=r[row,pick]
    signed=(v[k,0]*res[:,1]-v[k,1]*res[:,0])/np.sqrt(l2[k])
    station=reach['s'][k]+f*(reach['s'][k+1]-reach['s'][k])
    return station,signed,np.sqrt(d2[row,pick])

def surface(reach,points,base):
    s,d,dist=coordinates(reach,points)
    at=lambda key:np.interp(s,reach['s'],reach[key])
    left,right=at('left'),at('right');edge=np.minimum(left-d,right+d)
    floor=at('floor');offset=at('offset');half=at('half')
    shelf=floor+.34+.012*np.sin(s*.27+d*.31)
    primary=floor+at('relief')+.36*np.minimum(abs(d-offset)/half,1)**2
    bed=np.minimum(shelf,primary)
    for start,apex,end,side in reach['branches']:
        channel=interp([(start,float(np.interp(start,reach['s'],reach['offset']))),
            (apex,side),(end,float(np.interp(end,reach['s'],reach['offset'])))],s)
        secondary=floor+.045+.31*np.minimum(abs(d-channel)/2.3,1)**2
        bed=np.where((s>=start)&(s<=end),np.minimum(bed,secondary),bed)
    bar=np.zeros(len(s))
    for center,cross,along,across,crest in reach['bars']:
        u=(s-center)/along;v=(d-cross)/across
        cap=np.maximum(0,1-u*u-v*v)
        height=crest*cap**.65*np.clip(1-.22*u,.65,1.2)
        bar=np.maximum(bar,height)
        bed=np.where(cap>0,np.maximum(bed,floor+height),bed)
    bank=hydraulic.smooth(np.clip(edge/3,0,1))
    first=reach['xy'][1]-reach['xy'][0];first/=np.linalg.norm(first)
    last=reach['xy'][-1]-reach['xy'][-2];last/=np.linalg.norm(last)
    beyond=np.maximum((reach['xy'][0]-points)@first,(points-reach['xy'][-1])@last)
    cap=1-hydraulic.smooth(beyond/2.5)
    bank*=cap
    bed=base+(bed-base)*bank
    # Do not touch terrain beyond actual independently authored gravel margins.
    bed=np.where(edge>0,bed,base)
    zone=(1-hydraulic.smooth((-edge+1)/4))*(dist<30)*cap
    return bed,zone,bar,s,d

def prepare(warm_start=False):
    OUT.mkdir(parents=True,exist_ok=True)
    prior=None
    if warm_start:
        with np.load(OUT/'flow-state.npz') as f:prior={k:f[k] for k in f.files}
    original=np.fromfile(BASE/'candidate/height_local_south_up.f32','<f4').reshape(N,N)
    current=np.fromfile(BASE/'CourseRevision/height_local_south_up.f32','<f4').reshape(N,N)
    reaches=geometry(original)
    roads=resample(np.asarray(Image.open(BASE/'input/M_ProtectRoads_2048.png'))[::-1].astype(float)/65535,N)
    xx,yy=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N))
    points=np.c_[xx.ravel(),yy.ravel()];proposed=original.ravel().copy()
    zone=np.zeros(original.size);bars=zone.copy();rocky=zone.copy()
    for reach in reaches:
        dist=reach['tree'].query(points)[0];chosen=np.flatnonzero(dist<30)
        target,z,b,s,d=surface(reach,points[chosen],original.ravel()[chosen])
        protect=np.load(BASE/'source/protect_2017.npy').ravel()[chosen]
        mouth=hydraulic.smooth((-points[chosen,0]-1090)/90)*z
        protect=np.maximum(roads.ravel()[chosen],protect*(1-mouth))
        # Preserve the original ground and protected road. Bars are sediment
        # left above surrounding incision; no raised banks or deeper water goal.
        cut=np.clip(original.ravel()[chosen]-target,0,2.5)*(1-protect)
        proposed[chosen]=np.minimum(proposed[chosen],original.ravel()[chosen]-cut)
        zone[chosen]=np.maximum(zone[chosen],z);bars[chosen]=np.maximum(bars[chosen],b)
        rocky[chosen]=np.maximum(rocky[chosen],z*(1-hydraulic.smooth((s-420)/420)))
    retired=abs(current-original).ravel()>.008
    proposed=np.where((zone>0)|retired,proposed,current.ravel()).reshape(N,N)
    packed=np.uint16(np.rint(proposed*64+32768));h=(packed.astype(np.float32)-32768)/64
    assert np.array_equal(h[roads>=.99999],current[roads>=.99999])
    packed.astype('<u2').tofile(OUT/'H_GaeaCreek_2017.r16');h.astype('<f4').tofile(OUT/'height_local_south_up.f32')
    Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'T_GC_HeightRG.png')
    for name,data in [('bankfull_mask',zone),('inside_bar',bars),('rocky_reach',rocky)]:
        data.reshape(N,N).astype('<f4').tofile(OUT/(name+'.f32'))
    paths=[]
    for reach in reaches:
        xy=reach['xy']+reach['normal']*reach['offset'][:,None]
        paths.append(np.c_[xy,hydraulic.native(h,xy[:,0],xy[:,1])])
    # Network paths are utility guides, never the rendered water footprint.
    np.savez_compressed(OUT/'network-paths.npz',**{str(i):p for i,p in enumerate(paths)})
    a=np.concatenate([p[:-1] for p in paths]);b=np.concatenate([p[1:] for p in paths])
    np.savez_compressed(OUT/'channel-paths.npz',a=a,b=b,arc=np.concatenate([r['s'][:-1] for r in reaches]))
    old=np.load(BASE/'CourseRevision/flow-bake.npz');x,y=old['x'],old['y'];gx,gy=np.meshgrid(x,y)
    bed=np.where(gx>=-1250,hydraulic.native(h,gx,gy),old['bed'])
    query=np.c_[gx.ravel(),gy.ravel()];distance=cKDTree(np.concatenate([r['xy'] for r in reaches])).query(query)[0].reshape(gx.shape)
    selected=np.flatnonzero((gx<-1250).ravel()&(distance.ravel()<30))
    target,_,_,_,_=surface(reaches[0],query[selected],bed.ravel()[selected])
    edge=hydraulic.native(h,-1250,query[selected,1]);join=hydraulic.smooth((-query[selected,0]-1250)/10)
    bed.ravel()[selected]=edge*(1-join)+np.minimum(bed.ravel()[selected],target)*join
    # A local fixed-bed creek bake includes the complete gravel corridor and at
    # least 19 m of native soil beyond its widest bank. Far-field hillside
    # runoff is outside this solver's scope; artificial boundaries must still
    # pass the dry-edge gate. The lake reservoir keeps its original footprint.
    active=(distance<35)|((gx<-1220)&(bed<life.LAKE+1.5))|((gx<-1330)&old['active'])
    z=bed[active].astype(float);pts=query[active.ravel()]
    depth=np.maximum(0,life.LAKE-z);hu=depth*0;hv=depth*0
    for reach in reaches:
        near=reach['tree'].query(pts)[0]<24;ids=np.flatnonzero(near)
        s,d,_=coordinates(reach,pts[ids]);offset=np.interp(s,reach['s'],reach['offset'])
        floor=np.interp(s,reach['s'],reach['floor'])
        half=np.interp(s,reach['s'],reach['half'])
        hd=np.where((abs(d-offset)<half)&(s>1)&(s<reach['s'][-1]-1),np.maximum(0,floor+.14-z[ids]),0)
        depth[ids]=np.maximum(depth[ids],hd)
        k=np.clip(np.searchsorted(reach['s'],s),1,len(reach['s'])-1)
        direction=reach['xy'][k]-reach['xy'][k-1];direction/=np.linalg.norm(direction,axis=1)[:,None]
        hu[ids]=hd*direction[:,0];hv[ids]=hd*direction[:,1]
    if prior is not None:
        oldids=prior['cell_indices'];newids=np.flatnonzero(active)
        indices=np.searchsorted(oldids,newids);assert np.array_equal(oldids[indices],newids)
        depth=np.maximum(0,prior['bed'][indices]+prior['h'][indices]-z)
        hu=prior['hu'][indices]/np.maximum(prior['h'][indices],.003)*depth
        hv=prior['hv'][indices]/np.maximum(prior['h'][indices],.003)*depth
        # Initialize only the constructed bed and lake; allow the subsequent
        # solve to reveal any genuine new overbank escape. Never trim final water.
        inside=map_coordinates(zone.reshape(N,N),[(pts[:,1]+1250)/STEP,(pts[:,0]+1250)/STEP],order=1,mode='constant')>.03
        inside|=pts[:,0]<-1250
        depth*=inside;hu*=inside;hv*=inside
    np.savez_compressed(OUT/'flow-bake.npz',x=x,y=y,bed=bed,active=active,coverage=old['coverage'])
    np.savez_compressed(OUT/'initial-state.npz',x=x,y=y,cell_indices=np.flatnonzero(active),bed=z,h=depth,hu=hu,hv=hv)
    sources=[(float(p[0,0]),float(p[0,1]),q) for p,q in zip(paths,[.36,.22,.22])]
    (OUT/'sources.json').write_text(json.dumps(sources,indent=2))
    report=dict(ok=True,method='Gaea valley network, independent gravel margins, discrete bars, separate primary and short secondary grooves; water occupancy from conservative fixed-bed flow',
        sediment_transport=False,native_deformable=True,native_spacing_m=STEP,bar_count=len(reaches[0]['bars']),
        short_secondary_grooves=len(reaches[0]['branches']),maximum_cut_below_original_m=float((original-h).max()),
        changed_native_samples=int((abs(h-current)>.008).sum()),roads_protected_equal=True,active_offline_cells=int(active.sum()),
        offline_domain_valley_radius_m=35,minimum_margin_beyond_gravel_m=19,warm_start=warm_start,
        sources_m3s=sources,height_sha256=hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest())
    (OUT/'shape-report.json').write_text(json.dumps(report,indent=2))
    controls=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items() if k!='tree'} for r in reaches]
    (OUT/'morphology-controls.json').write_text(json.dumps(controls,indent=2))
    print(json.dumps(report,indent=2),flush=True);plot()

def plot():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    h=np.fromfile(OUT/'height_local_south_up.f32','<f4').reshape(N,N)
    zone=np.fromfile(OUT/'bankfull_mask.f32','<f4').reshape(N,N)
    bars=np.fromfile(OUT/'inside_bar.f32','<f4').reshape(N,N)
    flow=np.load(OUT/'flow-bake.npz')
    fig,axes=plt.subplots(1,2,figsize=(15,8),layout='constrained')
    shade=LightSource(315,35).hillshade(h,dx=STEP,dy=STEP)
    rgb=np.empty((*h.shape,3));rgb[:]=[.63,.57,.39]
    rgb=rgb*(1-zone[...,None])+np.array([.67,.66,.59])*zone[...,None]
    rgb=np.clip(rgb*(.65+.45*shade[...,None]),0,1)
    for ax in axes:
        ax.imshow(rgb,origin='lower',extent=[-1250,1250,-1250,1250])
        if 'wet' in flow:
            water=np.zeros((*flow['bed'].shape,4));water[flow['wet']]=[.13,.39,.44,.9]
            ax.imshow(water,origin='lower',extent=[flow['x'][0],flow['x'][-1],flow['y'][0],flow['y'][-1]])
        ax.set(aspect='equal',xlabel='World X (m)',ylabel='World Y (m)')
    axes[0].set(xlim=(-1270,-240),ylim=(-150,750),title='Gaea-aligned full drainage')
    axes[1].set(xlim=(-1245,-785),ylim=(-155,105),title='Independent gravel corridor and bar reaches')
    fig.suptitle('Native morphology / '+('baked wet occupancy' if 'wet' in flow else 'bed before water bake')+' — data diagnostic, not Unreal')
    fig.savefig(OUT/'Morphology_Plan.png',dpi=145);plt.close(fig)

def restart_connected():
    """Replace the analytic warm start's isolated puddles, then solve anew.

    This is an initial-condition repair, not deletion from a final bake. A fresh
    mass ledger and another complete settling window must pass afterwards.
    """
    from scipy.ndimage import label
    state=np.load(OUT/'flow-state.npz');b=np.load(OUT/'flow-bake.npz')
    depth=np.zeros(b['bed'].shape);depth.ravel()[state['cell_indices']]=state['h']
    xx,yy=np.meshgrid(b['x'],b['y']);labels,_=label(depth>.002,np.ones((3,3)))
    keepids=set(labels[(xx<-1400)&(depth>.002)].tolist())
    for sx,sy,q in json.loads((OUT/'sources.json').read_text()):
        keepids.update(labels[((xx-sx)**2+(yy-sy)**2<36)&(depth>.002)].tolist())
    keepids.discard(0);keep=np.isin(labels,list(keepids)).ravel()[state['cell_indices']]
    removed=float(state['h'][~keep].sum()*life.DX**2)
    np.savez_compressed(OUT/'initial-state.npz',x=b['x'],y=b['y'],cell_indices=state['cell_indices'],
        bed=state['bed'],h=state['h']*keep,hu=state['hu']*keep,hv=state['hv']*keep)
    report=dict(reason='Analytic initial water left disconnected puddles outside the creek. Warm-start only the source/lake-connected solution; rerun with a fresh mass ledger.',
        previous_simulated_seconds=float(state['time']),initial_volume_removed_m3=removed,
        requires_new_settling_and_boundary_validation=True)
    (OUT/'initial-condition-repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

def cold_start():
    """Only the existing lake is initially wet; all creek water enters at sources."""
    b=np.load(OUT/'flow-bake.npz');xx,yy=np.meshgrid(b['x'],b['y']);active=b['active']
    z=b['bed'][active].astype(float);h=np.where(xx[active]<-1250,np.maximum(0,life.LAKE-z),0)
    np.savez_compressed(OUT/'initial-state.npz',x=b['x'],y=b['y'],cell_indices=np.flatnonzero(active),bed=z,h=h,hu=h*0,hv=h*0)
    (OUT/'cold-start.json').write_text(json.dumps(dict(native_creek_initial_water_m3=0,
        initial_lake_volume_m3=float(h.sum()*life.DX**2),inflows_m3s=[.36,.22,.22],
        terrain_height_sha256=hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest(),
        all_creek_water_must_enter_from_sources_or_lake=True),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--seconds',type=float,default=0)
    parser.add_argument('--resume',action='store_true');parser.add_argument('--plot',action='store_true')
    parser.add_argument('--restart-connected',action='store_true');parser.add_argument('--warm-start',action='store_true')
    parser.add_argument('--cold-start',action='store_true');args=parser.parse_args()
    if args.prepare:prepare(args.warm_start)
    if args.restart_connected:
        assert not args.resume and not args.prepare
        restart_connected()
    if args.cold_start:
        assert not args.resume and not args.restart_connected
        cold_start()
    if args.seconds:
        hydraulic.OUT=OUT;life.SOURCES=json.loads((OUT/'sources.json').read_text());hydraulic.bake(args.seconds,args.resume,initial_dir=OUT);plot()
    elif args.plot:plot()
