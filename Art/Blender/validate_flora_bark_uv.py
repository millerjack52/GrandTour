import bpy,json,math
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/LidarStudy/FloraPath');bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.fbx(filepath=str(O/'BarkFix/SM_Path_FP_Tree_D_004.fbx'));o=next(o for o in bpy.context.selected_objects if o.type=='MESH');m=o.data
ue=json.loads((O/'BarkFix/ue-uv-check.json').read_text());lookup={}
for x,y,z,u,v in ue:lookup.setdefault((round(x,1),round(y,1),round(z,1)),[]).append((u,v))
a=[]
for p in m.polygons:
 if p.material_index!=0:continue
 for li in p.loop_indices:
  v=m.vertices[m.loops[li].vertex_index].co;k=(round(v.x*100,1),round(-v.y*100,1),round(v.z*100,1));uv=m.uv_layers[1].data[li].uv
  if k in lookup:a.append(min(math.hypot(u-uv.x,w-(1-uv.y)) for u,w in lookup[k]))
r={'matched':len(a),'max_error':max(a),'mean_error':sum(a)/len(a),'within_tolerance':sum(e<.001 for e in a)};(O/'BarkFix/uv-import-validation.json').write_text(json.dumps(r,indent=2));print(r)
