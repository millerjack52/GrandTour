import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import MultiPoint,Polygon,Point
O=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-window-repair-v05');bpy.ops.wm.open_mainfile(filepath=str(O/'Porsche_Window_Repair.blend'))
def tree(o):
 o.data.calc_loop_triangles();return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
trees=[tree(bpy.data.objects[n]) for n in ['Porsche original body - locally repaired','Cabin | rebuilt exterior shell']]+[tree(o) for o in bpy.data.collections['09 Rebuilt cabin interfaces'].objects if o.type=='MESH' and ('| fitted pane' in o.name or '| clean gasket' in o.name)]
report={};spec=json.loads((O/'repair-report.json').read_text());domains={n:Polygon(p['projection_boundary']) for p in spec['patches'] for n in p['apertures']}
for ob in bpy.data.collections['09 Rebuilt cabin interfaces'].objects:
 if '| fitted pane' not in ob.name:continue
 name=ob.name;ax=1 if name.startswith(('Windscreen','Rear glass')) else 0;sg=-1 if name.startswith('Windscreen') or ' R |' in name else 1;oth=[k for k in range(3) if k!=ax]
 ps=[v.co for v in ob.data.vertices];poly=MultiPoint([(p[oth[0]],p[oth[1]]) for p in ps]).convex_hull
 a=np.array([[1,p[oth[0]],p[oth[1]],p[oth[0]]**2,p[oth[0]]*p[oth[1]],p[oth[1]]**2] for p in ps]);co=np.linalg.lstsq(a,np.array([p[ax] for p in ps]),rcond=None)[0]
 missed=[];total=0;outside=[]
 for offset in [-.003,.003,.009,.015,.020]:
  ring=poly.buffer(offset).exterior
  for i in range(400):
   u,v=ring.interpolate(i/400,normalized=True).coords[0];d=float(np.dot(co,[1,u,v,u*u,u*v,v*v]));q=Vector();q[oth[0]]=u;q[oth[1]]=v;q[ax]=d+sg*.06;direction=Vector();direction[ax]=-sg
   hits=[t.ray_cast(q,direction,.12)[0] for t in trees];total+=1
   if not any(h is not None for h in hits):
    record={'offset':offset,'point':list(q)}
    if domains[name.split(' |')[0]].covers(Point(u,v)):missed.append(record)
    else:outside.append(record)
 report[name]={'samples':total,'misses_within_panel':len(missed),'missed_points':missed,'rays_outside_panel_silhouette':outside}
(O/'window-coverage.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:{a:b for a,b in v.items() if a!='missed_points'} for k,v in report.items()},indent=2))
