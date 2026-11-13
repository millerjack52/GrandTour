import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
from shapely.ops import unary_union
P=Path('C:/GrandTour/Art/Export/VehicleTools/ferrari288-good-working-v01')
d=json.loads((P/'body-data.json').read_text());vs=[Vector(v) for v in d['verts']];out={}
for name,axes,selector in [
 ('side',((0,1,0),(0,0,1)),lambda c:c.x>.10 and c.z>.24),
 ('front',((1,0,0),(0,.83,.55)),lambda c:c.y<.025 and c.z>.255 and abs(-.55*c.y+.83*c.z-.347)<.038),
 ('rear',((1,0,0),(0,-.85,.527)),lambda c:c.y>.04 and c.z>.21)]:
 a,b=map(Vector,axes);n=a.cross(b).normalized();n*=(-1 if name=='rear' else 1);polys=[];edges=[]
 for f in d['polys']:
  pts=[vs[i] for i in f];c=sum(pts,Vector())/len(pts)
  if not selector(c):continue
  p=Polygon([(v.dot(a),v.dot(b)) for v in pts])
  if p.is_valid and p.area>1e-10:
   polys.append(p)
   edges.extend([(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts))])
 merged=unary_union(polys).buffer(.00005).buffer(-.00005)
 items=[merged] if merged.geom_type=='Polygon' else list(merged.geoms)
 rings=[]
 for p in items:
  for r in p.interiors:
   if Polygon(r).area<.0003:continue
   ring=Polygon(r).simplify(.00018,preserve_topology=True);pts=[]
   for uv in list(ring.exterior.coords)[:-1]:
    candidates=[]
    q=Vector(uv)
    for v,w in edges:
     v2=Vector((v.dot(a),v.dot(b)));w2=Vector((w.dot(a),w.dot(b)));e=w2-v2
     t=max(0,min(1,(q-v2).dot(e)/max(e.length_squared,1e-14)));distance=(v2+t*e-q).length
     candidates.append((distance,(v+t*(w-v)).dot(n)))
    nearest=min(e[0] for e in candidates);dep=max(z for d,z in candidates if d<nearest+.00007)
    pts.append([*uv,dep])
   X=np.array([[1,x,y,x*x,x*y,y*y] for x,y,z in pts]);Z=np.array([z for x,y,z in pts]);coef=np.linalg.lstsq(X,Z,rcond=None)[0];err=X@coef-Z
   rings.append({'ring':pts,'coef':coef.tolist(),'fit_error_max':float(abs(err).max()),'axes':[list(a),list(b),list(n)]})
 out[name]=rings
 print(name,[(len(p['ring']),p['fit_error_max'],[min(q[i] for q in p['ring']) for i in range(3)],[max(q[i] for q in p['ring']) for i in range(3)]) for p in rings])
# Rear hatch: the projection sees the interior through the opening, so use the
# inspected outer lip landmarks instead of treating the occluding floor as glass.
rear=[(-.1062,.1707,.3721),(-.0789,.1687,.3745),(-.0496,.1682,.3755),(-.0002,.1682,.376),(.0491,.1682,.376),(.0784,.1692,.3745),(.1057,.1711,.3721),(.1106,.177,.3706),(.1223,.2673,.3516),(0,.267,.355),(-.1228,.2668,.3516),(-.1111,.1765,.3706)]
# This transition is strongly curved in the source; use cubic longitudinal terms.
X=np.array([[1,x,y,x*x,x*y,y*y] for x,y,z in rear]);Z=np.array([z for x,y,z in rear]);coef=np.linalg.lstsq(X,Z,rcond=None)[0]
out['rear']=[{'ring':rear,'coef':coef.tolist(),'fit_error_max':float(abs(X@coef-Z).max()),'axes':[[1,0,0],[0,1,0],[0,0,1]]}]
(P/'apertures.json').write_text(json.dumps(out))
