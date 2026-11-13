"""Author a whole-valley creek course, then rebake against native terrain.

Gaea supplies headwaters and junctions. Reviewed valley-space control points
author the larger middle/lower bends; this is not simulated channel migration.
Only the river-mouth corridor may alter the old protected shoreline/boundary.
Road heights and all terrain away from the new/retired creek remain unchanged.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d,map_coordinates
from scipy.spatial import cKDTree
import reshape_benmore_channel as hydraulic
import build_benmore_gaea_creek as previous
from prepare_benmore_gaea import resample
import bake_benmore_river_life as life
ROOT,BASE=previous.ROOT,previous.BASE
OUT=BASE/'CourseRevision';N=2017;STEP=2500/2016

def course(h):
    source=np.load(BASE/'review/CoherentCreek/network-paths.npz')
    old=np.load(BASE/'ChannelShape/original-paths.npz')['0']
    tail=old[np.flatnonzero(old[:,0]<=-1251)[0]:]
    # Uneven apex positions and bend spacing selected on the valley plan.
    # They replace the retained straight lower course, rather than adding a
    # periodic sine offset or smoothing the existing trench again.
    plan=np.array([[-445,335],[-500,319],[-490,279],[-545,260],[-595,290],
        [-650,240],[-697,255],[-740,214],[-720,163],[-788,125],[-827,93],
        [-810,49],[-870,12],[-922,32],[-952,-32],[-1008,-12],[-1053,-83],
        [-1110,-55],[-1150,-82],[-1192,-20],[-1227,-66]])
    p0=source['0'];join=np.argmin(np.linalg.norm(p0[:,:2]-[-433,380],axis=1))
    controls=np.vstack([p0[join,:2],plan,tail[0,:2]])
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(controls,axis=0),axis=1))]
    # Chord-parametric spline rounds junctions without flattening the large arcs.
    spline=CubicSpline(arc,controls,axis=0)
    middle=spline(np.arange(0,arc[-1],1.5))
    result=[]
    for key in source.files:
        p=source[key];at=np.argmin(np.linalg.norm(p[:,:2]-p0[join,:2],axis=1))
        assert np.linalg.norm(p[at,:2]-p0[join,:2])<2
        xy=np.vstack([p[:at,:2],middle,tail[:,:2]])
        keep=np.r_[True,np.linalg.norm(np.diff(xy,axis=0),axis=1)>.05];xy=xy[keep]
        result.append(np.c_[xy,hydraulic.native(h,xy[:,0],xy[:,1])])
    (OUT/'course-controls.json').write_text(json.dumps(dict(reference='Gaea headwaters/junctions with authored irregular middle/lower valley bends; regional interpretation, not a surveyed course',controls_xy_m=controls.tolist()),indent=2))
    return result

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    original=np.fromfile(BASE/'candidate/height_local_south_up.f32','<f4').reshape(N,N)
    current=np.fromfile(BASE/'GaeaCreek/height_local_south_up.f32','<f4').reshape(N,N)
    old=np.load(BASE/'GaeaCreek/flow-bake.npz')
    paths=course(original);starts=[];ends=[];widths=[];curves=[];stations=[]
    for p in paths:
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
        tang=np.gradient(p[:,:2],axis=0);tang/=np.linalg.norm(tang,axis=1)[:,None]
        curvature=gaussian_filter1d(np.gradient(np.unwrap(np.arctan2(tang[:,1],tang[:,0])),arc),2)
        ground=hydraulic.native(original,p[:,0],p[:,1]);normal=np.c_[-tang[:,1],tang[:,0]]
        # Read the lower terrain across the WHOLE bankfull section. Sampling
        # only +/-3 m missed low land beyond the inside shelves and allowed a
        # shortcut across the larger bends. The live water stays shallow.
        localgrade=np.maximum(0,-np.gradient(gaussian_filter1d(ground,3),arc))
        localwidth=2.0+1.15*(1-np.clip(localgrade/.08,0,1))
        section=localwidth+3.2+7.5*np.clip(abs(curvature)*50,0,1)+1.0
        banks=np.stack([hydraulic.native(original,p[:,0]+normal[:,0]*section*f,p[:,1]+normal[:,1]*section*f) for f in np.linspace(-1,1,17)])
        exterior=map_coordinates(old['bed'],[(p[:,1]-old['y'][0])/life.DX,(p[:,0]-old['x'][0])/life.DX],order=1,mode='nearest')
        floor=np.where(p[:,0]<-1250,exterior,gaussian_filter1d(banks.min(0),1)-.40)
        for j in range(1,len(floor)):
            floor[j]=min(floor[j],floor[j-1]-.002*(arc[j]-arc[j-1]))
        grade=np.clip(-np.gradient(gaussian_filter1d(floor,3),arc),.002,.15)
        width=2.0+1.15*(1-np.clip(grade/.08,0,1))
        q=np.c_[p[:,:2],floor];starts.extend(q[:-1]);ends.extend(q[1:]);widths.extend(width[:-1]);curves.extend(curvature[:-1]);stations.extend(arc[:-1])
    a,b=np.array(starts),np.array(ends);width=np.array(widths);curve=np.array(curves);station=np.array(stations)
    vec=b[:,:2]-a[:,:2];l2=np.sum(vec*vec,axis=1);assert l2.min()>0
    tree=cKDTree((a[:,:2]+b[:,:2])/2)
    xx,yy=np.meshgrid(np.linspace(-1250,1250,N),np.linspace(-1250,1250,N));xy=np.c_[xx.ravel(),yy.ravel()]
    distance=tree.query(xy)[0];chosen=np.flatnonzero(distance<24);p=xy[chosen]
    _,ids=tree.query(p,k=12);diff=p[:,None,:]-a[ids,:2]
    t=np.clip(np.sum(diff*vec[ids],axis=2)/l2[ids],0,1);residual=diff-t[:,:,None]*vec[ids]
    dd=np.sum(residual*residual,axis=2);row=np.arange(len(p));pick=dd.argmin(1);s=ids[row,pick];fraction=t[row,pick]
    d=np.sqrt(dd[row,pick]);signed=(vec[s,0]*residual[row,pick,1]-vec[s,1]*residual[row,pick,0])/np.sqrt(l2[s])
    inside=signed*curve[s]>0;bend=np.clip(abs(curve[s])*50,0,1)
    # Bankfull shelves widen at bend apices; the low-flow water is narrower.
    wetwidth=width[s];bankwidth=wetwidth+np.where(inside,3.2+7.5*bend,4.0+2.0*bend)
    floor=a[s,2]+fraction*(b[s,2]-a[s,2]);base=original.ravel()[chosen]
    # A broader flat shallow floor carries the discharge without over-topping
    # the low inside shelves; the former 2.2 m flat core created backwater.
    coret=hydraulic.smooth((d-wetwidth*.70)/np.maximum(wetwidth*.30,.4))
    shelf=floor+.23+np.where(inside,.04*bend,0)
    core=floor+(shelf-floor)*coret
    bankt=hydraulic.smooth((d-wetwidth)/np.maximum(bankwidth-wetwidth,.5))
    target=np.where(d<=wetwidth,core,shelf+(base-shelf)*bankt)
    roads=resample(np.asarray(Image.open(BASE/'input/M_ProtectRoads_2048.png'))[::-1].astype(float)/65535,N)
    # Existing shoreline/boundary protection caused the old mouth to close.
    # Release that mask only within this final channel corridor, retaining roads.
    protect=np.load(BASE/'source/protect_2017.npy').ravel()[chosen]
    mouth=hydraulic.smooth((-p[:,0]-1090)/90)*(1-hydraulic.smooth((d-bankwidth)/3))
    protect=np.maximum(roads.ravel()[chosen],protect*(1-mouth))
    # Native excavation adapts to the transverse slope; a 1.25 m cut cap had
    # left two bent sections above the neighbouring runoff route. This is bed
    # geometry, not a request for deeper water or a change to its solver/tuning.
    cut=np.clip(base-target,0,2.5)*(1-protect)
    proposed=original.copy().ravel();proposed[chosen]-=cut;proposed=proposed.reshape(N,N)
    # Preserve all prior terrain outside the new OR retired creek footprints.
    oldchannel=abs(current-original)>.008;editable=np.zeros(original.size,bool);editable[chosen]=True;editable=editable.reshape(N,N)
    proposed=np.where(editable|oldchannel,proposed,current)
    packed=np.uint16(np.rint(proposed*64+32768));h=(packed.astype(np.float32)-32768)/64
    fixed=roads>=.99999;assert np.array_equal(h[fixed],current[fixed])
    packed.astype('<u2').tofile(OUT/'H_GaeaCreek_2017.r16');h.astype('<f4').tofile(OUT/'height_local_south_up.f32')
    Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'T_GC_HeightRG.png')
    zone=np.zeros(original.size);zone[chosen]=1-hydraulic.smooth((d-(bankwidth+1.5))/4)
    inner=np.zeros(original.size);inner[chosen]=inside*bend
    zone.reshape(N,N).astype('<f4').tofile(OUT/'bankfull_mask.f32');inner.reshape(N,N).astype('<f4').tofile(OUT/'inside_bar.f32')
    np.savez_compressed(OUT/'network-paths.npz',**{str(i):p for i,p in enumerate(paths)})
    np.savez_compressed(OUT/'channel-paths.npz',a=a,b=b,arc=station)
    x,y=old['x'],old['y'];gx,gy=np.meshgrid(x,y)
    bed=np.where(gx>=-1250,hydraulic.native(h,gx,gy),old['bed'])
    query=np.c_[gx.ravel(),gy.ravel()];distance,near=tree.query(query);distance=distance.reshape(gx.shape)
    # The revised native mouth is lower than the previous scenery apron. Join
    # that existing, outside-Landscape bed to the same course; otherwise its
    # old sill dams the channel at x=-1250. This does not replace native terrain.
    for path_index,p in enumerate(paths):
        offset=sum(len(q)-1 for q in paths[:path_index]);count=len(p)-1
        arclength=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
        j=np.flatnonzero(p[:,0]<-1250)[0]
        mouth_y=np.interp(-1250,p[j-1:j+1,0][::-1],p[j-1:j+1,1][::-1])
        mouth_z=float(hydraulic.native(h,-1250,mouth_y))
        exterior_arc=arclength[j:]-arclength[j]
        floor_tail=mouth_z+(life.LAKE-.15-mouth_z)*np.clip(exterior_arc/max(exterior_arc[-1],1),0,1)
        a[offset+j:offset+count,2]=floor_tail[:-1];b[offset+j-1:offset+count,2]=floor_tail
    selected=np.flatnonzero((gx<-1250).ravel()&(distance.ravel()<24));p=query[selected]
    _,ids=tree.query(p,k=12);diff=p[:,None,:]-a[ids,:2]
    t=np.clip(np.sum(diff*vec[ids],axis=2)/l2[ids],0,1);residual=diff-t[:,:,None]*vec[ids]
    dd=np.sum(residual*residual,axis=2);row=np.arange(len(p));pick=dd.argmin(1);s=ids[row,pick];fraction=t[row,pick]
    d=np.sqrt(dd[row,pick]);floor=a[s,2]+fraction*(b[s,2]-a[s,2]);base=bed.ravel()[selected]
    bankwidth=width[s]+4.0
    coret=hydraulic.smooth((d-width[s]*.70)/np.maximum(width[s]*.30,.4));shelf=floor+.23
    target=np.where(d<=width[s],floor+.23*coret,shelf+(base-shelf)*hydraulic.smooth((d-width[s])/4.0))
    carved=np.minimum(base,target)
    edge=hydraulic.native(h,-1250,p[:,1]);join=hydraulic.smooth((-p[:,0]-1250)/10)
    bed.ravel()[selected]=edge*(1-join)+carved*join
    np.savez_compressed(OUT/'channel-paths.npz',a=a,b=b,arc=station)
    active=(distance<110)|((gx<-1220)&(bed<life.LAKE+1.5))|((gx<-1330)&old['active'])
    z=bed[active].astype(float);near=near.reshape(gx.shape)[active]
    seglen=np.sqrt(l2);grade=np.clip((a[:,2]-b[:,2])/seglen,.002,.15)
    depth_target=(.8*.055/(width[near]*2*np.sqrt(grade[near])))**.6
    reference=(a[near,2]+b[near,2])*.5+np.clip(depth_target,.08,.25)
    depth=np.where(distance[active]<width[near]+1,np.maximum(0,reference-z),0)
    depth=np.maximum(depth,np.maximum(0,life.LAKE-z))
    speed=np.minimum(1.4,.8/np.maximum(2*width[near]*depth_target,.15));direction=vec[near]/seglen[near,None]
    hu=depth*speed*direction[:,0];hv=depth*speed*direction[:,1]
    hu[distance[active]>width[near]+1]=0;hv[distance[active]>width[near]+1]=0
    np.savez_compressed(OUT/'flow-bake.npz',x=x,y=y,bed=bed,active=active,coverage=old['coverage'])
    np.savez_compressed(OUT/'initial-state.npz',x=x,y=y,cell_indices=np.flatnonzero(active),bed=z,h=depth,hu=hu,hv=hv)
    sources=[(float(p[0,0]),float(p[0,1]),q) for p,q in zip(paths,[.36,.22,.22])]
    (OUT/'sources.json').write_text(json.dumps(sources,indent=2))
    changed=abs(h-current)>.008;prefix=np.zeros((2018,2018),'<u4');prefix[1:,1:]=changed.cumsum(0).cumsum(1);prefix.tofile(OUT/'changed-prefix.u32')
    support=np.argwhere(changed);support=support[np.linspace(0,len(support)-1,24).astype(int)]
    (OUT/'support-checks.json').write_text(json.dumps([[-1250+i*STEP,-1250+j*STEP] for j,i in support]))
    report=dict(ok=True,course_source='Gaea headwaters plus reviewed authored valley-space control points',morphology='Whole middle/lower course: large irregular bends, asymmetric broad inside shelves, narrow outside banks; no raised berm',sediment_transport=False,
        maximum_cut_below_original_m=float((original-h).max()),changed_native_samples=int(changed.sum()),roads_protected_equal=True,local_mouth_protection_released=True,active_offline_cells=int(active.sum()),sources_m3s=sources,
        main_course_length_m=float(np.linalg.norm(np.diff(paths[0][:,:2],axis=0),axis=1).sum()),height_sha256=hashlib.sha256((OUT/'H_GaeaCreek_2017.r16').read_bytes()).hexdigest())
    (OUT/'shape-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
    plot(original,current,h,paths)

def plot(original,current,h,paths):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,2,figsize=(14,7),layout='constrained')
    old=np.load(BASE/'GaeaCreek/network-paths.npz')
    for ax,field,data,title in [(axs[0],original-current,[old[k] for k in old.files],'Rejected: retained straight lower course'),(axs[1],original-h,paths,'Candidate: whole-valley course and native gravel shelves')]:
        ax.imshow(field,origin='lower',extent=(-1250,1250,-1250,1250),cmap='cividis',vmin=0,vmax=1)
        for p in data:ax.plot(p[:,0],p[:,1],c='#50d7ff',lw=.65)
        ax.set(xlim=(-1280,-230),ylim=(-160,780),aspect='equal',title=title,xlabel='X (m)',ylabel='Y (m)')
    fig.suptitle('Native incision data — shape study, not an Unreal render')
    fig.savefig(OUT/'Native_Course_Plan.png',dpi=150);plt.close(fig)

def bake(seconds,resume):
    hydraulic.OUT=OUT;life.SOURCES=json.loads((OUT/'sources.json').read_text())
    hydraulic.bake(seconds,resume,initial_dir=OUT)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--seconds',type=float,default=0);p.add_argument('--resume',action='store_true');args=p.parse_args()
    if args.prepare:prepare()
    if args.seconds:bake(args.seconds,args.resume)
