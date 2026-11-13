import json,sys
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon,LineString
O=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-audit');R=O.parent/'prado-glazing-v11'
contract=json.loads((O/'windscreen-corner-repair-contract.json').read_text());ring=[p['co'] for p in contract['outer_ring']];report=json.loads((R/'repair-report.json').read_text())['windscreen']
outer=Polygon([(x,z) for x,y,z in ring]);seal=Polygon(report['smooth_seal_outline_raw']);pane=seal.buffer(-.001,join_style=1)
def bounds_at(poly,z):
 line=poly.intersection(LineString([(-.25,z),(.25,z)]));return line.bounds[0],line.bounds[2]
rows=[]
for z in [.32,.33,.34,.35,.36,.37,.38,.39,.40]:
 a,b=bounds_at(outer,z);u,v=bounds_at(pane,z);rows.append({'z_raw':z,'pillar_inner_lip_x_raw':[a,b],'v11_pane_x_raw':[u,v],'v11_setback_mm_left_right':[(u-a)*5000,(b-v)*5000],'v12_target_approx_pane_x_raw':[a+.0013,b-.0013]})
(O/'windscreen-width-negative-control.json').write_text(json.dumps({'rows':rows,'note':'True fit requires testing lateral glass extent, not just ring-to-body boundary coincidence. v11 source-aware joint matched exactly while handdrawn pane width was44-70mm too inset at sides.'},indent=2));print(json.dumps(rows,indent=2))
