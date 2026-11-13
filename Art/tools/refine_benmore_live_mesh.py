"""Conforming local refinement for the 48 x 24 m live river window only.
Keeps every original vertex and surface plane. No terrain or road edits.
"""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import map_coordinates
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'

def main():
    d=json.loads((ROOT/'Art/Export/BenmoreGaea/RiverLife/SM_RL_Stream.json').read_text())
    ref=json.loads((OUT/'live-reference.json').read_text());nx,ny=ref['size_x'],ref['size_y'];cell=ref['cell_cm']/100
    o=np.array(ref['origin_cm'])/100;ax=np.array(ref['axis_x']);ay=np.array([-ax[1],ax[0]])
    verts=np.array(d['vertices']);faces=np.array(d['faces']);original=verts.copy();before=len(faces)
    surface=(np.array(ref['bed_cm'])/100+ref['depth_m']).reshape(ny,nx);depth=np.array(ref['depth_m']).reshape(ny,nx)
    def local(v):return np.stack([(v[...,:2]-o)@ax,(v[...,:2]-o)@ay],-1)
    def sample(a,p):
        uv=local(p)/cell-.5
        return map_coordinates(a,[uv[...,1],uv[...,0]],order=1,mode='nearest')
    def displaced(v):
        uv=local(v);edge=np.minimum(uv-cell/2,np.array([nx,ny])*cell-cell/2-uv).min(-1)
        t=np.clip(edge/3.5,0,1);w=t*t*(3-2*t)
        return v[:,2]+(sample(surface,v)-v[:,2])*w
    def error():
        p=verts[faces].mean(1);uv=local(p);core=(uv[:,0]>4)&(uv[:,0]<44)&(uv[:,1]>4)&(uv[:,1]<20)&(sample(depth,p)>.03)
        z=displaced(verts);err=abs(z[faces].mean(1)-displaced(p))[core]
        return {'triangles':int(core.sum()),'p95_cm':float(np.quantile(err,.95)*100),'max_cm':float(err.max()*100)}
    initial=error()
    for _ in range(2):
        uv=local(verts[faces].mean(1));selected=(uv[:,0]>-2)&(uv[:,0]<50)&(uv[:,1]>-2)&(uv[:,1]<26)
        edges=set()
        for a,b,c in faces[selected]:edges.update([tuple(sorted((a,b))),tuple(sorted((b,c))),tuple(sorted((c,a)))])
        vv=verts.tolist();mid={}
        for a,b in sorted(edges):mid[a,b]=len(vv);vv.append(((verts[a]+verts[b])/2).tolist())
        ff=[]
        for tri in faces.tolist():
            m=[mid.get(tuple(sorted((tri[k],tri[(k+1)%3])))) for k in range(3)]
            count=sum(x is not None for x in m)
            if count==0:ff.append(tri)
            elif count==3:
                a,b,c=tri;ab,bc,ca=m;ff.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
            elif count==1:
                k=next(i for i,x in enumerate(m) if x is not None);a,b,c=[tri[(k+j)%3] for j in range(3)];ab=m[k];ff.extend([[a,ab,c],[ab,b,c]])
            else:
                k=next(i for i in range(3) if m[i] is not None and m[(i+1)%3] is not None)
                a,b,c=[tri[(k+j)%3] for j in range(3)];ab,bc=m[k],m[(k+1)%3];ff.extend([[b,bc,ab],[a,ab,c],[ab,bc,c]])
        verts=np.array(vv);faces=np.array(ff)
    assert np.array_equal(verts[:len(original)],original)
    area=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]])[:,2]
    assert np.all(area>0),'Winding flipped'
    d.update(vertices=verts.tolist(),faces=faces.tolist())
    (OUT/'SM_RS_StreamLive.json').write_text(json.dumps(d,separators=(',',':')))
    report=dict(ok=True,original_triangles=before,refined_triangles=len(faces),original_vertices=len(original),refined_vertices=len(verts),reference_surface_error_before=initial,reference_surface_error_after=error(),original_vertices_unchanged=True)
    (OUT/'live-mesh-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
