"""Broad physical verge relief on the existing 1.24 m landscape grid."""
from pathlib import Path
import numpy as np,json,math
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreRelief';OUT.mkdir(parents=True,exist_ok=True)
ROAD=ROOT/'Art/Export/BenmoreRoads';baseline=OUT/'before_height_local_south_up.f32'
if not baseline.exists():baseline.write_bytes((ROAD/'height_local_south_up.f32').read_bytes())
n=2017;step=2500/2016;old=np.fromfile(baseline,dtype='<f4').reshape(n,n)
routes=json.loads((ROAD/'road-manifest.json').read_text())['routes']
clearance=np.full((n,n),1e6);arc=np.zeros((n,n));signed=np.zeros((n,n))
for r in routes:
    for p,q in zip(r['points'][:-1],r['points'][1:]):
        a=np.array([p['x_m'],p['y_m']]);b=np.array([q['x_m'],q['y_m']]);v=b-a;length=np.linalg.norm(v)
        if length<.001:continue
        reach=r['width_m']/2+8
        lo=np.maximum(0,np.floor((np.minimum(a,b)-reach+1250)/step).astype(int));hi=np.minimum(n-1,np.ceil((np.maximum(a,b)+reach+1250)/step).astype(int));sl=(slice(lo[1],hi[1]+1),slice(lo[0],hi[0]+1))
        x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)*step-1250,np.arange(lo[1],hi[1]+1)*step-1250)
        t=np.clip(((x-a[0])*v[0]+(y-a[1])*v[1])/(length*length),0,1)
        d=np.hypot(x-a[0]-t*v[0],y-a[1]-t*v[1])-r['width_m']/2;take=d<clearance[sl]
        arc[sl]=np.where(take,p['arc_m']+t*length,arc[sl]);signed[sl]=np.where(take,((y-a[1])*v[0]-(x-a[0])*v[1])/length,signed[sl]);clearance[sl]=np.minimum(clearance[sl],d)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
d=clearance;side=np.sign(signed)
patch=.5+.28*np.sin(arc*.13+side*1.7)+.22*np.sin(arc*.041+side*4.1)
envelope=.22+.78*smooth(.18,.82,patch)
gap=1-.88*np.exp(-((np.sin(arc*.21+side*2.8))/.20)**2)
ridge_centre=2.10+.22*np.sin(arc*.25+side)
bank=(.34+.24*patch)*np.exp(-((d-ridge_centre)/1.10)**2)*envelope*gap
ditch=(.24+.16*patch)*np.exp(-((d-3.75-.22*np.sin(arc*.11))/1.05)**2)*(.4+.6*envelope)
outer=.14*np.exp(-((d-5.05)/1.3)**2)*envelope
delta=(bank-ditch+outer)*smooth(1.05,1.65,d)*(1-smooth(6,7,d))*smooth(.8,2,old)
new=np.round((old+delta)*64)/64;actual=new-old
def height(grid,x,y):
    f=(x+1250)/step;g=(y+1250)/step;i=int(f);j=int(g);a=f-i;b=g-j
    return float((grid[j,i]*(1-a)+grid[j,i+1]*a)*(1-b)+(grid[j+1,i]*(1-a)+grid[j+1,i+1]*a)*b)
errors=[]
for r in routes:
    for p in r['points']:
        a=math.radians(p['yaw'])
        for off in [-1.4,0,1.4]:
            x=p['x_m']-math.sin(a)*off;y=p['y_m']+math.cos(a)*off
            errors.append(abs(height(new,x,y)-height(old,x,y)))
assert max(errors)<.002,max(errors)
assert np.max(np.abs(actual[d>7]))<.001
new.astype('<f4').tofile(OUT/'height_local_south_up.f32')
encoded=np.uint16(np.clip(np.round(new*64+32768),0,65535));rgba=np.zeros((n,n,4),np.uint8);rgba[:,:,0]=encoded>>8;rgba[:,:,1]=encoded&255;rgba[:,:,3]=255
Image.fromarray(rgba).save(OUT/'T_Benmore_VergeHeightRG.png')
# Height-import probes include maxima, minima and untouched terrain.
indices=[np.unravel_index(np.argmax(actual),actual.shape),np.unravel_index(np.argmin(actual),actual.shape)]
indices.extend((y,x) for y in range(100,2000,300) for x in range(100,2000,300))
report=dict(ok=True,max_raise_m=float(actual.max()),max_cut_m=float(-actual.min()),changed_vertices=int(np.count_nonzero(abs(actual)>.001)),running_surface_max_change_m=max(errors),running_surface_probes=len(errors),anchors=[dict(pixel=[int(x),int(y)],z_m=float(new[y,x])) for y,x in indices])
(OUT/'height-report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='anchors'},indent=2))
