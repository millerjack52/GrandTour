import bpy,json,sys,ast
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01');S=3.6
if '--glb' in sys.argv:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'Panda_Assembly.glb'))
else:bpy.ops.wm.open_mainfile(filepath=str(P/'Panda_Assembly.blend'))
def tree(obs):
 v=[];f=[]
 for o in obs:
  off=len(v);v.extend(o.matrix_world@p.co for p in o.data.vertices);f.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons)
 return BVHTree.FromPolygons(v,f)
obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('SOURCE')];cabin=[o for o in obs if o.get('panda_cabin')]
tyres=tree([o for o in obs if o.name.endswith(' tyre')]);glass=tree([o for o in obs if o.name.endswith(' glass') and not o.get('panda_cabin')]);tubs=tree([o for o in obs if 'wheelhouse' in o.name and not o.get('panda_cabin')])
report={'tyre_intersections':[],'glazing_intersections':[],'seat_tub_intersections':[],'seat_control_intersections':[],'unbacked_feet':[]}
seats=[o for o in cabin if any(k in o.name for k in ['seat cushion','seat back','Rear bench cushion','Rear bench back','headrest'])]
controls=[o for o in cabin if any(k in o.name for k in ['Steering','Gear','Handbrake','shaped door card','armrest','map pocket','Dashboard','Instrument'])]
ctree=tree(controls);floor=tree([o for o in obs if o.name.startswith('Fitted floor bay')])
for o in cabin:
 t=tree([o])
 if t.overlap(tyres):report['tyre_intersections'].append(o.name)
 if t.overlap(glass):report['glazing_intersections'].append(o.name)
 if o in seats:
  if t.overlap(tubs):report['seat_tub_intersections'].append(o.name)
  if t.overlap(ctree):report['seat_control_intersections'].append(o.name)
 if 'floor foot' in o.name:
  vs=[o.matrix_world@v.co for v in o.data.vertices];x0=min(p.x for p in vs);x1=max(p.x for p in vs);y0=min(p.y for p in vs);y1=max(p.y for p in vs);z=min(p.z for p in vs)
  for fx in [.15,.5,.85]:
   for fy in [.15,.5,.85]:
    if floor.ray_cast(Vector((x0+(x1-x0)*fx,y0+(y1-y0)*fy,z+.002)),Vector((0,0,-1)),.035)[0] is None:report['unbacked_feet'].append(o.name)
report['cabin_meshes']=len(cabin);report['seat_meshes_checked']=len(seats);report['pass']=not any(report[k] for k in ['tyre_intersections','glazing_intersections','seat_tub_intersections','seat_control_intersections','unbacked_feet'])
(P/('cabin-fit-glb.json' if '--glb' in sys.argv else 'cabin-fit.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
