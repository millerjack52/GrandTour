"""Read-only reconstruction of the original drainage-sampling phase."""
import numpy as np,json
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
import reshape_benmore_channel as s
from bake_benmore_river_life import terrain,old,SOURCES
def main():
    base=np.fromfile(s.BASE/'candidate/height_local_south_up.f32',dtype='<f4').reshape(s.N,s.N)
    installed=np.fromfile(s.BASE/'RiverLife/H_RiverLife_2017.r16',dtype='<u2').reshape(s.N,s.N)
    x=np.arange(s.life.BOUNDS[0],s.life.BOUNDS[2]+s.DX/2,s.DX);y=np.arange(s.life.BOUNDS[1],s.life.BOUNDS[3]+s.DX/2,s.DX)
    xx,yy=np.meshgrid(x,y);s.life.H=base;bed=terrain(xx,yy)
    yh,xh=np.meshgrid(np.linspace(-1250,1250,s.N),np.linspace(-1250,1250,s.N),indexing='ij')
    changed=np.flatnonzero(abs(base.ravel()-(installed.astype(float).ravel()-32768)/64)>.0079)
    # Limit evaluation to a wider bounding corridor around actual incision.
    points=np.c_[xh.ravel(),yh.ravel()];distance=cKDTree(points[changed]).query(points)[0]
    selected=np.flatnonzero(distance<12);points=points[selected]
    width=3.6+.6*np.sin(points[:,0]*.023+points[:,1]*.013);protect=np.load(s.BASE/'source/protect_2017.npy').ravel()[selected]
    reports=[]
    for j in range(3):
        for i in range(3):
            paths=[]
            for sx,sy,q in SOURCES:
                old.SOURCE=(sx,sy);line=old.drainage(bed[j::3,i::3],xx[j::3,i::3],yy[j::3,i::3])
                line[:,:2]=gaussian_filter1d(line[:,:2],1.15,axis=0,mode='nearest')
                line[:,2]=terrain(line[:,0],line[:,1]);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(line[:,:2],axis=0),axis=1))]
                paths.append(np.c_[line[:,:2],np.minimum.accumulate(line[:,2]-.48-.12*(.5+.5*np.sin(arc/37)))])
            channels=np.concatenate(paths);dist,near=cKDTree(channels[:,:2]).query(points)
            strength=(1-s.smooth((dist-.7)/(width-.7)))*(1-protect)
            delta=np.minimum(np.maximum(base.ravel()[selected]-channels[near,2],0),1.25)*strength
            reconstructed=np.uint16(np.rint((base.ravel()[selected]-delta)*64+32768))
            mismatch=int(np.count_nonzero(reconstructed!=installed.ravel()[selected]))
            report=dict(i=i,j=j,mismatch=mismatch,mean_abs_error_m=float(abs(reconstructed.astype(float)-installed.ravel()[selected]).mean()/64))
            reports.append(report);print(json.dumps(report),flush=True)
            if mismatch==0:
                np.savez_compressed(s.OUT/'original-paths.npz',**{str(k):p for k,p in enumerate(paths)})
                (s.OUT/'alignment.json').write_text(json.dumps(report,indent=2));return
    (s.OUT/'alignment-search.json').write_text(json.dumps(reports,indent=2))
    raise RuntimeError('Original path not recovered exactly')
if __name__=='__main__':main()
