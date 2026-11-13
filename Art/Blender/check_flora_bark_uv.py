import bpy,json
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath');out=[]
for n in ['FP_Tree_D_001','FP_Tree_D_004','FP_Tree_B_001']:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.fbx(filepath=str(O/('SM_Path_'+n+'.fbx')));o=next(o for o in bpy.context.selected_objects if o.type=="MESH");m=o.data;uv=m.uv_layers[0]
 stats=[]
 for p in m.polygons:
  if p.material_index!=0 or p.center.z>6:continue
  ps=[uv.data[i].uv for i in p.loop_indices];area=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(ps,ps[1:]+ps[:1])))/2
  stats.append((p.area,area,p.center.z))
 out.append({'tree':n,'faces':len(stats),'geometry_area':sum(a for a,b,z in stats),'uv_area':sum(b for a,b,z in stats),'collapsed_surface_area':sum(a for a,b,z in stats if b<1e-10)})
(O/'bark-uv-check.json').write_text(json.dumps(out,indent=2))

