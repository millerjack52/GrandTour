import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
blend=Path(args[0]) if args else Path('C:/GrandTour/Art/Export/VehicleTools/prado-cabin-v06/Prado_Cabin.blend')
P=blend.parent
bpy.ops.wm.open_mainfile(filepath=str(blend));dg=bpy.context.evaluated_depsgraph_get()
def tree(ob):
 o=ob.evaluated_get(dg);m=o.to_mesh();t=BVHTree.FromPolygons([o.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]);o.to_mesh_clear();return t
def objects(col):return [o for o in bpy.data.collections[col].objects if o.type=='MESH']
structure=objects('12 Cabin structure');seats=objects('13 Seats');trim=objects('16 Cabin trim')
body=objects('01 Body')+objects('10 Doors and closures')
trees={o.name:tree(o) for o in structure+seats+trim+body+objects('02 Glass')}
overlaps=[]
for w in objects('03 Road wheels'):
 if 'tyre carcass' not in w.name and 'all-terrain tread' not in w.name:continue
 t=tree(w)
 for o in structure+seats+body:
  hits=trees[o.name].overlap(t)
  if hits:overlaps.append((w.name,o.name,len(hits)))
print('TYRE',overlaps)
seatbody=[]
for s in seats:
 if not any(w in s.name for w in ['headrest','backrest','cushion','riser']):continue
 for o in body+objects('02 Glass')+trim:
  hits=trees[s.name].overlap(trees[o.name])
  if hits:seatbody.append((s.name,o.name,len(hits)))
print('SEAT vs SHELL GLASS TRIM',seatbody)
floorseat=[]
for s in seats:
 if not any(w in s.name for w in ['backrest','cushion','rail','riser']):continue
 for o in structure:
  hits=trees[s.name].overlap(trees[o.name])
  if hits:floorseat.append((s.name,o.name,len(hits)))
print('SEAT vs FLOOR',floorseat)
trimbody=[]
for s in trim:
 if not any(w in s.name for w in ['Headliner','Sun visor','Interior mirror','Rear mirror','Visor hinge','Interior lamp']):continue
 for o in body+objects('02 Glass'):
  hits=trees[s.name].overlap(trees[o.name])
  if hits:trimbody.append((s.name,o.name,len(hits)))
print('TRIM vs SHELL GLASS',trimbody)
report={'tyre_intersections':overlaps,'seat_shell_trim_intersections':seatbody,'seat_floor_intersections':floorseat,'trim_shell_intersections':trimbody}
(P/'cabin-audit.json').write_text(json.dumps(report,indent=2))
