"""Measure sampled-point scalloping and protected crossing cross-sections."""
import json
import numpy as np
from scipy.ndimage import gaussian_filter1d
import reshape_benmore_channel as s

def main():
    base=np.fromfile(s.BASE/'candidate/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    old=np.fromfile(s.BASE/'RiverLife/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    new=np.fromfile(s.OUT/'height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
    paths=np.load(s.OUT/'original-paths.npz');p=paths['0'][:,:2]
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    station=np.arange(0,arc[-1],.25);xy=np.c_[np.interp(station,arc,p[:,0]),np.interp(station,arc,p[:,1])]
    tangent=np.gradient(xy,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    normal=np.c_[-tangent[:,1],tangent[:,0]]
    selected=(xy[:,0]>-725)&(xy[:,0]<-550)&(xy[:,1]>105)&(xy[:,1]<310)&(np.linalg.norm(xy-[-661.25,177.5],axis=1)>16)
    widths={};cross=np.arange(-8,8.001,.05)
    for name,h in [('before',old),('after',new)]:
        pts=xy[:,None,:]+normal[:,None,:]*cross[None,:,None]
        cut=s.native(base,pts[...,0],pts[...,1])-s.native(h,pts[...,0],pts[...,1])
        widths[name]=np.sum(cut>.10,axis=1)*.05
    details={}
    for name,w in widths.items():
        ripple=w-gaussian_filter1d(w,40)
        details[name]=dict(incision_width_percentiles_m=np.percentile(w[selected],[5,50,95]).tolist(),short_scale_width_ripple_rms_m=float(np.sqrt(np.mean(ripple[selected]**2))))
    decrease=1-details['after']['short_scale_width_ripple_rms_m']/details['before']['short_scale_width_ripple_rms_m']
    crossings=json.loads((s.BASE/'RiverLife/assets.json').read_text())['crossings'];checks=[]
    for c in crossings:
        center=np.array(c['center_m'][:2]);n=np.array(c['cross_direction']);t=np.linspace(-11,11,221);q=center+n*t[:,None]
        error=float(np.max(abs(s.native(old,q[:,0],q[:,1])-s.native(new,q[:,0],q[:,1]))))
        assert error==0,(c['name'],error);checks.append(dict(name=c['name'],cross_section_max_change_m=error))
    assert decrease>.65,decrease
    report=dict(ok=True,measurement='Incision width above 10 cm along the recovered river path, excluding protected crossing; residual after a 10 m Gaussian station filter',widths=details,short_scale_ripple_reduction_fraction=decrease,crossings=checks)
    (s.OUT/'shape-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
