import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
sys.path.insert(0,'C:/GrandTour/Art/VehicleTools/vendor_geometry')
from shapely.geometry import Polygon
from shapely.ops import unary_union
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-source-v01');Q=Path('C:/GrandTour/Art/Export/VehicleTools/prado-prepared-v01')
A=json.loads((P/'islands.json').read_text());G=json.loads((P/'glass-selections.json').read_text())
a=A[0];v=[Vector(p) for p in a['verts']]
report={}
for name in ['FrontDoor_L','FrontDoor_R','RearDoor_L','RearDoor_R']:
 ids=G[name]['faces'];poly=unary_union([Polygon([(v[i].y,v[i].z) for i in a['polys'][j]]) for j in ids]);area=poly.area
 candidates=[];sgn=1 if name.endswith('_L') else -1
 for j,f in enumerate(a['polys']):
  if j in ids:continue
  pts=[v[i] for i in f];pp=Polygon([(p.y,p.z) for p in pts])
  if not pp.is_valid or pp.area<1e-10:continue
  ratio=pp.intersection(poly.buffer(.0001)).area/pp.area
  if ratio>.9 and all(.139<p.x*sgn<.173 for p in pts):candidates.append({'id':j,'verts':[list(p) for p in pts],'ratio':ratio})
 report[name]={'extra':candidates,'projection_area':area}
print(json.dumps(report,indent=2));(P/'glass-extra-faces.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(Q/'Prado_Prepared.blend'))
counts=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.name.startswith('REFERENCE'):continue
 bm=bmesh.new();bm.from_mesh(o.data)
 counts.append({'name':o.name,'boundary':sum(e.is_boundary for e in bm.edges),'overconnected':sum(len(e.link_faces)>2 for e in bm.edges),'loose':sum(len(e.link_faces)==0 for e in bm.edges),'degenerate':sum(f.calc_area()<1e-10 for f in bm.faces)})
 bm.free()
(Q/'topology-audit.json').write_text(json.dumps(counts,indent=2))
print('AUDIT',sum(c['boundary'] for c in counts),sum(c['overconnected'] for c in counts))
