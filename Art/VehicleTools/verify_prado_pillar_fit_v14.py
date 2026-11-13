import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_glazing_repair import edge_y
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
BASE=Path('C:/GrandTour/Art/Export/VehicleTools');OUT=BASE/'prado-glazing-v14'
report=json.loads((OUT/'repair-report.json').read_text());ring=report['windscreen']['fixed_outer_ring_raw'];opening=Polygon([(p[0],p[2]) for p in ring]);target=Polygon(report['windscreen']['pane_outline_raw'])
diag=report['windscreen']['depth_fit'];c=diag['coefficients'];xs=diag['x_scale_raw'];zc=diag['z_center_raw'];zs=diag['z_scale_raw']
def surface(x,z):
 u=x/xs;v=(z-zc)/zs;terms=[1,u,v,u*u,u*v,v*v,u*u*v,u*v*v,u*u*v*v];return sum(a*b for a,b in zip(c,terms))
def tree(ob):
 return BVHTree.FromPolygons([ob.matrix_world@v.co/5 for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons])
results=[]
for rev in ['v11','v14']:
 bpy.ops.wm.open_mainfile(filepath=str(BASE/('prado-glazing-'+rev)/'Prado_Corrected.blend'))
 ob=bpy.data.objects['Glass | Windscreen'];vv=[ob.matrix_world@v.co/5 for v in ob.data.vertices];ff=[tuple(p.vertices) for p in ob.data.polygons];gt=tree(ob)
 shapes=[]
 for ids in ff:
  poly=Polygon([(vv[i].x,vv[i].z) for i in ids])
  if poly.is_valid and poly.area>1e-12:shapes.append(poly)
 projection=unary_union(shapes);widths=[]
 for z in [.33,.34,.35,.36,.37,.38,.39,.395]:
  cut=LineString([(-.25,z),(.25,z)]);bounds=opening.intersection(cut).bounds;actual=projection.intersection(cut).bounds;widths.extend([(actual[0]-bounds[0])*5000,(bounds[2]-actual[2])*5000])
 distances=[]
 for i in range(160):
  p=target.exterior.interpolate((i+.25)/160,normalized=True);distances.append(gt.find_nearest(Vector((p.x,surface(p.x,p.y),p.y)))[3]*5000)
 result={'revision':rev,'max_side_setback_mm':max(widths),'min_side_setback_mm':min(widths),'max_distance_to_fair_pane_rim_mm':max(distances),'pane_rim_samples':len(distances),'width_pass':max(widths)<9,'rim_fit_pass':max(distances)<.5}
 if rev=='v14':
  body=tree(bpy.data.objects['Prado | fixed shell and underbody']);ds=[]
  for a,b in zip(ring,ring[1:]+ring[:1]):
   for t in [.0,.25,.5,.75]:ds.append(body.find_nearest(Vector(a).lerp(Vector(b),t))[3]*5000)
  result.update({'body_join_samples':len(ds),'maximum_new_boundary_to_body_distance_mm':max(ds),'body_join_pass':max(ds)<.05})
 results.append(result)
(OUT/'pillar-fit-verification.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
assert not results[0]['width_pass'],'Must detect rejected narrow pane'
assert results[1]['width_pass'] and results[1]['rim_fit_pass'] and results[1]['body_join_pass'],results[1]
