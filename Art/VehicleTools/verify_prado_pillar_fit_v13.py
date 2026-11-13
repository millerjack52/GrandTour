"""Check the user's demonstrated wrong extent against the revised saved mesh."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools')
from prado_glazing_repair import edge_y
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
BASE=Path('C:/GrandTour/Art/Export/VehicleTools')
contract=json.loads((BASE/'prado-glazing-audit/windscreen-corner-repair-contract.json').read_text());ring=[p['co'] for p in contract['outer_ring']]
opening=Polygon([(p[0],p[2]) for p in ring])
target=Polygon(json.loads((BASE/'prado-glazing-v13/repair-report.json').read_text())['windscreen']['pane_outline_raw'])
results=[]
for rev in ['v11','v13']:
 bpy.ops.wm.open_mainfile(filepath=str(BASE/('prado-glazing-'+rev)/'Prado_Corrected.blend'))
 ob=bpy.data.objects['Glass | Windscreen'];vv=[ob.matrix_world@v.co/5 for v in ob.data.vertices]
 ff=[tuple(p.vertices) for p in ob.data.polygons]
 tree=BVHTree.FromPolygons(vv,ff)
 shapes=[]
 for ids in ff:
  po=Polygon([(vv[i].x,vv[i].z) for i in ids])
  if po.is_valid and po.area>1e-12:shapes.append(po)
 projection=unary_union(shapes)
 widths=[]
 for z in [.33,.34,.35,.36,.37,.38,.39,.395]:
  cut=LineString([(-.25,z),(.25,z)]);bounds=opening.intersection(cut).bounds;actual=projection.intersection(cut).bounds
  widths.extend([(actual[0]-bounds[0])*5000,(bounds[2]-actual[2])*5000])
 distances=[]
 for i in range(160):
  p=target.exterior.interpolate((i+.25)/160,normalized=True)
  desired=Vector((p.x,edge_y(ring,p.x,p.y)+.00065,p.y))
  distances.append(tree.find_nearest(desired)[3]*5000)
 results.append({'revision':rev,'max_side_setback_mm':max(widths),'min_side_setback_mm':min(widths),'max_distance_to_desired_pane_rim_mm':max(distances),'mean_distance_to_desired_pane_rim_mm':sum(distances)/len(distances),'pane_rim_samples':len(distances),'width_pass':max(widths)<9,'rim_fit_pass':max(distances)<1.0})
(BASE/'prado-glazing-v13/pillar-fit-verification.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
assert not results[0]['width_pass'],'Negative control failed to detect rejected narrow glass'
assert results[1]['width_pass'],results[1]
assert results[1]['rim_fit_pass'],results[1]
