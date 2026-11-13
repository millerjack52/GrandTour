import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('C:/GrandTour/Art/Export/VehicleTools/prado-glazing-v09');O=P.parent/'prado-glazing-audit'
bpy.ops.wm.open_mainfile(filepath=str(P/'Prado_Corrected.blend'));sc=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();glass=bpy.data.objects['Glass | Windscreen'];g=glass.evaluated_get(deps);me=g.to_mesh();tree=BVHTree.FromPolygons([g.matrix_world@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);report=[]
for ob in sc.objects:
 if ob.type!='MESH' or 'source_component' not in ob:continue
 pts=[ob.matrix_world@v.co for v in ob.data.vertices];c=sum(pts,Vector())/len(pts)/5
 if -.25<c.y<-.1 and .3<c.z<.35 and abs(c.x)<.17:
  distances=[tree.find_nearest(v)[3]*1000 for v in pts]
  report.append({'object':ob.name,'source':ob['source_component'],'center_raw':list(c),'distance_to_windscreen_mm':{'min':min(distances),'max':max(distances),'mean':sum(distances)/len(distances)},'bounds_raw':[[min(v[i]/5 for v in pts) for i in range(3)],[max(v[i]/5 for v in pts) for i in range(3)]]})
g.to_mesh_clear();(O/'v09-contact.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
