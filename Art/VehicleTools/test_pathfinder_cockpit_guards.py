"""Negative controls modify an in-memory copy only; never save the damaged model."""
import sys,json
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1])
s=Path('C:/GrandTour/Art/VehicleTools/verify_pathfinder_cockpit.py').read_text()
mutation="""
# Deliberately put one bench into the wheelhouse and narrow the floor.
for ob in bpy.data.collections['16 | Pathfinder mounted seats'].objects:
 if ob.name.startswith('Rear bench 1 |'):ob.location.x+=.22
floor=bpy.data.objects['Floor | fitted passenger and cargo pan'];floor.scale.x=.55
bpy.context.view_layer.update();pan=bvh(floor)
"""
s=s.replace("cockpit=json.loads",mutation+"\ncockpit=json.loads").replace("out/'cockpit-assembly-checks.json'","out/'negative-control-checks.json'")
try:exec(compile(s,'<deliberate bad assembly>','exec'))
except AssertionError:pass
r=json.loads((out/'negative-control-checks.json').read_text())
assert not r['passed'] and r['seat_wheelhouse_containment'] and r['seat_floor_projection']['missing']>0
print('NEGATIVE CONTROLS DETECTED: wheelhouse containment and uncovered seat bases. No blend saved.')
