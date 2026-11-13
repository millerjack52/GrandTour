"""Subdivide only the coarse water apron, preserving the original piecewise plane.

No bed/terrain, water domain, shoreline, or physics edits. The native river and
moving interaction mesh are already 62.5cm; this matches the apron to them.
"""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement/SM_GC_OutletSurface.json'
OUT=SRC.parent.parent/'FlowWaves'

def main():
    OUT.mkdir(exist_ok=True);d=json.loads(SRC.read_text());v=np.array(d['vertices']);f=np.array(d['faces'])
    vertices=v.tolist();midpoints={};faces=[]
    def mid(a,b):
        edge=tuple(sorted((a,b)))
        if edge not in midpoints:
            midpoints[edge]=len(vertices);vertices.append(((v[a]+v[b])*.5).tolist())
        return midpoints[edge]
    for a,b,c in f.tolist():
        ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
        faces.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
    nv=np.array(vertices);nf=np.array(faces)
    def area(a,t):return .5*np.sum(np.cross(a[t[:,1]]-a[t[:,0]],a[t[:,2]]-a[t[:,0]])[:,2])
    assert np.array_equal(nv[:len(v)],v)
    assert np.max(np.abs(nv.min(0)-v.min(0)))<1e-10 and np.max(np.abs(nv.max(0)-v.max(0)))<1e-10
    assert abs(area(nv,nf)-area(v,f))<1e-7
    max_edge=max(np.linalg.norm(nv[nf[:,j],:2]-nv[nf[:,(j+1)%3],:2],axis=1).max() for j in range(3))
    assert max_edge<=np.sqrt(2)*.625+1e-8
    name='SM_GC_OutletSurface'
    (OUT/(name+'.json')).write_text(json.dumps(dict(vertices=vertices,faces=faces),separators=(',',':')))
    report=dict(ok=True,source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),old_triangles=len(f),new_triangles=len(nf),vertices=len(nv),max_edge_m=max_edge,area_m2=area(v,f),original_vertices_unchanged=True,midpoints_on_original_planes=True,bed_or_physics_changed=False)
    (OUT/'mesh-prepare-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
