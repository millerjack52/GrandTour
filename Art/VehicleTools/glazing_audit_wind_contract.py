import json,sys
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
O=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-audit');d=json.loads((O/'adjacent-loops.json').read_text())['Windscreen'];r=d[2];by={v['index']:v for v in r['boundary']}
assert all(len(v['edges'])==2 for v in by.values())
start=min(by,key=lambda k:(by[k]['co'][2],by[k]['co'][0]));order=[start];prev=None;cur=start
while True:
 nxt=next(i for i,p in by[cur]['edges'] if i!=prev)
 if nxt==start:break
 order.append(nxt);prev,cur=cur,nxt
assert len(order)==len(by)
poly=Polygon([(by[i]['co'][0],by[i]['co'][2]) for i in order]);assert poly.is_valid
rep={'coordinate_system':'source raw coords, multiply by5 in model',
 'outer_ring':[{'source_vertex':i,'co':by[i]['co']} for i in order],
 'surround_source_faces_to_remove':sorted(set(r['faces'])-set(d[0]['faces'])),
 'pane_source_faces_already_removed':d[0]['faces'],
 'verified_simple_loop':True,'degree_two_all_28_vertices':True,
 'construction':'Keep outer ring fixed, bridge to smooth symmetric inner pane/seal. Outer ring is within existing windshield surround and retains irregular triangulation offsets; do not use outer ring directly as finished visible glass edge.'}
(O/'windscreen-repair-contract.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep,indent=2))
