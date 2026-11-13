import json,sys,math
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
import numpy as np
O=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-audit');ring=[p['co'] for p in json.loads((O/'windscreen-corner-repair-contract.json').read_text())['outer_ring']];rows=json.loads((O/'windscreen-width-negative-control.json').read_text())['rows'];arr=np.array(ring);z0=min(arr[:,2]);dz=max(arr[:,2])-z0;w=max(abs(arr[:,0]));co=np.linalg.lstsq(np.array([[1,(z-z0)/dz,((z-z0)/dz)**2,(x/w)**2] for x,y,z in ring]),arr[:,1],rcond=None)[0]
def yfit(x,z):
 t=(z-z0)/dz;return float(co@np.array([1,t,t*t,(x/w)**2]))+.00065-.0007*max(0,1-(x/w)**2)*max(0,4*t*(1-t))
def edge_y(sign,z):
 hits=[]
 for a,b in zip(ring,ring[1:]+ring[:1]):
  if (a[2]<=z<=b[2] or b[2]<=z<=a[2]) and abs(a[2]-b[2])>1e-10:
   t=(z-a[2])/(b[2]-a[2]);x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1]);hits.append((x,y))
 return (min(hits) if sign<0 else max(hits))
out=[]
for r in rows:
 z=r['z_raw'];pairs=[edge_y(s,z) for s in [-1,1]];vals=[yfit(x,z) for x in r['v12_target_approx_pane_x_raw']]
 out.append({'z_raw':z,'actual_lip_xy':pairs,'new_pane_edge_y_if_analytic_unchanged':vals,'pane_Y_behind_lip_mm':[(v-p[1])*5000 for v,p in zip(vals,pairs)]})
(O/'windscreen-depth-analysis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
