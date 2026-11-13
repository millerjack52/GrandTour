"""Inspect the actual quantized bed / baked water, separate from art acceptance."""
import json
import numpy as np
from scipy.ndimage import map_coordinates, label, binary_erosion
from build_benmore_morphology import OUT, STEP
from reshape_benmore_channel import native

def main():
    data=np.load(OUT/'flow-bake.npz');flow=json.loads((OUT/'flow-report.json').read_text())
    h=np.fromfile(OUT/'height_local_south_up.f32','<f4').reshape(2017,2017)
    r=json.loads((OUT/'morphology-controls.json').read_text())[0]
    s=np.array(r['s']);xy=np.array(r['xy']);normal=np.array(r['normal'])
    dx=float(data['x'][1]-data['x'][0]);sample=lambda a,p:map_coordinates(a,[(p[:,1]-data['y'][0])/dx,(p[:,0]-data['x'][0])/dx],order=1,mode='constant')
    sections=[]
    for station in [980,1025,1055,1090,1145,1215,1258,1295,1360,1420,1458,1490,1550]:
        center=np.array([np.interp(station,s,xy[:,k]) for k in [0,1]])
        n=np.array([np.interp(station,s,normal[:,k]) for k in [0,1]]);n/=np.linalg.norm(n)
        tangent=np.array([n[1],-n[0]])
        offset=np.arange(-24,24.001,.125);points=center+offset[:,None]*n
        depth=sample(data['depth'],points);speed=sample(data['vx'],points)*tangent[0]+sample(data['vy'],points)*tangent[1]
        wet=depth>.028;groups,count=label(wet)
        threads=[dict(width_m=float((groups==i).sum()*.125),
            estimated_discharge_m3s=float((depth*speed)[groups==i].sum()*.125),
            mean_offset_m=float(offset[groups==i].mean())) for i in range(1,count+1)]
        sections.append(dict(station_m=station,center_m=center.tolist(),wet_threads=threads))
    xx,yy=np.meshgrid(data['x'],data['y']);valid=(xx>=-1250)&data['active']
    error=np.max(abs(native(h,xx[valid],yy[valid])-data['bed'][valid]))
    river=data['wet']&(xx>-1240)
    edge=data['active']&~binary_erosion(data['active'],np.ones((3,3)))&(data['bed']>.8)
    report=dict(ok=bool(flow['ok'] and flow['converged'] and error<1e-6),
        native_bake_bed_max_error_m=float(error),
        maximum_artificial_edge_depth_m=float(data['depth'][edge].max()),
        river_depth_percentiles_m=np.percentile(data['depth'][river],[5,50,95,99,100]).tolist(),
        sections=sections,flow_validation=flow['validation'],
        short_split_sections=sum(sum(t['estimated_discharge_m3s']>.01 for t in q['wet_threads'])>=2 for q in sections),
        limits='Section discharges are interpolated estimates, not conservative solver face fluxes. Numerical checks do not establish natural appearance, driving feel or frame rate.')
    (OUT/'morphology-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    assert report['ok']

if __name__=='__main__':main()
