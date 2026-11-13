"""Check exported river triangles and road clearance without changing assets."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.spatial import cKDTree
from prepare_benmore_composition import A,B,WIDTH

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreRivers'

def run():
    # Sampling each road centreline at <= 1 m gives a conservative clearance
    # bound when the covering radius and largest half-width are subtracted.
    points=[];radius=0.
    for a,b in zip(A,B):
        length=np.linalg.norm(b-a);n=max(1,int(np.ceil(length)))
        points.extend(a+(b-a)*t for t in np.linspace(0,1,n+1))
        radius=max(radius,float(length/n/2))
    roads=cKDTree(points);assets=json.loads((OUT/'assets.json').read_text())
    rows=[]
    for part in assets['parts']+assets['bank_parts']:
        raw=json.loads((OUT/(part['name']+'.json')).read_text())
        v=np.asarray(raw['vertices'])+part['origin_m'];faces=np.asarray(raw['faces'])
        assert np.isfinite(v).all() and faces.min()>=0 and faces.max()<len(v)
        t=v[faces];ab=t[:,1,:2]-t[:,0,:2];ac=t[:,2,:2]-t[:,0,:2]
        area=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
        assert area.min()>1e-10,(part['name'],'folded or degenerate triangle',area.min())
        lower=float(roads.query(v[:,:2])[0].min()-radius-WIDTH.max())
        assert lower>40,(part['name'],'road clearance',lower)
        assert len(faces)==part['triangles'] and len(v)==part['vertices']
        rows.append(dict(mesh=part['name'],triangles=len(faces),road_edge_clearance_lower_bound_m=lower,min_projected_double_area_m2=float(area.min())))
    terrain_sha=hashlib.sha256((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes()).hexdigest()
    assert terrain_sha==json.loads((OUT/'bake-report.json').read_text())['height_sha256']
    report=dict(ok=True,parts=rows,terrain_sha256=terrain_sha,bake_sha256=hashlib.sha256((OUT/'river_bake.npz').read_bytes()).hexdigest())
    (OUT/'geometry-validation.json').write_text(json.dumps(report,indent=2))
    print('RIVER_GEOMETRY_OK',len(rows),'meshes; minimum road clearance',min(r['road_edge_clearance_lower_bound_m'] for r in rows))

if __name__=='__main__':run()
