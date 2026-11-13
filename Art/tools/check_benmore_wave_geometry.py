"""Numerical geometry bounds on actual water vertices; NOT an Unreal visual test."""
from pathlib import Path
import ast,json,math,hashlib
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'FlowWaves'
tree=ast.parse((ROOT/'Art/Unreal/benmore_flow_waves.py').read_text())
coarse=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='COARSE')
height_bound=sum(w[2] for w in coarse)

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def main():
    flow=np.asarray(Image.open(BASE/'Morphology/T_RS_DomainFlow.png')).astype(float)/255
    shore=np.asarray(Image.open(BASE/'ShoreRefinement/T_SR_Shore.png')).astype(float)/255
    rows=[]
    for name,folder in [('SM_GC_RiverSurface','ShoreRefinement'),('SM_GC_OutletSurface','FlowWaves')]:
        mesh=json.loads((BASE/folder/(name+'.json')).read_text());v=np.array(mesh['vertices']);f=np.array(mesh['faces']);q=v[:,:2]
        rgb=np.stack([map_coordinates(flow[:,:,i],[(q[:,1]+300)/1.25,(q[:,0]+1480)/1.25],order=1,mode='nearest') for i in range(3)],1)
        velocity=(rgb[:,:2]-.5)*4;depth=rgb[:,2]*2;speed=np.linalg.norm(velocity,axis=1)
        sd=map_coordinates(shore[:,:,1],[(q[:,1]+300)/.625,(q[:,0]+1480)/.625],order=1,mode='nearest')*4-2
        strength=np.minimum(1.35,.22*depth/height_bound)*smooth(.12,.85,speed)
        edge=smooth(.025,.18,depth)*smooth(.10,.75,sd)
        theta=np.arctan2(velocity[:,1],velocity[:,0])/math.tau*16
        lo=np.floor(theta);dw=smooth(0,1,theta-lo)
        sb=speed/.25;s0=np.floor(sb)*.25;sw=smooth(0,1,sb-np.floor(sb))
        def waves(t):
            h=np.zeros(len(v))
            for j in [0,1]:
                angle=(lo+j)*math.tau/16;c=np.cos(angle);s=np.sin(angle)
                px=q[:,0]*c+q[:,1]*s;py=-q[:,0]*s+q[:,1]*c
                for k in [0,1]:
                    x=px-(s0+k*.25)*t
                    raw=sum(a*np.sin(math.tau*(nx*x+ny*py)/12-w*t+phase) for nx,ny,a,w,phase in coarse)
                    h+=raw*(dw if j else 1-dw)*(sw if k else 1-sw)
            return h*strength*edge
        values=np.stack([waves(t) for t in [12,12+1/12,13,14.75,16.9]])
        assert np.isfinite(values).all()
        assert np.all(np.abs(values)<=depth[None,:]*.22+1e-10)
        assert np.max(np.abs(values[:,sd<=.10]),initial=0)<1e-10
        # Height actually varies spatially and temporally, rather than translating
        # the whole plane. Only samples, not GPU or visual acceptance.
        active=(speed>.65)&(depth>.12)&(sd>.8)
        assert active.sum()>50
        assert values[:,active].std()>.002
        assert np.sqrt(np.mean((values[2,active]-values[0,active])**2))>.003
        edge_max=max(np.linalg.norm(q[f[:,j]]-q[f[:,(j+1)%3]],axis=1).max() for j in range(3))
        rows.append(dict(name=name,vertices=len(v),triangles=len(f),max_edge_m=float(edge_max),
            sampled_max_absolute_cm=float(np.abs(values).max()*100),fast_interior_rms_cm=float(np.sqrt(np.mean(values[:,active]**2))*100),
            fast_interior_temporal_rms_cm=float(np.sqrt(np.mean((values[2,active]-values[0,active])**2))*100)))
    shortest=min(12/math.hypot(w[0],w[1]) for w in coarse)
    assert shortest>=4*.625
    report=dict(ok=True,unreal_validated=False,installed=False,scope='Numerical candidate geometry only, before distance fade',
        min_geometry_wavelength_m=shortest,unfaded_amplitude_bound_cm=height_bound*1.35*100,depth_fraction_cap=.22,meshes=rows)
    (OUT/'geometry-check-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
