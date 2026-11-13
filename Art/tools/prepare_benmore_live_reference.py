"""Reconcile the bounded river mean to the runtime grid, without interior water sources.

Weighted flux projection enforces continuity on every non-boundary wet cell.
The reduced runtime wave solver evolves perturbations about this mean; it does
not claim that the offline bake solves its momentum equation or flooding.
"""
from pathlib import Path
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.ndimage import label

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'

def main():
    d=np.load(OUT/'reference_Ford.npz');h=d['depth_m'].astype('f8');h[h<.01]=0
    ny,nx=h.shape;c=float(d['cell_m']);wet=h>0
    boundary=np.zeros_like(wet);boundary[[0,-1],:]=True;boundary[:,[0,-1]]=True
    # Remove disconnected sub-centimetre bank puddles from the fixed-bank pilot.
    groups,n=label(wet)
    for i in range(1,n+1):
        if not np.any((groups==i)&boundary):h[groups==i]=0
    wet=h>0;interior=wet&~boundary;ids=np.full(h.shape,-1,int);ids[interior]=np.arange(interior.sum())
    qx=np.zeros_like(h);qy=np.zeros_like(h);kx=np.zeros_like(h);ky=np.zeros_like(h)
    kx[:,:-1]=np.where(wet[:,:-1]&wet[:,1:],np.minimum(h[:,:-1],h[:,1:]),0)
    ky[:-1]=np.where(wet[:-1]&wet[1:],np.minimum(h[:-1],h[1:]),0)
    qx[:,:-1]=kx[:,:-1]*c*.5*(d['velocity_x_mps'][:,:-1]+d['velocity_x_mps'][:,1:])
    qy[:-1]=ky[:-1]*c*.5*(d['velocity_y_mps'][:-1]+d['velocity_y_mps'][1:])
    def divergence(x,y):
        a=x+y;a[:,1:]-=x[:,:-1];a[1:]-=y[:-1];return a
    rows=[];cols=[];vals=[];diag=np.zeros(interior.sum())
    for y,x in zip(*np.where(interior)):
        a=ids[y,x]
        for j,i,k in [(y,x+1,kx[y,x]),(y,x-1,kx[y,x-1]),(y+1,x,ky[y,x]),(y-1,x,ky[y-1,x])]:
            if k<=0:continue
            diag[a]+=k
            if ids[j,i]>=0:rows.append(a);cols.append(ids[j,i]);vals.append(-k)
    rows.extend(range(len(diag)));cols.extend(range(len(diag)));vals.extend(diag)
    mat=coo_matrix((vals,(rows,cols)),shape=(len(diag),len(diag))).tocsr()
    phi=np.zeros_like(h);phi[interior]=spsolve(mat,-divergence(qx.copy(),qy.copy())[interior])
    qx[:,:-1]+=kx[:,:-1]*(phi[:,:-1]-phi[:,1:]);qy[:-1]+=ky[:-1]*(phi[:-1]-phi[1:])
    # A single global scale preserves continuity while limiting the fastest face.
    fastest=max(np.max(np.abs(qx)/np.maximum(kx*c,1e-12)),np.max(np.abs(qy)/np.maximum(ky*c,1e-12)))
    scale=min(1,1.5/max(fastest,1e-12));qx*=scale;qy*=scale
    qx=qx.astype('f4');qy=qy.astype('f4');h=h.astype('f4')
    residual=float(np.max(np.abs(divergence(qx.copy(),qy.copy())[interior])))
    assert residual<1e-7 and np.isfinite(phi).all()
    payload=dict(size_x=nx,size_y=ny,cell_cm=c*100,origin_cm=(d['origin_m']*100).tolist(),axis_x=d['axis_x'].tolist(),bed_cm=(d['bed_m']*100).flatten().tolist(),depth_m=h.flatten().tolist(),flux_x=qx.flatten().tolist(),flux_y=qy.flatten().tolist())
    (OUT/'live-reference.json').write_text(json.dumps(payload,separators=(',',':')))
    # Native automation consumes the exact same imported arrays (little endian, header then four planes).
    with (OUT/'live-reference.bin').open('wb') as f:
        np.array([nx,ny],'<i4').tofile(f);np.array([c*100,*d['origin_m']*100,*d['axis_x']],'<f4').tofile(f)
        for a in [d['bed_m']*100,h,qx,qy]:np.asarray(a,'<f4').tofile(f)
    report=dict(ok=True,wet_cells=int(wet.sum()),cells=nx*ny,max_interior_divergence_m3s=residual,velocity_scale=scale,max_face_speed_mps=fastest*scale,reference_volume_m3=float(h.sum()*c*c),model='Fixed-bank linearized advected waves over a projected baked mean; no flood/erosion claim')
    (OUT/'live-reference-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
