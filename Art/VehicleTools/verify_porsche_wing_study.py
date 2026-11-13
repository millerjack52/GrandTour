import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-wing-study-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_FL_Wing_Study.blend'))
report={}
for n in ['Porsche_FL_Wing_Authored','Porsche_FL_Wheelhouse']:
 o=bpy.data.objects[n];me=o.data;me.calc_loop_triangles();vs=[o.matrix_world@v.co for v in me.vertices];tri=[list(t.vertices) for t in me.loop_triangles]
 tree=BVHTree.FromPolygons(vs,tri,all_triangles=True)
 overlaps=[(a,b) for a,b in tree.overlap(tree) if a<b and not set(tri[a]).intersection(tri[b])]
 report[n]={'nonadjacent_triangle_intersections':len(overlaps),'intersection_samples':overlaps[:12]}
 for a,b in overlaps[:3]:
  print('OVERLAP',n,a,b,'POLYGONS',me.loop_triangles[a].polygon_index,me.loop_triangles[b].polygon_index,'RAW_A',[list(vs[i]/4.5) for i in tri[a]],'RAW_B',[list(vs[i]/4.5) for i in tri[b]],flush=True)
 print('TOTAL',len(overlaps),'EARLY_POLYGONS',sum(me.loop_triangles[a].polygon_index<1360 and me.loop_triangles[b].polygon_index<1360 for a,b in overlaps),flush=True)
 assert not overlaps,(n,overlaps[:12])
report['reopened_file_validation']='passed'
(P/'independent-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
