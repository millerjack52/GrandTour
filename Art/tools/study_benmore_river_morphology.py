"""Research/audit and an isolated gravel-channel geometry experiment.

This writes only review/MorphologyResearch. It never imports a heightmap, edits
an installed course, launches Unreal or claims sediment/bank-migration physics.
The study's independent banks and low-flow threads interpret ORC's Lower Lindis
Figure 1. They are not a digitized survey: that figure has no metric scale.
"""
from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from reshape_benmore_channel import native
from benmore_shallow_water import step_for

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Art/Export/BenmoreGaea'
OUT=BASE/'review/MorphologyResearch'
DX=2500/2016
REFERENCE='https://www.orc.govt.nz/media/15692/relationships-between-flow-and-channel-braiding-in-the-lower-lindis-river-dean-olsen.pdf'

def checksum(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def protected_inputs():
    paths=[BASE/'CourseRevision/H_GaeaCreek_2017.r16',BASE/'CourseRevision/flow-bake.npz',
           BASE/'CourseRevision/course-controls.json',BASE/'candidate/height_local_south_up.f32']
    return {str(p.relative_to(ROOT)):checksum(p) for p in paths}

def audit():
    original=np.fromfile(BASE/'candidate/height_local_south_up.f32','<f4').reshape(2017,2017)
    installed=np.fromfile(BASE/'CourseRevision/height_local_south_up.f32','<f4').reshape(2017,2017)
    p=np.load(BASE/'CourseRevision/network-paths.npz')['0']
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))]
    # Exclude scenery outside the native Landscape; clamped native() values
    # beyond that boundary are not valid longitudinal profile observations.
    native_end=float(arc[np.flatnonzero(p[:,0]>=-1250)[-1]])
    z0=native(original,p[:,0],p[:,1]);z1=native(installed,p[:,0],p[:,1])
    edges=list(np.arange(0,native_end,300))+[native_end]
    rows=[]
    colors=['#b15345','#cf7950','#d99a53','#99946d','#639392','#407e8e']
    for i,(lo,hi) in enumerate(zip(edges[:-1],edges[1:])):
        drop0=float(np.interp(lo,arc,z0)-np.interp(hi,arc,z0))
        drop1=float(np.interp(lo,arc,z1)-np.interp(hi,arc,z1))
        grade=drop0/(hi-lo)*100
        hypothesis=('steep rocky / cascade candidate' if grade>7.5 else
                    'step-pool / rocky run candidate' if grade>3 else
                    'riffle / run transition candidate' if grade>1.5 else
                    'alluvial bar / pool-riffle candidate')
        rows.append(dict(station_start_m=lo,station_end_m=hi,length_m=hi-lo,
            original_terrain_drop_m=drop0,original_terrain_grade_percent=grade,
            installed_bed_grade_percent=drop1/(hi-lo)*100,
            morphology_hypothesis=hypothesis,field_classification=False))
    figure,axes=plt.subplots(1,2,figsize=(13,7.8),layout='constrained',
                            gridspec_kw={'width_ratios':[1,1.25]})
    # Crop for legibility, using data rather than editing an Unreal capture.
    x=np.linspace(-1250,1250,2017);j0=np.searchsorted(x,-170);j1=np.searchsorted(x,800)
    i0=0;i1=np.searchsorted(x,-200)
    patch=original[j0:j1,i0:i1]
    shade=LightSource(315,35).shade(patch,plt.get_cmap('gist_earth'),dx=DX,dy=DX,
                                  vert_exag=1,blend_mode='soft')
    axes[0].imshow(shade,origin='lower',extent=[x[i0],x[i1-1],x[j0],x[j1-1]])
    for i,row in enumerate(rows):
        lo,hi=row['station_start_m'],row['station_end_m'];q=p[(arc>=lo)&(arc<=hi)]
        axes[0].plot(q[:,0],q[:,1],color=colors[i%len(colors)],lw=2.4)
        mid=(lo+hi)/2;px=np.interp(mid,arc,p[:,0]);py=np.interp(mid,arc,p[:,1])
        axes[0].annotate(str(i+1),(px,py),xytext=(7,4),textcoords='offset points',
            fontsize=12,fontweight='bold',color='white',bbox={'facecolor':'#24363b','pad':2})
    axes[0].set(title='Installed path over pre-incision terrain',xlabel='World X (m)',ylabel='World Y (m)',aspect='equal')
    axes[1].plot(arc[arc<=native_end],z0[arc<=native_end],color='#8d755a',label='Pre-incision terrain')
    axes[1].plot(arc[arc<=native_end],z1[arc<=native_end],color='#274d68',lw=1,label='Installed bed at path')
    for i,row in enumerate(rows):
        lo,hi=row['station_start_m'],row['station_end_m']
        axes[1].axvspan(lo,hi,color=colors[i%len(colors)],alpha=.13)
        axes[1].text((lo+hi)/2,96,'%.1f%%' % row['original_terrain_grade_percent'],ha='center',fontsize=10)
    axes[1].set(xlabel='Distance along installed path (m)',ylabel='Local elevation (m)',
        title='Grade changes the channel type',ylim=(-3,103),xlim=(0,native_end))
    axes[1].legend(loc='upper right',bbox_to_anchor=(1,.91),fontsize=9)
    figure.suptitle('BENMORE CHANNEL DIAGNOSIS | terrain audit, not an Unreal render',fontsize=14)
    figure.savefig(OUT/'Reach_Diagnosis.png',dpi=150);plt.close(figure)
    report=dict(installed_art_state='Rejected by owner: unnatural shape',
        native_only=True,native_end_station_m=native_end,native_spacing_m=DX,reaches=rows,
        slope_classification_caveat='First-order hypotheses from Pacific Northwest studies, not calibrated Otago thresholds. Confinement, sediment supply, substrate and observations must also guide the design.',
        code_findings=['Banks derived from signed distance to one spline, with curvature widening.',
                       '70 percent of half-wet-width is a flat core; no independently shaped bar tops.',
                       'Sequential minimum downhill bed grade removes pool/riffle bed undulations.',
                       'Width driven largely by slope, not bankfull sediment corridor morphology.',
                       'Fixed-bed flow bake cannot erode banks, migrate a channel or deposit gravel.'])
    (OUT/'channel-morphology-audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

def study(seconds):
    # Metric dimensions below are art-study choices, not measured Lindis data.
    # Both sides of the gravel corridor have independent control sets. A
    # secondary chute joins one main channel; bars are discrete sediment bodies.
    upper=np.array([[0,10],[12,12],[31,8],[58,16],[77,17],[98,13],[120,17],
                    [146,10],[166,11],[182,-2],[199,-5],[216,-27],[240,-57]])
    lower=np.array([[0,-32],[17,-30],[36,-24],[60,-16],[72,-9],[101,-4],
                    [120,-3],[139,-7],[156,-13],[175,-14],[192,-27],[216,-43],[240,-65]])
    main=np.array([[0,-10],[15,-9],[32,-4],[50,1],[72,7],[98,6],[124,4],
                   [150,3],[175,-3],[200,-16],[218,-36],[240,-60]])
    branch=np.array([[0,-10],[15,-17],[32,-23],[48,-17],[67,-12],
                     [87,-7],[104,-1],[124,4],[240,-60]])
    x=np.arange(-5,245+DX/2,DX);y=np.arange(-85,40+DX/2,DX)
    xx,yy=np.meshgrid(x,y);cx=np.clip(xx,0,240)
    up=PchipInterpolator(upper[:,0],upper[:,1])(cx)
    low=PchipInterpolator(lower[:,0],lower[:,1])(cx)
    footprint=(yy>=low)&(yy<=up)
    slope=.01;reference=-slope*xx
    edge=np.minimum(up-yy,yy-low)
    # A broad shallow gravel shelf, then an outer soil bank only at its actual
    # edge. This is not a valley-width buffer around the water's spline.
    roughness=gaussian_filter(np.random.default_rng(91008).normal(size=xx.shape),1.8)
    roughness*=.018/max(roughness.std(),1e-12)
    bed=reference+.35+roughness
    bed+=.50*(1-np.clip(edge/2.6,0,1))
    bed=np.where(footprint,bed,reference+.85+np.maximum(-edge,0)*.02)
    maincurve=PchipInterpolator(main[:,0],main[:,1])
    mainy=maincurve(cx);maingrade=maincurve.derivative()(cx)
    width=np.interp(cx,[0,30,56,90,135,170,203,225,240],[5.2,6.8,4.3,5.1,7.7,4.4,6.3,4.1,5.5])
    # Separate low-flow groove, with non-monotone bedform relief. The enclosing
    # flood/gravel footprint is never computed by offsetting this path.
    d=abs(yy-mainy)/np.sqrt(1+maingrade**2);r=np.clip(d/(width/2),0,1)
    mainfloor=reference+sum(.055*np.exp(-((xx-s)/5.5)**2) for s in [45,133,204])
    mainfloor-=sum(.035*np.exp(-((xx-s)/11)**2) for s in [80,159])
    thread=mainfloor+.36*r*r
    bed=np.where(footprint,np.minimum(bed,thread),bed)
    branchcurve=PchipInterpolator(branch[:,0],branch[:,1]);by=branchcurve(cx)
    bd=abs(yy-by)/np.sqrt(1+branchcurve.derivative()(cx)**2)
    branch_active=(xx>=7)&(xx<=124)&footprint
    secondary=reference+.065+.31*np.clip(bd/2.25,0,1)**2
    bed=np.where(branch_active,np.minimum(bed,secondary),bed)
    # Discrete, tapered bars occupying the gravel shelf. They follow reference
    # anatomy; a true morphodynamic model would evolve these from transport.
    bars=np.zeros_like(bed)
    for bx,by,along,across,angle,crest in [(52,-9,26,5.2,.32,.49),
        (111,11,22,4,-.18,.46),(164,-10,19,3.8,-.1,.47)]:
        dx,dy=xx-bx,yy-by;c,s=np.cos(angle),np.sin(angle)
        u=(dx*c+dy*s)/along;v=(-dx*s+dy*c)/across
        cap=np.maximum(0,1-u*u-v*v)
        height=crest*cap**.65*np.clip(1-.22*u,.65,1.2)
        bars=np.maximum(bars,height)
        bed=np.where(footprint&(cap>0),np.maximum(bed,reference+height),bed)
    # Quantize the experiment to the same 1/64 m height increments as native
    # Landscape. The solver and geometry use that same quantized floor.
    bed=np.rint(bed*64)/64
    active=(distance_transform_edt(~footprint)*DX<4)|(footprint)
    ids=np.full(bed.shape,-1,np.int32);ids[active]=np.arange(active.sum())
    aa=[];bb=[];axes=[]
    for axis,(a,b) in enumerate([(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]):
        ok=(a>=0)&(b>=0);aa.extend(a[ok]);bb.extend(b[ok]);axes.extend([axis]*int(ok.sum()))
    a,b,axes=np.array(aa,np.int32),np.array(bb,np.int32),np.array(axes,np.int32)
    z=bed[active];h=np.maximum(0,reference[active]+.19-z)
    hu=h*np.maximum(0,1.0);hv=h*0
    src=np.flatnonzero((xx[active]-1.2)**2+(yy[active]+10)**2<2**2).astype(np.int64)
    weights=np.exp(-(z[src]-z[src].min())*10);weights/=weights.sum()
    reservoir=np.flatnonzero(xx[active]>240).astype(np.int64)
    level=-2.4+.19;initial=h.sum()*DX*DX;added=removed=negative=0.;t=0;rows=[]
    before=h.copy();started=time.monotonic();window=[]
    while t<seconds:
        dt=min(40,seconds-t)
        result=step_for(z,h,hu,hv,a,b,axes,DX,src,weights,.8,reservoir,level,dt,.045)
        added+=result[0];removed+=result[1];negative+=result[4];t+=dt
        error=h.sum()*DX*DX-initial-added-removed
        row=dict(time_s=t,outflow_m3s=-result[1]/dt,depth_change_m=float(abs(h-before).max()),
                 mass_residual_m3=float(error),wall_s=round(time.monotonic()-started,1))
        print(json.dumps(row),flush=True);rows.append(row)
        window.append((t,h.copy(),hu/np.maximum(h,.001),hv/np.maximum(h,.001)))
        window=window[-6:]
        before=h.copy()
    depth=np.zeros_like(bed);depth[active]=h
    vx=depth.copy();vy=depth.copy();vx[active]=hu/np.maximum(h,.001);vy[active]=hv/np.maximum(h,.001)
    def face_flow(station):
        col=int(np.clip(np.searchsorted(x,station),1,len(x)-1))
        left,right=depth[:,col-1],depth[:,col]
        crest=np.maximum(bed[:,col-1],bed[:,col])
        hl=np.maximum(0,bed[:,col-1]+left-crest)
        hr=np.maximum(0,bed[:,col]+right-crest)
        ul,ur=vx[:,col-1],vx[:,col]
        signal=np.maximum(abs(ul)+np.sqrt(9.81*hl),abs(ur)+np.sqrt(9.81*hr))
        flux=.5*(hl*ul+hr*ur-signal*(hr-hl))*DX
        groups,count=label(np.maximum(left,right)>.025)
        discharges=[float(flux[groups==k].sum()) for k in range(1,count+1)]
        return dict(x_face_m=float((x[col-1]+x[col])/2),
                    face_total_discharge_m3s=float(flux.sum()),
                    wet_thread_discharges_m3s=discharges,
                    flowing_threads=int(sum(q>.01 for q in discharges)))
    wet=depth>.025;lab,n=label(wet,np.ones((3,3)))
    inlet_labels=np.unique(lab[(xx<5)&wet]);outlet_labels=np.unique(lab[(xx>235)&wet])
    connected=bool(set(inlet_labels)-{0} & (set(outlet_labels)-{0}))
    widths=[]
    for station in [30,70,108,146,175,210]:
        tangent=float(maincurve.derivative()(station));normal=np.array([-tangent,1.])/np.sqrt(1+tangent*tangent)
        transverse=np.arange(-60,60+DX/2,DX/4)
        qx=station+normal[0]*transverse;qy=float(maincurve(station))+normal[1]*transverse
        values=map_coordinates(depth,[(qy-y[0])/DX,(qx-x[0])/DX],order=1,mode='constant',cval=0)>.025
        _,count=label(values)
        widths.append(dict(station_m=station,wet_threads=int(count),total_wet_width_m=float(values.sum()*DX/4),
                           transect='Normal to primary channel tangent; all intersected threads',
                           finite_volume_face_flow=face_flow(station)))
    assert np.all(np.isfinite(bed)) and np.all(np.isfinite(depth))
    assert np.all(np.isfinite(vx)) and np.all(np.isfinite(vy))
    assert np.all(depth>=0)
    # Actual flow-produced surface/wetness; no drawn water polygon used for plot.
    fig,axs=plt.subplots(2,1,figsize=(13,9),layout='constrained',sharex=True,sharey=True)
    rgba=np.zeros((*bed.shape,3));rgba[:]=[.66,.62,.48]
    rgba[footprint]=[.70,.68,.61];rgba[(bars>.18)&footprint]=[.79,.76,.64]
    axs[0].imshow(rgba,origin='lower',extent=[x[0],x[-1],y[0],y[-1]],aspect='equal')
    levels=reference+.02-bed
    axs[0].contour(xx,yy,levels,levels=[0],colors=['#9b865c'],linewidths=.5)
    for data in [upper,lower]:
        s=np.linspace(0,240,601);axs[0].plot(s,PchipInterpolator(data[:,0],data[:,1])(s),c='#564f3b',lw=.8)
    axs[0].set_title('Independent gravel-bed edges and discrete bars | geometry study')
    axs[0].annotate('Tapered bar between two channels',(52,-9),xytext=(14,-53),
        arrowprops={'arrowstyle':'->'},fontsize=10,bbox={'facecolor':'white','alpha':.8,'pad':3})
    axs[0].annotate('Narrowing gravel corridor',(218,-36),xytext=(144,27),
        arrowprops={'arrowstyle':'->'},fontsize=10,bbox={'facecolor':'white','alpha':.8,'pad':3})
    rgba[wet]=np.stack([.17+.10*np.clip(depth[wet]/.4,0,1),.37+.08*np.clip(depth[wet]/.4,0,1),
                       .40+.06*np.clip(depth[wet]/.4,0,1)],axis=1)
    axs[1].imshow(rgba,origin='lower',extent=[x[0],x[-1],y[0],y[-1]],aspect='equal')
    q=(wet)&(depth>.04);jj,ii=np.where(q);take=np.arange(0,len(ii),16)
    axs[1].quiver(x[ii[take]],y[jj[take]],vx[jj[take],ii[take]],vy[jj[take],ii[take]],
                  color='#d8f2f0',scale=90,width=.0015)
    axs[1].set_title('Water occupancy produced by the fixed-bed bake | %.0f simulated seconds' % t)
    for ax in axs:ax.set(xlim=(-5,245),ylim=(-80,35),ylabel='Cross-valley position (m)')
    axs[1].set_xlabel('Study distance downstream (m)')
    fig.suptitle('CHANNEL ANATOMY EXPERIMENT | not the installed level or a surveyed Lindis copy',fontsize=14)
    fig.savefig(OUT/'Channel_Anatomy_Study.png',dpi=150);plt.close(fig)
    np.savez_compressed(OUT/'anatomy-study.npz',x=x,y=y,bed=bed,depth=depth,vx=vx,vy=vy,
                        footprint=footprint,bars=bars,upper=upper,lower=lower,main=main,branch=branch)
    t0,h0,u0,v0=window[0];visible=(h>.05)&(h0>.05)
    drift=float(abs(h-h0)[visible].max()) if seconds>=200 else None
    velocity_drift=float(np.hypot(hu/np.maximum(h,.001)-u0,hv/np.maximum(h,.001)-v0)[visible].max())
    # Explicit border check on the study's artificial active-domain boundary.
    from scipy.ndimage import binary_erosion
    edge=active&~binary_erosion(active,np.ones((3,3)))
    edgewet=int(np.count_nonzero(edge&(depth>.05)&(xx>5)&(xx<235)))
    report=dict(reference=REFERENCE,reference_figure='Figure 1, PDF page 2',
        shape_method='Independently authored gravel corridor, discrete tapered bars, separate low-flow grooves; solve wet occupancy from bed',
        source_metric_scale_available=False,metric_dimensions_are_study_choices=True,
        river_shape_simulated=False,sediment_transport=False,installed=False,
        terrain_spacing_m=DX,height_quantization_m=1/64,simulated_seconds=t,discharge_m3s=.8,
        active_cells=int(active.sum()),mass_residual_m3=float(error),positivity_correction_m3=negative,
        inlet_outlet_connected=connected,last_outflow_m3s=rows[-1]['outflow_m3s'],
        last_depth_change_m=rows[-1]['depth_change_m'],depth_drift_200s_m=drift,
        stability_window_s=t-t0,visible_velocity_drift_mps=velocity_drift,artificial_side_edge_wet_cells=edgewet,
        visible_depth_percentiles_m=np.percentile(depth[wet],[5,50,95]).tolist(),sections=widths,
        flow_is_converged=bool(abs(rows[-1]['outflow_m3s']-.8)<.028 and drift is not None and drift<.003 and velocity_drift<.01 and connected and edgewet==0 and negative<1e-7 and abs(error)<1e-7),
        history=rows)
    (OUT/'anatomy-study-report.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--audit',action='store_true')
    parser.add_argument('--study-seconds',type=float,default=0);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);before=protected_inputs()
    if args.audit:audit()
    if args.study_seconds:study(args.study_seconds)
    after=protected_inputs();assert before==after,'Research changed installed-course inputs'
    (OUT/'preservation-report.json').write_text(json.dumps(dict(installed_inputs_unchanged=True,hashes=after),indent=2))
