import json
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-audit')
d=json.loads((O/'adjacent-loops.json').read_text());r=d['RearWindow'][2];by={v['index']:v for v in r['boundary']}
start=min(by,key=lambda k:(by[k]['co'][2],by[k]['co'][0]));order=[start];prev=None;cur=start
while True:
 nxt=next(i for i,p in by[cur]['edges'] if i!=prev)
 if nxt==start:break
 order.append(nxt);prev,cur=cur,nxt
assert len(order)==len(by)
report={'coordinate_system':'source normalized, front -Y, up Z; multiply all coordinates by 5 in delivered Blender scene',
 'rear_outer_ring':[{'source_vertex':i,'co':by[i]['co']} for i in order],
 'rear_tunnel_source_faces_to_remove':sorted(set(r['faces'])-set(d['RearWindow'][0]['faces'])),
 'rear_pane_source_faces_already_removed':d['RearWindow'][0]['faces'],
 'diagnosis':{'rear':'Original source had a 145-256 mm deep tunnel at working scale. Pane construction blindly reused inner opening. Relocate pane to outer ring rake with shallow deliberate seal; remove 40 tunnel triangles.',
 'windscreen':'Existing perimeter contains a 53.7 mm lower sill height jump and asymmetric sides. Arbitrary tessellation, subdivision and Laplacian smoothing interpolated this broken contour. Repair shared local sill contour and create regular curved grid; do not smooth glass alone.',
 'cowl':'CAB | aperture-fitted dashboard cowl copied irregular lower boundary and must be regenerated from repaired common glass/sill curve.'},
 'evidence_images':['source-rear.png','source-rear-quarter.png','source-front.png','source-front-quarter.png']}
(O/'repair-contract.json').write_text(json.dumps(report,indent=2))
print(O/'repair-contract.json')
