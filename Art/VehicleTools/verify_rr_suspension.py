"""Reopen the saved library: topology plus contact relationships that topology cannot prove."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(OUT/'GT_RangeRover_Suspension_Components.blend'))
checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
def bounds(o):
 v=[o.matrix_world@p.co for p in o.data.vertices]
 return [(min(p[i] for p in v),max(p[i] for p in v)) for i in range(3)]
for c in bpy.data.collections:
 if c.get('kind')!='suspension':continue
 if c.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(c)
 bpy.context.view_layer.update()
 obs=[o for o in c.objects if o.type=='MESH']
 for o in obs:
  bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
  check(o.name+' closed with UVs',bad==0 and bool(o.data.uv_layers))
 for end in ['lower','upper']:
  seat=next(o for o in obs if end+' pressed seat' in o.name); stud=next(o for o in obs if end+' mounting stud' in o.name)
  z=sum(bounds(seat)[2])/2-.002
  tree=BVHTree.FromPolygons([seat.matrix_world@p.co for p in seat.data.vertices],[list(f.vertices) for f in seat.data.polygons])
  gaps=[tree.find_nearest(Vector((.010,0,z)))[3],tree.find_nearest(Vector((-.010,0,z)))[3]]
  check(c.name+' '+end+' stud seats into plate',max(gaps)<.0002,dict(gap_m=max(gaps)))
  washers=sorted((o for o in obs if end+' retaining washer' in o.name),key=lambda o:bounds(o)[2][0])
  sz=sorted(set(round(v.co.z,6) for v in seat.data.vertices)); wb=[bounds(o)[2] for o in washers]
  # Central plate is zbase-.006 .. zbase+.001 (outer rim is raised independently).
  gap_bottom=abs(wb[0][1]-sz[0]);gap_top=abs(wb[1][0]-(sz[0]+.007))
  check(c.name+' '+end+' washers contact plate',max(gap_bottom,gap_top)<.0001,dict(gaps_m=[gap_bottom,gap_top]))
  sleeve=next(o for o in obs if end+' damper eye sleeve' in o.name);bush=next(o for o in obs if end+' damper eye bush' in o.name)
  centre=Vector(sleeve.location);tree=BVHTree.FromPolygons([sleeve.matrix_world@p.co for p in sleeve.data.vertices],[list(f.vertices) for f in sleeve.data.polygons])
  check(c.name+' '+end+' sleeve bore open',tree.ray_cast(centre+Vector((-.04,0,0)),Vector((1,0,0)),.08)[0] is None)
check('Three kits',len([c for c in bpy.data.collections if c.get('kind')=='suspension'])==3)
report=dict(ok=all(c['passed'] for c in checks),checks=checks,scope='Saved component topology/UVs, stud-to-plate attachment, washer seating, open sleeve bores. Vehicle mounts remain a separate task.')
(OUT/'saved-assembly-check.json').write_text(json.dumps(report,indent=2));print('SAVED_COMPONENT_CHECK',report['ok'],len(checks))
if '--require-pass' in sys.argv:assert report['ok'],[c for c in checks if not c['passed']]
